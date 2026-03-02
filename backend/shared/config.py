"""Configuration management for JobSys.

Loads configuration from environment variables, AWS SSM Parameter Store,
and AWS Secrets Manager.  All LLM provider settings (provider name, model
names, API keys) are configurable here without touching application code.
"""

import os
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

# ── Environment Variable Defaults ──────────────────────────────────────────────
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
JOBS_TABLE_NAME = os.environ.get("JOBS_TABLE_NAME", "jobsys-jobs")
CONFIG_TABLE_NAME = os.environ.get("CONFIG_TABLE_NAME", "jobsys-config")
TOKEN_USAGE_TABLE_NAME = os.environ.get("TOKEN_USAGE_TABLE_NAME", "jobsys-token-usage")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "jobsys-storage")
RESUME_MATCHER_FUNCTION = os.environ.get("RESUME_MATCHER_FUNCTION", "jobsys-resume-matcher")
DOC_GENERATOR_FUNCTION = os.environ.get("DOC_GENERATOR_FUNCTION", "jobsys-document-generator")

# ── LLM Provider Selection ─────────────────────────────────────────────────────
# Override with LLM_PROVIDER env var.  Allowed values: gemini | openai | huggingface
LLM_PROVIDER_DEFAULT = "gemini"

# ── AWS Secrets Manager — secret name defaults ─────────────────────────────────
GEMINI_API_KEY_SECRET  = os.environ.get("GEMINI_API_KEY_SECRET",  "jobsys/gemini-api-key")
OPENAI_API_KEY_SECRET  = os.environ.get("OPENAI_API_KEY_SECRET",  "jobsys/openai-api-key")
HF_API_KEY_SECRET      = os.environ.get("HF_API_KEY_SECRET",      "jobsys/hf-api-key")

# ── AWS SSM Parameter Store — parameter name defaults ─────────────────────────
# Models are non-secret config → SSM Parameter Store (not Secrets Manager)
SSM_GEMINI_MODEL  = os.environ.get("SSM_GEMINI_MODEL",  "/jobsys/llm/gemini_model")
SSM_OPENAI_MODEL  = os.environ.get("SSM_OPENAI_MODEL",  "/jobsys/llm/openai_model")
SSM_HF_MODEL      = os.environ.get("SSM_HF_MODEL",      "/jobsys/llm/hf_model")
SSM_LLM_PROVIDER  = os.environ.get("SSM_LLM_PROVIDER",  "/jobsys/llm/provider")

# ── Model Defaults (used when SSM parameter is absent) ────────────────────────
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"          # Fast, cheap, great at JSON tasks
DEFAULT_HF_MODEL     = "mistralai/Mistral-7B-Instruct-v0.3"  # Best free-tier option

# ── S3 Folder Prefixes ────────────────────────────────────────────────────────
S3_JD_PREFIX                = "job-descriptions/"
S3_BASE_RESUMES_PREFIX      = "base-resumes/"
S3_OPTIMIZED_RESUMES_PREFIX = "resume-optimized/"
S3_COVER_LETTERS_PREFIX     = "cover-letters/"


# ── AWS Client Helpers ─────────────────────────────────────────────────────────

def get_dynamodb_client():
    """Get a DynamoDB client."""
    return boto3.client("dynamodb", region_name=AWS_REGION)


def get_s3_client():
    """Get an S3 client."""
    return boto3.client("s3", region_name=AWS_REGION)


def get_lambda_client():
    """Get a Lambda client."""
    return boto3.client("lambda", region_name=AWS_REGION)


def get_secrets_manager_client():
    """Get a Secrets Manager client."""
    return boto3.client("secretsmanager", region_name=AWS_REGION)


def get_ssm_client():
    """Get an SSM Parameter Store client."""
    return boto3.client("ssm", region_name=AWS_REGION)


# ── SSM Parameter Store Helpers ────────────────────────────────────────────────

