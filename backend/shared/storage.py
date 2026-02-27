"""S3 storage operations for JobSys documents."""

import io
import logging
import re
from typing import List, Optional, Tuple

from . import config

logger = logging.getLogger(__name__)


def _sanitize_filename(name: str) -> str:
    """Remove special characters from a string to create safe filenames."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", name).strip("_")[:80]


# ── Upload Operations ──────────────────────────────────────────────────────────

def upload_jd(job_id: str, job_title: str, content: bytes, extension: str = "txt") -> str:
    """Upload a Job Description to S3.

    Args:
        job_id: Unique job identifier.
        job_title: Job title (used in the folder name).
        content: Raw file content bytes.
        extension: File extension (txt, pdf, docx).

    Returns:
        The S3 key where the file was stored.
    """
    safe_title = _sanitize_filename(job_title)
    s3_key = f"{config.S3_JD_PREFIX}{job_id}_{safe_title}/jd.{extension}"
    _upload_bytes(s3_key, content)
    return s3_key


def upload_base_resume(filename: str, content: bytes) -> str:
    """Upload a base resume file to S3.

    Args:
        filename: Original filename.
        content: Raw file content bytes.

    Returns:
        The S3 key where the file was stored.
    """
    # Ensure it goes into the base-resumes/ folder
    s3_key = f"{config.S3_BASE_RESUMES_PREFIX}{filename}"
    _upload_bytes(s3_key, content)
    return s3_key


def upload_optimized_resume(
    user_name: str, job_title: str, job_id: str, content: bytes
) -> str:
    """Upload an optimized resume DOCX to S3.

    Returns:
        The S3 key where the file was stored.
    """
    safe_name = _sanitize_filename(user_name)
    safe_title = _sanitize_filename(job_title)
    filename = f"{safe_name}_{safe_title}_{job_id}.docx"
    s3_key = f"{config.S3_OPTIMIZED_RESUMES_PREFIX}{filename}"
    _upload_bytes(s3_key, content)
    return s3_key


def upload_cover_letter(
    user_name: str, job_title: str, job_id: str, content: bytes
) -> str:
    """Upload a cover letter DOCX to S3.

    Returns:
        The S3 key where the file was stored.
    """
    safe_name = _sanitize_filename(user_name)
    safe_title = _sanitize_filename(job_title)
    filename = f"{safe_name}_{safe_title}_{job_id}_cover.docx"
    s3_key = f"{config.S3_COVER_LETTERS_PREFIX}{filename}"
    _upload_bytes(s3_key, content)
    return s3_key


# ── Download Operations ────────────────────────────────────────────────────────

def download_file(s3_key: str) -> bytes:
    """Download a file from S3 and return its content as bytes."""
    client = config.get_s3_client()
    response = client.get_object(Bucket=config.S3_BUCKET_NAME, Key=s3_key)
    return response["Body"].read()


def download_text(s3_key: str) -> str:
    """Download a text file from S3 and return as string."""
    return download_file(s3_key).decode("utf-8")


# ── Listing Operations ─────────────────────────────────────────────────────────

def list_base_resumes() -> List[str]:
    """List all base resume files in the base-resumes/ folder.

    Returns:
        List of S3 keys for base resume files.
    """
    # Only return actual resume files, not the hidden summaries doc.
    return [k for k in _list_files(config.S3_BASE_RESUMES_PREFIX)
            if not k.endswith(".summaries.json")]


def list_jd_files() -> List[str]:
    """List all JD files in the job-descriptions/ folder."""
    return _list_files(config.S3_JD_PREFIX)


# ── Resume Summaries ──────────────────────────────────────────────────────────

# Fixed S3 key for the consolidated summaries file
_SUMMARIES_KEY = f"{config.S3_BASE_RESUMES_PREFIX}.summaries.json"


def save_resume_summaries(summaries: list) -> str:
    """Save resume summaries as JSON to S3.

    Args:
        summaries: List of summary dicts (one per resume).

    Returns:
        The S3 key where summaries were stored.
    """
    import json as _json
    content = _json.dumps({"summaries": summaries}, indent=2).encode("utf-8")
    _upload_bytes(_SUMMARIES_KEY, content)
    logger.info(f"Saved {len(summaries)} resume summaries to {_SUMMARIES_KEY}")
    return _SUMMARIES_KEY


def load_resume_summaries() -> list:
    """Load resume summaries from S3.

    Returns:
        List of summary dicts, or empty list if not found.
    """
    import json as _json
    try:
        raw = download_text(_SUMMARIES_KEY)
        data = _json.loads(raw)
        return data.get("summaries", [])
    except Exception as e:
        logger.warning(f"Could not load resume summaries: {e}")
        return []


# ── Pre-signed URL Generation ─────────────────────────────────────────────────

def generate_presigned_url(s3_key: str, expiration: int = 3600) -> str:
    """Generate a pre-signed URL for downloading a file.

    Args:
        s3_key: The S3 object key.
        expiration: URL expiry in seconds (default 1 hour).

    Returns:
        Pre-signed URL string.
    """
    client = config.get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": config.S3_BUCKET_NAME, "Key": s3_key},
        ExpiresIn=expiration,
    )


# ── Delete Operations ──────────────────────────────────────────────────────────

def delete_file(s3_key: str) -> None:
    """Delete a file from S3."""
    client = config.get_s3_client()
    client.delete_object(Bucket=config.S3_BUCKET_NAME, Key=s3_key)
    logger.info(f"Deleted from s3://{config.S3_BUCKET_NAME}/{s3_key}")


# ── Internal Helpers ───────────────────────────────────────────────────────────

def _upload_bytes(s3_key: str, content: bytes) -> None:
    """Upload raw bytes to S3."""
    client = config.get_s3_client()
    content_type = _guess_content_type(s3_key)
    client.put_object(
        Bucket=config.S3_BUCKET_NAME,
        Key=s3_key,
        Body=content,
        ContentType=content_type,
    )
    logger.info(f"Uploaded to s3://{config.S3_BUCKET_NAME}/{s3_key}")


def _list_files(prefix: str) -> List[str]:
    """List all object keys under a given S3 prefix."""
    client = config.get_s3_client()
    keys = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=config.S3_BUCKET_NAME, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            # Skip "folder" markers
            if not key.endswith("/"):
                keys.append(key)
    return keys


def _guess_content_type(s3_key: str) -> str:
    """Guess MIME type from file extension."""
    ext = s3_key.rsplit(".", 1)[-1].lower() if "." in s3_key else ""
    return {
        "txt": "text/plain",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "json": "application/json",
        "html": "text/html",
    }.get(ext, "application/octet-stream")
