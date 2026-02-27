"""Resume Matcher Lambda handler.

Triggered by the Job Scanner or EventBridge schedule.
For each job with status='new':
  1. Retrieves the JD from S3
  2. Scores all base resumes against the JD
  3. Selects the best match and updates the DB
  4. Invokes the Document Generator for each matched job
"""

import json
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared import config
from shared.db import list_jobs_by_status, update_job_match_results, update_job_status
from shared.storage import list_base_resumes, download_file, download_text, load_resume_summaries
from shared.models import JobStatus
from resume_matcher.llm_matcher import match_resume_to_jd
from shared.parser import extract_text_from_file


def handler(event, context):
    """Lambda entry point.

    Event can contain:
      - {"job_ids": ["id1", "id2"]} for specific jobs
      - {} to process all jobs with status='new'
    """
    logger.info(f"Resume Matcher invoked. Event: {json.dumps(event, default=str)[:500]}")

    # Get jobs to process
    specific_ids = event.get("job_ids", [])
    if specific_ids:
        from shared.db import get_job
        jobs = [get_job(jid) for jid in specific_ids]
        jobs = [j for j in jobs if j is not None]
    else:
        jobs = list_jobs_by_status(JobStatus.NEW)

    if not jobs:
        logger.info("No new jobs to process")
        return {"statusCode": 200, "body": "No new jobs"}

    # Load all base resumes
    base_resume_keys = list_base_resumes()
    if not base_resume_keys:
        logger.error("No base resumes found in S3. Upload resumes to base-resumes/ folder.")
        return {"statusCode": 200, "body": "No base resumes available"}

    logger.info(f"Found {len(jobs)} new jobs and {len(base_resume_keys)} base resumes")

    # ── Try using pre-generated summaries first (much faster) ─────────────────
    stored_summaries = load_resume_summaries()
    summary_map = {s["resume_name"]: s for s in stored_summaries if "resume_name" in s}

    def _summary_to_text(summary: dict) -> str:
        """Convert a stored summary dict into a compact text for LLM matching."""
        lines = [
            f"Resume: {summary.get('resume_name', '')}",
            f"Headline: {summary.get('headline', '')}",
            f"Years of Experience: {summary.get('total_experience_years', 'N/A')}",
            f"Education: {summary.get('education', '')}",
            f"Skills: {', '.join(summary.get('skills', []))}",
            f"Key Strengths: {', '.join(summary.get('key_strengths', []))}",
            f"Summary: {summary.get('summary_text', '')}",
        ]
        return "\n".join(lines)

    # Pre-load all base resume texts (use summary if available, otherwise full text)
    base_resumes = {}
    for key in base_resume_keys:
        try:
            filename = key.split("/")[-1]
            if not filename:
                continue
            if filename in summary_map:
                # Use compact summary text — saves tokens and time
                text = _summary_to_text(summary_map[filename])
                logger.info(f"Using stored summary for {filename}")
            else:
                file_bytes = download_file(key)
                text = extract_text_from_file(file_bytes, filename)
                logger.info(f"Loaded full resume text for {filename} ({len(text)} chars)")
            if text.strip():
                base_resumes[filename] = text
        except Exception as e:
            logger.error(f"Failed to load base resume {key}: {e}")

    if not base_resumes:
        logger.error("Could not load any base resumes")
        return {"statusCode": 200, "body": "Failed to load base resumes"}

    matched_count = 0
    error_count = 0

    for job in jobs:
        try:
            # Get JD text
            jd_text = ""
            if job.jd_s3_path:
                try:
                    jd_text = download_text(job.jd_s3_path)
                except Exception:
                    pass

            if not jd_text:
                jd_text = job.job_details

            if not jd_text:
                logger.warning(f"No JD text for job {job.job_id}, skipping")
                continue

            job_meta = {
                "job_title": job.job_title,
                "company": job.company,
                "location": job.location,
            }

            # Score each base resume
            best_result = None
            for resume_name, resume_text in base_resumes.items():
                result = match_resume_to_jd(resume_name, resume_text, jd_text, job_meta)
                if best_result is None or result.overall_score > best_result.overall_score:
                    best_result = result

            if best_result:
                # Update DB with match results
                update_job_match_results(
                    job_id=job.job_id,
                    best_resume_name=best_result.resume_name,
                    match_score=best_result.overall_score,
                    match_details=best_result.to_dict(),
                )
                matched_count += 1
                logger.info(
                    f"Matched job '{job.job_title}': "
                    f"best resume='{best_result.resume_name}' "
                    f"score={best_result.overall_score}"
                )

        except Exception as e:
            logger.error(f"Failed to match job {job.job_id}: {e}")
            update_job_status(job.job_id, JobStatus.ERROR)
            error_count += 1

    result = {
        "matched": matched_count,
        "errors": error_count,
        "total_jobs": len(jobs),
    }
    logger.info(f"Resume Matcher complete: {result}")

    # Trigger Document Generator if any jobs were matched
    if matched_count > 0:
        _invoke_document_generator()

    return {"statusCode": 200, "body": json.dumps(result)}


def _invoke_document_generator():
    """Asynchronously invoke the Document Generator Lambda."""
    try:
        lambda_client = config.get_lambda_client()
        lambda_client.invoke(
            FunctionName=config.DOC_GENERATOR_FUNCTION,
            InvocationType="Event",
            Payload=json.dumps({"trigger": "resume-matcher"}),
        )
        logger.info("Document Generator Lambda invoked asynchronously")
    except Exception as e:
        logger.error(f"Failed to invoke Document Generator: {e}")
