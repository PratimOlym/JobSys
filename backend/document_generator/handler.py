"""Document Generator Lambda handler.

Triggered by the Resume Matcher or manual invocation.
For each job with status='resume-match-done':
  1. Retrieves the JD and best-matching base resume from S3
  2. Generates an optimized resume using Gemini
  3. Generates a tailored cover letter using Gemini
  4. Saves both as DOCX files to S3
  5. Updates the DB with document paths
"""

import json
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared import config
from shared.db import list_jobs_by_status, update_job_documents, update_job_status, get_job
from shared.storage import download_file, download_text, upload_optimized_resume, upload_cover_letter
from shared.models import JobStatus, MatchResult
from shared.llm_client import generate_optimized_resume_content, generate_cover_letter_content
from document_generator.resume_generator import build_resume_docx
from document_generator.cover_letter import build_cover_letter_docx
from shared.parser import extract_text_from_file


def handler(event, context):
    """Lambda entry point.

    Event can contain:
      - {"job_ids": ["id1", "id2"]} for specific jobs
      - {} to process all jobs with status='resume-match-done'
    """
    logger.info(f"Document Generator invoked. Event: {json.dumps(event, default=str)[:500]}")

    # Get user profile for resume filenames and cover letter
    user_profile = config.get_user_profile()
    user_name = user_profile.get("name", "Applicant")

    # Get jobs to process
    specific_ids = event.get("job_ids", [])
    if specific_ids:
        jobs = [get_job(jid) for jid in specific_ids]
        jobs = [j for j in jobs if j is not None]
    else:
        jobs = list_jobs_by_status(JobStatus.RESUME_MATCH_DONE)

    if not jobs:
        logger.info("No jobs pending document generation")
        return {"statusCode": 200, "body": "No jobs pending"}

    logger.info(f"Generating documents for {len(jobs)} jobs")

    generated_count = 0
    error_count = 0

    for job in jobs:
        try:
            logger.info(f"Processing job: {job.job_title} at {job.company} ({job.job_id})")

            # Get JD text
            jd_text = ""
            if job.jd_s3_path:
                try:
                    jd_text = download_text(job.jd_s3_path)
                except Exception:
                    pass
            if not jd_text:
                jd_text = job.job_details

            # Get best-matching base resume text
            base_resume_text = ""
            if job.best_resume_name:
                try:
                    key = f"{config.S3_BASE_RESUMES_PREFIX}{job.best_resume_name}"
                    file_bytes = download_file(key)
                    base_resume_text = extract_text_from_file(file_bytes, job.best_resume_name)
                except Exception as e:
                    logger.error(f"Failed to load base resume '{job.best_resume_name}': {e}")

            if not base_resume_text:
                logger.warning(f"No base resume text for job {job.job_id}, skipping")
                continue

            job_meta = {
                "job_title": job.job_title,
                "company": job.company,
                "location": job.location,
            }

            # Reconstruct MatchResult from stored match_details
            match_result = MatchResult(
                resume_name=job.best_resume_name,
                overall_score=job.match_score,
                keyword_score=job.match_details.get("keyword_score", 0) if job.match_details else 0,
                semantic_score=job.match_details.get("semantic_score", 0) if job.match_details else 0,
                matched_skills=job.match_details.get("matched_skills", []) if job.match_details else [],
                missing_skills=job.match_details.get("missing_skills", []) if job.match_details else [],
                recommendation=job.match_details.get("recommendation", "") if job.match_details else "",
            )

            # ── Generate Optimized Resume ──────────────────────────────────
            logger.info(f"Generating optimized resume for job {job.job_id}")
            resume_data = generate_optimized_resume_content(
                base_resume_text, jd_text, job_meta, match_result
            )
            resume_docx_bytes = build_resume_docx(resume_data)
            resume_s3_key = upload_optimized_resume(
                user_name, job.job_title, job.job_id, resume_docx_bytes
            )
            logger.info(f"Optimized resume uploaded: {resume_s3_key}")

            # ── Generate Cover Letter ──────────────────────────────────────
            logger.info(f"Generating cover letter for job {job.job_id}")
            cover_letter_text = generate_cover_letter_content(
                base_resume_text, jd_text, job_meta, user_profile
            )
            cover_letter_bytes = build_cover_letter_docx(cover_letter_text, user_profile)
            cover_letter_s3_key = upload_cover_letter(
                user_name, job.job_title, job.job_id, cover_letter_bytes
            )
            logger.info(f"Cover letter uploaded: {cover_letter_s3_key}")

            # ── Update DB ──────────────────────────────────────────────────
            update_job_documents(
                job_id=job.job_id,
                optimized_resume_path=resume_s3_key,
                cover_letter_path=cover_letter_s3_key,
            )
            generated_count += 1
            logger.info(f"Documents generated for job '{job.job_title}'")

        except Exception as e:
            logger.error(f"Failed to generate documents for job {job.job_id}: {e}")
            update_job_status(job.job_id, JobStatus.ERROR)
            error_count += 1

    result = {
        "generated": generated_count,
        "errors": error_count,
        "total_jobs": len(jobs),
    }
    logger.info(f"Document Generator complete: {result}")
    return {"statusCode": 200, "body": json.dumps(result)}
