# Testing Resume Matching

This guide outlines how to test the `resume_matcher` logic.

## Option 1: Direct File-Based Test (Recommended)
Use this to verify the LLM scoring and keyword matching without touching the database.

### 1. Create a Test JD
Create a file at `c:/Projects/JobSys/backend/test_jd.txt` with the content of the job description you want to test.

### 2. Run the Test Runner
Run the following script to see how your resumes match:
`python backend/scripts/test_matcher.py --jd backend/test_jd.txt`

---

## Option 2: End-to-End System Test
Use this to test the full Lambda workflow, including database updates and triggering the next step.

### 1. Upload JD to S3
Put your JD in the standard storage location:
`aws s3 cp my_jd.txt s3://jobsys-storage/job-descriptions/test-job-001/jd.txt --profile superclub-dev`

### 2. Create DynamoDB Record
The Lambda only processes jobs with `status = 'new'`.
```bash
aws dynamodb put-item \
    --table-name jobsys-jobs \
    --item '{
        "job_id": {"S": "test-job-001"},
        "job_title": {"S": "Senior DevOps Engineer"},
        "company": {"S": "TechCorp"},
        "status": {"N": "new"},
        "jd_s3_path": {"S": "job-descriptions/test-job-001/jd.txt"}
    }' \
    --profile superclub-dev
```

### 3. Invoke Lambda
`aws lambda invoke --function-name jobsys-resume-matcher --profile superclub-dev out.json`
