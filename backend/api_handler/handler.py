"""API Handler Lambda — REST API for the JobSys Dashboard.

Routes API Gateway requests to the appropriate handler functions.
Provides endpoints for job management, configuration, and document access.
"""

import json
import logging
import os
import traceback

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared import config
from shared.db import (
    list_all_jobs, list_jobs_by_status, get_job,
    delete_job, update_job_status
)
import base64
from shared.storage import (
    generate_presigned_url, list_base_resumes, upload_base_resume, delete_file,
    save_resume_summaries, load_resume_summaries, download_file as download_file_bytes
)
from shared.models import JobStatus


def handler(event, context):
    """Lambda entry point for API Gateway proxy integration."""
    logger.info(f"API request: {event.get('httpMethod')} {event.get('path')}")

    try:
        method = event.get("httpMethod", "GET")
        path = event.get("path", "/")
        path_params = event.get("pathParameters") or {}
        query_params = event.get("queryStringParameters") or {}
        body = _parse_body(event)

        # ── Route Requests ─────────────────────────────────────────────────
        if path == "/jobs" and method == "GET":
            return _list_jobs(query_params)

        elif path.startswith("/jobs/") and method == "GET":
            job_id = path_params.get("id") or path.split("/jobs/")[1].split("/")[0]
            return _get_job_detail(job_id)

        elif path == "/jobs/scan" and method == "POST":
            return _trigger_scan(body)

        elif path.endswith("/regenerate") and method == "POST":
            job_id = path_params.get("id") or path.split("/jobs/")[1].split("/")[0]
            return _regenerate_documents(job_id)

        elif path == "/config" and method == "GET":
            return _get_config()

        elif path == "/config" and method == "PUT":
            return _update_config(body)

        elif path == "/dashboard/stats" and method == "GET":
            return _get_dashboard_stats()

        elif path == "/resumes" and method == "GET":
            return _list_resumes()

        elif path == "/resumes/summaries" and method == "GET":
            return _get_resume_summaries()

        elif path == "/resumes/summarize" and method == "POST":
            return _generate_resume_summaries()

        elif path == "/resumes/match" and method == "POST":
            return _match_resumes_to_jd(body)

        elif path == "/resumes" and method == "POST":
            return _upload_resume(body)

        elif path == "/resumes" and method == "DELETE":
            return _delete_resume(query_params)

        elif path.startswith("/documents/") and method == "GET":
            s3_key = path.split("/documents/")[1]
            return _get_document_url(s3_key)

        else:
            return _response(404, {"error": f"Not found: {method} {path}"})

    except Exception as e:
        logger.error(f"API error: {traceback.format_exc()}")
        return _response(500, {"error": str(e)})


# ── Handler Functions ──────────────────────────────────────────────────────────

def _list_jobs(params: dict) -> dict:
    """GET /jobs — List jobs with optional status filter."""
    status_filter = params.get("status")
    if status_filter:
        jobs = list_jobs_by_status(status_filter)
    else:
        jobs = list_all_jobs()

    # Convert to JSON-serializable list
    jobs_data = []
    for job in jobs:
        jobs_data.append({
            "job_id": job.job_id,
            "job_title": job.job_title,
            "company": job.company,
            "location": job.location,
            "date_posted": job.date_posted,
            "status": job.status,
            "match_score": job.match_score,
            "best_resume_name": job.best_resume_name,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        })

    # Sort by created_at descending
    jobs_data.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return _response(200, {"jobs": jobs_data, "total": len(jobs_data)})


def _get_job_detail(job_id: str) -> dict:
    """GET /jobs/{id} — Get full job details."""
    job = get_job(job_id)
    if not job:
        return _response(404, {"error": f"Job not found: {job_id}"})

    data = {
        "job_id": job.job_id,
        "job_url": job.job_url,
        "job_title": job.job_title,
        "company": job.company,
        "location": job.location,
        "date_posted": job.date_posted,
        "job_details": job.job_details[:5000],  # Limit for API response size
        "status": job.status,
        "jd_s3_path": job.jd_s3_path,
        "best_resume_name": job.best_resume_name,
        "match_score": job.match_score,
        "match_details": job.match_details,
        "optimized_resume_path": job.optimized_resume_path,
        "cover_letter_path": job.cover_letter_path,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }

    # Generate pre-signed URLs for documents
    if job.optimized_resume_path:
        data["optimized_resume_url"] = generate_presigned_url(job.optimized_resume_path)
    if job.cover_letter_path:
        data["cover_letter_url"] = generate_presigned_url(job.cover_letter_path)
    if job.jd_s3_path:
        data["jd_url"] = generate_presigned_url(job.jd_s3_path)

    return _response(200, data)


