# JobSys — CV Optimization & Job Application System

An AWS serverless system that automates job application preparation: scans job listings, matches resumes, generates ATS-optimized documents, and provides a web dashboard.

## Architecture

```
EventBridge (daily 1 AM) → Job Scanner Lambda → Resume Matcher Lambda → Document Generator Lambda
                                                                              ↓
                                                       API Gateway → API Handler Lambda → React Dashboard
```

**Stack**: AWS Lambda, DynamoDB, S3, EventBridge, API Gateway, Google Gemini, React

See [DOCS.md](./DOCS.md) for detailed documentation on project components and [COMMANDS.md](./COMMANDS.md) for a comprehensive list of commands for development and deployment.


## Quick Start

### Prerequisites
- AWS CLI configured (`aws configure`)
- Terraform >= 1.0
- Python 3.11+
- Node.js 18+
- Google Gemini API key

### 1. Package Lambda Functions
```powershell
.\scripts\package-lambdas.ps1
```

### 2. Deploy Infrastructure
```powershell
cd infra
terraform init
terraform apply -var="gemini_api_key=YOUR_KEY"
```

### 3. Upload Base Resumes
```powershell
aws s3 cp ./my-resume.docx s3://jobsys-storage/base-resumes/
```

### 4. Configure Job Sources
```powershell
aws dynamodb put-item --table-name jobsys-config --item '{
  "config_key": {"S": "job_sources"},
  "config_value": {"S": "{\"urls\": [\"https://example.com/jobs\"]}"}
}'
```

### 5. Build & Deploy Frontend
```powershell
cd frontend
npm install
# Update API URL in src/services/api.js
npm run build
aws s3 sync dist/ s3://jobsys-frontend/
```

## Project Structure

```
backend/                 # Lambda functions & shared code
├── shared/              # DB, S3, Gemini client, config
├── job_scanner/         # Scrapes & registers new jobs
├── resume_matcher/      # Scores resumes against JDs
├── document_generator/  # Generates optimized DOCX files
└── api_handler/         # REST API for the dashboard

frontend/                # React dashboard (Vite)

infra/                   # Terraform IaC
```

## Status Flow

```
new → resume-match-done → documents-ready
```
