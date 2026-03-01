# JobSys — Commands Reference

This document lists the essential commands for setting up, deploying, and managing the JobSys application.

## 1. Prerequisites & Setup

Ensure you have the following installed:
- [AWS CLI](https://aws.amazon.com/cli/) (configured with `aws configure`)
- [Terraform](https://www.terraform.io/downloads.html) (>= 1.0)
- [Python 3.11+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)

### Initialize Backend Environment
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 2. Infrastructure Deployment (Terraform)

Use the automated script or run manual commands.

### Automated Setup
```powershell
.\scripts\deploy-infra.ps1
```
*Note: This script will create dummy ZIPs for first-time Terraform initialization if needed.*

### Manual Terraform Commands
```powershell
cd infra
terraform init
terraform plan
terraform apply -var="aws_region=ap-south-1"
```

---

## 3. Application Deployment

Deploys Lambda functions and (optionally) the frontend.

### Full Deployment (Lambdas + Frontend)
```powershell
.\scripts\deploy-lambdas.ps1 -DeployFrontend
```

### Lambda-only Deployment
```powershell
.\scripts\deploy-lambdas.ps1
```

### Manual Lambda Packaging
If you only want to package the functions without deploying:
```powershell
.\scripts\package-lambdas.ps1
```

---

## 4. Frontend Development

### Local Development Server
```powershell
cd frontend
npm install
npm run dev
```

### Build & Manual Upload to S3
```powershell
cd frontend
npm run build
aws s3 sync dist/ s3://jobsys-frontend/ --delete
```

---

## 5. Testing

### Run Backend Tests
Ensure your virtual environment is active.
```powershell
python -m pytest backend/tests/ -v
```

---

## 6. Manual Operations (AWS CLI)

### Upload Base Resumes to S3
```powershell
aws s3 cp my-resume.docx s3://jobsys-storage/base-resumes/
```

### Configure Job Sources in DynamoDB
```powershell
aws dynamodb put-item --table-name jobsys-config --item '{
  "config_key": {"S": "job_sources"},
  "config_value": {"S": "{\"urls\": [\"https://example.com/jobs\"]}"}
}'
```

---

## 7. Troubleshooting

### View Lambda Logs
Replace `FUNCTION_NAME` with `job-scanner`, `resume-matcher`, etc.
```powershell
aws logs tail /aws/lambda/jobsys-FUNCTION_NAME --follow
```

### Destroy Infrastructure
```powershell
cd infra
terraform destroy
```
