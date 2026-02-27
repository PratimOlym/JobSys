"""DynamoDB operations for the JobSys jobs table."""

import logging
from datetime import datetime
from typing import List, Optional

from . import config
from .models import Job, JobStatus

logger = logging.getLogger(__name__)


def create_job(job: Job) -> Job:
    """Insert a new job record into DynamoDB.

    Args:
        job: Job dataclass instance to persist.

    Returns:
        The saved Job with timestamps set.
    """
    client = config.get_dynamodb_client()
    now = datetime.utcnow().isoformat()
    job.created_at = now
    job.updated_at = now

    client.put_item(
        TableName=config.JOBS_TABLE_NAME,
        Item=job.to_dynamo_item(),
        ConditionExpression="attribute_not_exists(job_id)",
    )
    logger.info(f"Created job {job.job_id}: {job.job_title} at {job.company}")
    return job


def get_job(job_id: str) -> Optional[Job]:
    """Retrieve a single job by its ID."""
    client = config.get_dynamodb_client()
    response = client.get_item(
        TableName=config.JOBS_TABLE_NAME,
        Key={"job_id": {"S": job_id}},
    )
    item = response.get("Item")
    if not item:
        return None
    return Job.from_dynamo_item(item)


def job_exists_by_url(url: str) -> bool:
    """Check if a job with the given URL already exists.

    Uses a scan with a filter — acceptable for moderate dataset sizes.
    For large-scale use, consider adding a GSI on job_url.
    """
    client = config.get_dynamodb_client()
    response = client.scan(
        TableName=config.JOBS_TABLE_NAME,
        FilterExpression="job_url = :url",
        ExpressionAttributeValues={":url": {"S": url}},
        Select="COUNT",
    )
    return response.get("Count", 0) > 0


def list_jobs_by_status(status: str, limit: int = 100) -> List[Job]:
    """List jobs filtered by status using the GSI.

    Args:
        status: One of the JobStatus enum values.
        limit: Maximum number of results.

    Returns:
        List of Job instances.
    """
    client = config.get_dynamodb_client()
    response = client.query(
        TableName=config.JOBS_TABLE_NAME,
        IndexName="status-index",
        KeyConditionExpression="#s = :status",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":status": {"S": status}},
        Limit=limit,
    )
    return [Job.from_dynamo_item(item) for item in response.get("Items", [])]


def list_all_jobs(limit: int = 500) -> List[Job]:
    """List all jobs (scan). Use with caution on large tables."""
    client = config.get_dynamodb_client()
    response = client.scan(
        TableName=config.JOBS_TABLE_NAME,
        Limit=limit,
    )
    return [Job.from_dynamo_item(item) for item in response.get("Items", [])]


def update_job_status(job_id: str, new_status: str, **extra_fields) -> None:
    """Update the status of a job and any additional fields.

    Args:
        job_id: The job's primary key.
        new_status: New status value.
        **extra_fields: Additional string fields to update (e.g., jd_s3_path="...").
    """
    client = config.get_dynamodb_client()
    now = datetime.utcnow().isoformat()

    update_parts = ["#s = :status", "updated_at = :now"]
    attr_names = {"#s": "status"}
    attr_values = {
        ":status": {"S": new_status},
        ":now": {"S": now},
    }

    for key, value in extra_fields.items():
        placeholder = f":{key}"
        if isinstance(value, (int, float)):
            update_parts.append(f"{key} = {placeholder}")
            attr_values[placeholder] = {"N": str(value)}
        elif isinstance(value, dict):
            import json
            update_parts.append(f"{key} = {placeholder}")
            attr_values[placeholder] = {"S": json.dumps(value)}
        else:
            update_parts.append(f"{key} = {placeholder}")
            attr_values[placeholder] = {"S": str(value)}

    update_expr = "SET " + ", ".join(update_parts)

    client.update_item(
        TableName=config.JOBS_TABLE_NAME,
        Key={"job_id": {"S": job_id}},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=attr_names,
        ExpressionAttributeValues=attr_values,
    )
    logger.info(f"Updated job {job_id} → status={new_status}")


def update_job_match_results(
    job_id: str,
    best_resume_name: str,
    match_score: float,
    match_details: dict,
) -> None:
    """Update a job with resume matching results."""
    update_job_status(
        job_id,
        JobStatus.RESUME_MATCH_DONE,
        best_resume_name=best_resume_name,
        match_score=match_score,
        match_details=match_details,
    )


def update_job_documents(
    job_id: str,
    optimized_resume_path: str,
    cover_letter_path: str,
) -> None:
    """Update a job with generated document paths."""
    update_job_status(
        job_id,
        JobStatus.DOCUMENTS_READY,
        optimized_resume_path=optimized_resume_path,
        cover_letter_path=cover_letter_path,
    )


def delete_job(job_id: str) -> None:
    """Delete a job record."""
    client = config.get_dynamodb_client()
    client.delete_item(
        TableName=config.JOBS_TABLE_NAME,
        Key={"job_id": {"S": job_id}},
    )
    logger.info(f"Deleted job {job_id}")
