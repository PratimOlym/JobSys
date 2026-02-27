"""Job Scanner Lambda handler.

Triggered by EventBridge (daily schedule) or manual invocation.
Scans configured job source URLs, parses job listings,
deduplicates by URL, stores new jobs in DynamoDB and JDs in S3,
then invokes the Resume Matcher Lambda asynchronously.
"""

import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add shared module to path for Lambda execution
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared import config
from shared.db import create_job, job_exists_by_url
from shared.storage import upload_jd
from shared.models import Job, JobStatus
from job_scanner.scraper import scrape_job_listings, scrape_single_job_page
from shared.parser import extract_text_from_file


def handler(event, context):
    """Lambda entry point.

    Event can be:
      - EventBridge scheduled event (no special payload)
      - Manual invocation with {"source_urls": ["..."]} for ad-hoc scanning
    """
    logger.info(f"Job Scanner invoked. Event: {json.dumps(event, default=str)[:500]}")

    # Determine source URLs
    source_urls = event.get("source_urls") or config.get_job_source_urls()

    if not source_urls:
        logger.warning("No job source URLs configured. Exiting.")
        return {"statusCode": 200, "body": "No source URLs configured"}

    # Load scraping configurations (optional per-source CSS selectors)
    scrape_configs = config.get_config_value("scrape_configs") or {}

    new_jobs_count = 0
    skipped_count = 0
    error_count = 0

    for source_url in source_urls:
        logger.info(f"Processing source: {source_url}")
        try:
            # Get optional scrape config for this URL
            scrape_cfg = scrape_configs.get(source_url)

            # Scrape job listings
            scraped_jobs = scrape_job_listings(source_url, scrape_cfg)

            if not scraped_jobs:
                # If no listings found, try treating the URL as a single job page
                logger.info(f"No listings found, treating as single job page: {source_url}")
                single_job = scrape_single_job_page(source_url)
                if single_job.title or single_job.description:
                    scraped_jobs = [single_job]

            for scraped in scraped_jobs:
                try:
                    job_url = scraped.url or source_url

                    # Deduplication check by URL
                    if job_exists_by_url(job_url):
                        logger.debug(f"Skipping duplicate: {job_url}")
                        skipped_count += 1
                        continue

                    # If this is a listing (no description yet), fetch the detail page
                    if not scraped.description and scraped.url and scraped.url != source_url:
                        detail = scrape_single_job_page(scraped.url)
                        scraped.description = detail.description
                        if not scraped.title:
                            scraped.title = detail.title
                        if not scraped.company:
                            scraped.company = detail.company
                        if not scraped.location:
                            scraped.location = detail.location

                    # Create the job record
                    job = Job(
                        job_url=job_url,
                        job_title=scraped.title or "Untitled Position",
                        company=scraped.company,
                        location=scraped.location,
                        date_posted=scraped.date_posted,
                        job_details=scraped.description[:25000],  # DynamoDB item size limit
                        status=JobStatus.NEW,
                    )

                    # Store the JD in S3
                    jd_content = scraped.description.encode("utf-8")
                    jd_s3_key = upload_jd(job.job_id, job.job_title, jd_content, "txt")
                    job.jd_s3_path = jd_s3_key

                    # Persist to DynamoDB
                    create_job(job)
                    new_jobs_count += 1
                    logger.info(f"Registered new job: {job.job_title} at {job.company} ({job.job_id})")

                except Exception as e:
                    logger.error(f"Failed to process scraped job '{scraped.title}': {e}")
                    error_count += 1

        except Exception as e:
            logger.error(f"Failed to process source URL {source_url}: {e}")
            error_count += 1

    result = {
        "new_jobs": new_jobs_count,
        "skipped_duplicates": skipped_count,
        "errors": error_count,
    }
    logger.info(f"Job Scanner complete: {result}")

    # Trigger Resume Matcher if we found new jobs
    if new_jobs_count > 0:
        _invoke_resume_matcher()

    return {"statusCode": 200, "body": json.dumps(result)}


def _invoke_resume_matcher():
    """Asynchronously invoke the Resume Matcher Lambda."""
    try:
        lambda_client = config.get_lambda_client()
        lambda_client.invoke(
            FunctionName=config.RESUME_MATCHER_FUNCTION,
            InvocationType="Event",  # Async invocation
            Payload=json.dumps({"trigger": "job-scanner"}),
        )
        logger.info("Resume Matcher Lambda invoked asynchronously")
    except Exception as e:
        logger.error(f"Failed to invoke Resume Matcher: {e}")
