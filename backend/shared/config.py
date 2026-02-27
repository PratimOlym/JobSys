"""Configuration management for JobSys.

Loads configuration from environment variables and DynamoDB config table.
"""

import os
import json
import logging
import boto3

logger = logging.getLogger(__name__)

# ── Environment Variable Defaults ──────────────────────────────────────────────
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
JOBS_TABLE_NAME = os.environ.get("JOBS_TABLE_NAME", "jobsys-jobs")
CONFIG_TABLE_NAME = os.environ.get("CONFIG_TABLE_NAME", "jobsys-config")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "jobsys-storage")
GEMINI_API_KEY_SECRET = os.environ.get("GEMINI_API_KEY_SECRET", "jobsys/gemini-api-key")
RESUME_MATCHER_FUNCTION = os.environ.get("RESUME_MATCHER_FUNCTION", "jobsys-resume-matcher")
DOC_GENERATOR_FUNCTION = os.environ.get("DOC_GENERATOR_FUNCTION", "jobsys-document-generator")

# ── S3 Folder Prefixes ────────────────────────────────────────────────────────
S3_JD_PREFIX = "job-descriptions/"
S3_BASE_RESUMES_PREFIX = "base-resumes/"
S3_OPTIMIZED_RESUMES_PREFIX = "resume-optimized/"
S3_COVER_LETTERS_PREFIX = "cover-letters/"


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


def get_gemini_api_key() -> str:
    """Retrieve the Gemini API key from AWS Secrets Manager."""
    # Allow override via environment variable for local testing
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key

    try:
        client = get_secrets_manager_client()
        response = client.get_secret_value(SecretId=GEMINI_API_KEY_SECRET)
        secret = json.loads(response["SecretString"])
        return secret.get("api_key", "")
    except Exception as e:
        logger.error(f"Failed to retrieve Gemini API key: {e}")
        raise


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
            logger.warning(f"Config key '{config_key}' not found")
            return {}

        # Parse the config_value (stored as a JSON string in an S attribute)
        raw = item.get("config_value", {}).get("S", "{}")
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Failed to retrieve config '{config_key}': {e}")
        return {}


def put_config_value(config_key: str, config_value: dict) -> None:
    """Store a configuration value in the DynamoDB config table."""
    try:
        client = get_dynamodb_client()
        client.put_item(
            TableName=CONFIG_TABLE_NAME,
            Item={
                "config_key": {"S": config_key},
                "config_value": {"S": json.dumps(config_value)},
            },
        )
    except Exception as e:
        logger.error(f"Failed to store config '{config_key}': {e}")
        raise


def get_job_source_urls() -> list:
    """Get the list of job source URLs from configuration."""
    config = get_config_value("job_sources")
    return config.get("urls", [])


def get_user_profile() -> dict:
    """Get the user profile (name, email, etc.) from configuration."""
    return get_config_value("user_profile")