def _trigger_scan(body: dict) -> dict:
    """POST /jobs/scan — Manually trigger a job scan."""
    source_urls = body.get("source_urls")

    payload = {}
    if source_urls:
        payload["source_urls"] = source_urls

    try:
        lambda_client = config.get_lambda_client()
        lambda_client.invoke(
            FunctionName=os.environ.get("JOB_SCANNER_FUNCTION", "jobsys-job-scanner"),
            InvocationType="Event",
            Payload=json.dumps(payload),
        )
        return _response(202, {"message": "Scan triggered successfully"})
    except Exception as e:
        return _response(500, {"error": f"Failed to trigger scan: {str(e)}"})


def _regenerate_documents(job_id: str) -> dict:
    """POST /jobs/{id}/regenerate — Re-generate documents for a job."""
    job = get_job(job_id)
    if not job:
        return _response(404, {"error": f"Job not found: {job_id}"})

    # Reset status to trigger re-generation
    update_job_status(job_id, JobStatus.RESUME_MATCH_DONE)

    try:
        lambda_client = config.get_lambda_client()
        lambda_client.invoke(
            FunctionName=config.DOC_GENERATOR_FUNCTION,
            InvocationType="Event",
            Payload=json.dumps({"job_ids": [job_id]}),
        )
        return _response(202, {"message": f"Document regeneration triggered for job {job_id}"})
    except Exception as e:
        return _response(500, {"error": f"Failed to trigger regeneration: {str(e)}"})


def _get_config() -> dict:
    """GET /config — Get current configuration."""
    job_sources = config.get_config_value("job_sources")
    user_profile = config.get_config_value("user_profile")
    scrape_configs = config.get_config_value("scrape_configs")

    return _response(200, {
        "job_sources": job_sources,
        "user_profile": user_profile,
        "scrape_configs": scrape_configs,
    })


def _update_config(body: dict) -> dict:
    """PUT /config — Update configuration."""
    updated_keys = []

    if "job_sources" in body:
        config.put_config_value("job_sources", body["job_sources"])
        updated_keys.append("job_sources")

    if "user_profile" in body:
        config.put_config_value("user_profile", body["user_profile"])
        updated_keys.append("user_profile")

    if "scrape_configs" in body:
        config.put_config_value("scrape_configs", body["scrape_configs"])
        updated_keys.append("scrape_configs")

    return _response(200, {"message": "Configuration updated", "updated": updated_keys})


def _get_dashboard_stats() -> dict:
    """GET /dashboard/stats — Aggregate statistics for the dashboard."""
    all_jobs = list_all_jobs()

    stats = {
        "total_jobs": len(all_jobs),
        "new": 0,
        "resume_match_done": 0,
        "documents_ready": 0,
        "error": 0,
        "avg_match_score": 0,
        "recent_jobs": [],
    }

    scores = []
    for job in all_jobs:
        status = job.status
        if status == JobStatus.NEW:
            stats["new"] += 1
        elif status == JobStatus.RESUME_MATCH_DONE:
            stats["resume_match_done"] += 1
        elif status == JobStatus.DOCUMENTS_READY:
            stats["documents_ready"] += 1
        elif status == JobStatus.ERROR:
            stats["error"] += 1

        if job.match_score > 0:
            scores.append(job.match_score)

    if scores:
        stats["avg_match_score"] = round(sum(scores) / len(scores), 1)

    # Recent jobs (last 10)
    sorted_jobs = sorted(all_jobs, key=lambda j: j.created_at or "", reverse=True)
    stats["recent_jobs"] = [
        {
            "job_id": j.job_id,
            "job_title": j.job_title,
            "company": j.company,
            "status": j.status,
            "match_score": j.match_score,
            "created_at": j.created_at,
        }
        for j in sorted_jobs[:10]
    ]

    return _response(200, stats)


def _get_document_url(s3_key: str) -> dict:
    """GET /documents/{path+} — Get a pre-signed download URL."""
    try:
        url = generate_presigned_url(s3_key)
        return _response(200, {"url": url, "s3_key": s3_key})
    except Exception as e:
        return _response(404, {"error": f"Document not found: {str(e)}"})


def _get_resume_summaries() -> dict:
    """GET /resumes/summaries — Return stored resume summaries."""
    try:
        summaries = load_resume_summaries()
        return _response(200, {"summaries": summaries, "total": len(summaries)})
    except Exception as e:
        return _response(500, {"error": f"Failed to load summaries: {str(e)}"})


