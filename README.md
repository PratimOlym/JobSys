# JobSys — CV Optimization & Job Application System

An AWS serverless system that automates job application preparation: scans job listings, matches resumes, generates ATS-optimized documents, and provides a web dashboard.

## Overview

JobSys is a comprehensive tool developed to streamline the job application process. It automates the extraction of job details from URLs, matches them against your base resumes using LLMs, and generates customized, ATS-friendly documents for each application.

## Key Components

- **`job_scanner`**: Automatically scrapes job listings from configured URLs and registers new jobs in DynamoDB.
- **`resume_matcher`**: Scores base resumes against Job Descriptions using advanced LLM-based semantic matching.
- **`document_generator`**: Extracts job-specific data and generates optimized DOCX resumes and cover letters.
- **`api_handler`**: Provides a REST API for the frontend dashboard.
- **`shared`**: Common utilities for S3, DynamoDB, and the multi-provider LLM abstraction layer.

## Architecture & Stack

```
EventBridge (daily 1 AM) → Job Scanner Lambda → Resume Matcher Lambda → Document Generator Lambda
                                                                               ↓
                                                        API Gateway → API Handler Lambda → React Dashboard
```

- **Backend**: AWS Lambda (Python 3.11+), DynamoDB, S3, EventBridge, API Gateway.
- **Frontend**: React (Vite), Framer Motion, Vanilla CSS.
- **LLM Layer**: Multi-provider abstraction supporting **Google Gemini** (Primary), OpenAI, and HuggingFace. Provider selection is managed via SSM Parameters.
- **Infrastructure**: Terraform (IaC).

See [COMMANDS.md](./COMMANDS.md) for a comprehensive list of commands for development and deployment. Detailed functional requirements are documented in [requirements.md](./requirements.md).

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
backend/                 # Python Lambda functions & shared logic
├── shared/              # DB, S3, LLM clients, configuration
├── job_scanner/         # Scraping & registration
├── resume_matcher/      # Scoring & matching
├── document_generator/  # Generation of DOCX/PDF
└── api_handler/         # REST API for the dashboard

frontend/                # React dashboard (Vite)

infra/                   # Terraform infrastructure code

scripts/                 # Automation scripts (PowerShell)
```

## Status Flow

```
new → resume-match-done → documents-ready
```