def get_ssm_parameter(parameter_name: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieve a plain-text parameter from SSM Parameter Store.

    Falls back to *default* if the parameter does not exist or SSM is
    unreachable (e.g. local development without AWS access).

    Args:
        parameter_name: Full SSM parameter path (e.g. ``/jobsys/llm/provider``).
        default: Value to return when the parameter cannot be fetched.

    Returns:
        Parameter value string, or *default*.
    """
    try:
        client = get_ssm_client()
        response = client.get_parameter(Name=parameter_name)
        return response["Parameter"]["Value"]
    except Exception as e:
        logger.debug("SSM parameter '%s' not found, using default: %s", parameter_name, e)
        return default


# ── LLM Provider Config ────────────────────────────────────────────────────────

def get_llm_provider() -> str:
    """Return the active LLM provider name.

    Resolution order:
    1. ``LLM_PROVIDER`` environment variable
    2. SSM Parameter Store (``/jobsys/llm/provider``)
    3. Hard-coded default: ``"gemini"``
    """
    env_val = os.environ.get("LLM_PROVIDER")
    if env_val:
        return env_val.strip().lower()
    ssm_val = get_ssm_parameter(SSM_LLM_PROVIDER, default=LLM_PROVIDER_DEFAULT)
    return (ssm_val or LLM_PROVIDER_DEFAULT).strip().lower()


def get_llm_model(provider: str) -> str:
    """Return the model name for *provider*.

    Resolution order for each provider:
    1. Environment variable (``GEMINI_MODEL`` / ``OPENAI_MODEL`` / ``HF_MODEL``)
    2. SSM Parameter Store
    3. Baked-in default

    Args:
        provider: ``"gemini"``, ``"openai"``, or ``"huggingface"``.

    Returns:
        Model name string.
    """
    if provider == "openai":
        env_model = os.environ.get("OPENAI_MODEL")
        if env_model:
            return env_model.strip()
        return get_ssm_parameter(SSM_OPENAI_MODEL, default=DEFAULT_OPENAI_MODEL) or DEFAULT_OPENAI_MODEL

    if provider == "huggingface":
        env_model = os.environ.get("HF_MODEL")
        if env_model:
            return env_model.strip()
        return get_ssm_parameter(SSM_HF_MODEL, default=DEFAULT_HF_MODEL) or DEFAULT_HF_MODEL

    # Default: gemini
    env_model = os.environ.get("GEMINI_MODEL")
    if env_model:
        return env_model.strip()
    return get_ssm_parameter(SSM_GEMINI_MODEL, default=DEFAULT_GEMINI_MODEL) or DEFAULT_GEMINI_MODEL


# ── API Key Helpers ────────────────────────────────────────────────────────────

def _get_secret(env_var: str, secret_name: str, secret_key: str = "api_key") -> str:
    """Generic helper: env var → Secrets Manager → raise.

    Args:
        env_var: Environment variable name to check first.
        secret_name: AWS Secrets Manager secret name.
        secret_key: JSON key within the secret string.

    Returns:
        API key string.

    Raises:
        RuntimeError: If the key cannot be resolved from any source.
    """
    env_val = os.environ.get(env_var)
    if env_val:
        return env_val

    try:
        client = get_secrets_manager_client()
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        return secret.get(secret_key, "")
    except Exception as e:
        logger.error("Failed to retrieve secret '%s': %s", secret_name, e)
        raise


def get_gemini_api_key() -> str:
    """Retrieve the Gemini API key from env var or AWS Secrets Manager."""
    return _get_secret("GEMINI_API_KEY", GEMINI_API_KEY_SECRET)


def get_openai_api_key() -> str:
    """Retrieve the OpenAI API key from env var or AWS Secrets Manager."""
    return _get_secret("OPENAI_API_KEY", OPENAI_API_KEY_SECRET)


def get_hf_api_key() -> str:
    """Retrieve the HuggingFace API key from env var or AWS Secrets Manager."""
    return _get_secret("HF_API_KEY", HF_API_KEY_SECRET)


# ── Token Usage Tracking ───────────────────────────────────────────────────────

def record_token_usage(
    usage,           # TokenUsage dataclass from llm_types
    provider: str,
    model: str,
    operation: str,
) -> None:
    """Persist one token-usage record to the ``jobsys-token-usage`` DynamoDB table.

    This is a best-effort write — failures are logged but never re-raised so
    that a DynamoDB outage or missing table never blocks an LLM operation.

    The table uses ``record_id`` (UUID) as the partition key and ``timestamp``
    as a sort key / GSI for time-range queries.

    Args:
        usage: :class:`~shared.llm_types.TokenUsage` instance.
        provider: Provider identifier (``"gemini"`` / ``"openai"`` / …).
        model: Exact model name string.
        operation: Name of the high-level function (e.g. ``"summarize_resume"``).
    """
    try:
        record_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        timestamp = now.isoformat()
        # TTL for DynamoDB (90 days from now)
        ttl_epoch = int((now.timestamp() + (90 * 24 * 60 * 60)))

        item: dict = {
            "record_id": {"S": record_id},
            "timestamp":  {"S": timestamp},
            "ttl_epoch":  {"N": str(ttl_epoch)},
            "provider":   {"S": provider},
            "model":      {"S": model},
            "operation":  {"S": operation},
            "prompt_tokens":     {"N": str(usage.prompt_tokens)},
            "completion_tokens": {"N": str(usage.completion_tokens)},
            "total_tokens":      {"N": str(usage.total_tokens)},
        }

        if usage.remaining_tokens is not None:
            item["remaining_tokens"] = {"N": str(usage.remaining_tokens)}

        client = get_dynamodb_client()
        client.put_item(TableName=TOKEN_USAGE_TABLE_NAME, Item=item)

        logger.debug(
            "Token usage recorded: record_id=%s provider=%s model=%s "
            "operation=%s total_tokens=%d",
            record_id, provider, model, operation, usage.total_tokens,
        )
    except Exception as e:
        logger.warning("Token usage recording skipped (table may not exist yet): %s", e)


# ── DynamoDB Config Helpers (unchanged) ───────────────────────────────────────

def get_config_value(config_key: str) -> dict:
    """Retrieve a configuration value from the DynamoDB config table.

    Args:
        config_key: The configuration key (e.g., 'job_sources', 'user_profile')

    Returns:
        The config_value map as a Python dict.
    """
    try:
        client = get_dynamodb_client()
        response = client.get_item(
            TableName=CONFIG_TABLE_NAME,
            Key={"config_key": {"S": config_key}},
        )
        item = response.get("Item")
        if not item:
            logger.warning("Config key '%s' not found", config_key)
            return {}

        raw = item.get("config_value", {}).get("S", "{}")
        return json.loads(raw)
    except Exception as e:
        logger.error("Failed to retrieve config '%s': %s", config_key, e)
        return {}


def put_config_value(config_key: str, config_value: dict) -> None:
    """Store a configuration value in the DynamoDB config table."""
    try:
        client = get_dynamodb_client()
        client.put_item(
            TableName=CONFIG_TABLE_NAME,
            Item={
                "config_key":   {"S": config_key},
                "config_value": {"S": json.dumps(config_value)},
            },
        )
    except Exception as e:
        logger.error("Failed to store config '%s': %s", config_key, e)
        raise


def get_job_source_urls() -> list:
    """Get the list of job source URLs from configuration."""
    config = get_config_value("job_sources")
    return config.get("urls", [])


def get_user_profile() -> dict:
    """Get the user profile (name, email, etc.) from configuration."""
    return get_config_value("user_profile")