def _generate_resume_summaries() -> dict:
    """POST /resumes/summarize — Generate and store summaries for all base resumes."""
    try:
        from shared.gemini_client import summarize_resume
        from shared.parser import extract_text_from_file
        from concurrent.futures import ThreadPoolExecutor, as_completed

        resume_keys = list_base_resumes()
        if not resume_keys:
            return _response(200, {"message": "No resumes found", "summaries": []})

        logger.info(f"Generating summaries for {len(resume_keys)} resumes...")

        summaries = []
        errors = []

        def process_one(key):
            fname = key.split("/")[-1]
            try:
                fbytes = download_file_bytes(key)
                txt = extract_text_from_file(fbytes, fname)
                if not txt.strip():
                    return None, {"filename": fname, "error": "No text extracted"}
                
                sumry = summarize_resume(fname, txt)
                return sumry, None
            except Exception as ex:
                logger.error(f"Error processing {fname}: {ex}")
                return None, {"filename": fname, "error": str(ex)}

        # Process in parallel to avoid API Gateway 29s timeout
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_key = {executor.submit(process_one, k): k for k in resume_keys}
            for future in as_completed(future_to_key):
                res, err = future.result()
                if res:
                    summaries.append(res)
                if err:
                    errors.append(err)

        # Persist the successful ones to S3
        if summaries:
            save_resume_summaries(summaries)

        return _response(200, {
            "message": f"Processed {len(resume_keys)} resumes",
            "summaries": summaries,
            "errors": errors,
            "success_count": len(summaries),
            "error_count": len(errors)
        })
    except Exception as e:
        logger.error(f"Summarize main error: {traceback.format_exc()}")
        return _response(500, {"error": f"Internal server error: {str(e)}"})


def _match_resumes_to_jd(body: dict) -> dict:
    """POST /resumes/match — Score stored summaries against a JD using Gemini."""
    jd_text = body.get("jd_text", "").strip()
    if not jd_text:
        return _response(400, {"error": "Missing jd_text in request body"})

    job_meta = body.get("job_meta", {})

    try:
        from shared.gemini_client import match_jd_against_summaries

        summaries = load_resume_summaries()
        if not summaries:
            return _response(404, {"error": "No resume summaries found. Generate summaries first."})

        results = match_jd_against_summaries(jd_text, summaries, job_meta)
        return _response(200, {
            "results": results,
            "total": len(results),
            "best_match": results[0] if results else None,
        })
    except Exception as e:
        logger.error(f"Match error: {traceback.format_exc()}")
        return _response(500, {"error": f"Matching failed: {str(e)}"})


def _list_resumes() -> dict:
    """GET /resumes — List base resumes."""
    try:
        keys = list_base_resumes()
        resumes = []
        for key in keys:
            filename = key.split("/")[-1]
            if filename:
                resumes.append({
                    "filename": filename,
                    "s3_key": key,
                    "url": generate_presigned_url(key)
                })
        return _response(200, {"resumes": resumes})
    except Exception as e:
        return _response(500, {"error": f"Failed to list resumes: {str(e)}"})


def _upload_resume(body: dict) -> dict:
    """POST /resumes — Upload a new base resume."""
    filename = body.get("filename")
    content_b64 = body.get("content")

    if not filename or not content_b64:
        return _response(400, {"error": "Missing filename or content"})

    try:
        # Decode base64 content
        content = base64.b64decode(content_b64)
        s3_key = upload_base_resume(filename, content)
        
        return _response(201, {
            "message": "Resume uploaded successfully",
            "filename": filename,
            "s3_key": s3_key,
            "url": generate_presigned_url(s3_key)
        })
    except Exception as e:
        return _response(500, {"error": f"Failed to upload resume: {str(e)}"})


def _delete_resume(params: dict) -> dict:
    """DELETE /resumes?key=... — Delete a base resume."""
    s3_key = params.get("key")
    if not s3_key:
        return _response(400, {"error": "Missing S3 key"})

    # Security: Ensure it's in the base-resumes/ folder
    from shared import config
    if not s3_key.startswith(config.S3_BASE_RESUMES_PREFIX):
        return _response(403, {"error": "Unauthorized: Can only delete base resumes"})

    try:
        delete_file(s3_key)
        return _response(200, {"message": f"Resume deleted: {s3_key}"})
    except Exception as e:
        return _response(500, {"error": f"Failed to delete resume: {str(e)}"})


# ── Utilities ──────────────────────────────────────────────────────────────────

def _parse_body(event: dict) -> dict:
    """Parse the request body from an API Gateway event."""
    body = event.get("body")
    if not body:
        return {}
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return {}


def _response(status_code: int, body: dict) -> dict:
    """Build an API Gateway proxy response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body, default=str),
    }
