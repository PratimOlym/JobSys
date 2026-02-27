import unittest
import json
from datetime import datetime
from backend.shared.models import Job, JobStatus

class TestModels(unittest.TestCase):
    def test_job_creation(self):
        job = Job(
            job_url="https://example.com/job",
            job_title="Software Engineer",
            company="Example Corp",
            location="Remote"
        )
        self.assertEqual(job.job_title, "Software Engineer")
        self.assertEqual(job.status, JobStatus.NEW)
        self.assertTrue(len(job.job_id) > 0)
        self.assertTrue(isinstance(job.created_at, str))

    def test_job_to_dynamo_item(self):
        job = Job(
            job_id="test-id",
            job_url="https://example.com/job",
            job_title="Software Engineer",
            company="Example Corp",
            match_score=85.5,
            match_details={"skills": ["Python", "AWS"]}
        )
        item = job.to_dynamo_item()
        
        self.assertEqual(item["job_id"]["S"], "test-id")
        self.assertEqual(item["job_title"]["S"], "Software Engineer")
        self.assertEqual(item["match_score"]["N"], "85.5")
        
        match_details = json.loads(item["match_details"]["S"])
        self.assertEqual(match_details["skills"], ["Python", "AWS"])

    def test_job_from_dynamo_item(self):
        item = {
            "job_id": {"S": "test-id"},
            "job_url": {"S": "https://example.com/job"},
            "job_title": {"S": "Software Engineer"},
            "company": {"S": "Example Corp"},
            "location": {"S": "Remote"},
            "date_posted": {"S": "2023-01-01"},
            "job_details": {"S": "Details"},
            "status": {"S": "new"},
            "jd_s3_path": {"S": "s3://path"},
            "best_resume_name": {"S": "resume.pdf"},
            "match_score": {"N": "85.5"},
            "match_details": {"S": json.dumps({"skills": ["Python", "AWS"]})},
            "optimized_resume_path": {"S": "s3://opt"},
            "cover_letter_path": {"S": "s3://cl"},
            "created_at": {"S": "2023-01-01T00:00:00"},
            "updated_at": {"S": "2023-01-01T00:00:00"},
        }
        
        job = Job.from_dynamo_item(item)
        self.assertEqual(job.job_id, "test-id")
        self.assertEqual(job.match_score, 85.5)
        self.assertEqual(job.match_details["skills"], ["Python", "AWS"])

if __name__ == "__main__":
    unittest.main()
