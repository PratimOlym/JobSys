# JobSys Documentation Guide

This directory contains the documentation for the JobSys CV Optimization & Job Application System.

## Main Documentation

- [README.md](./README.md): Project overview, architecture, and quick start guide.
- [COMMANDS.md](./COMMANDS.md): Comprehensive list of all development, deployment, and manual commands.
- [Requirement Doc](./Requirement Doc.pdf): Project requirements and features overview.

## Project Structure

- `backend/`: Python-based AWS Lambda functions and shared logic.
- `frontend/`: React-based dashboard (Vite).
- `infra/`: Terraform configurations for AWS infrastructure.
- `scripts/`: PowerShell scripts for automation (packaging, deployment).

## Key Components

### 1. Backend Service
- **`job_scanner`**: Scrapes Job URLs and registers new jobs in DynamoDB.
- **`resume_matcher`**: Scores resumes against Job Descriptions using LLMs.
- **`document_generator`**: Extracts data and generates ATS-optimized DOCX resumes.
- **`api_handler`**: Provides REST API for the frontend dashboard.
- **`shared`**: Common utilities for S3, DynamoDB, and LLM abstraction.

### 2. LLM Abstraction Layer
The system uses a multi-provider LLM abstraction that supports:
- **Google Gemini** (Primary)
- **OpenAI** (Fallback/Alternative)
- **HuggingFace** (Alternative)

This layer is managed through SSM Parameters for provider and model selection.

### 3. Frontend Dashboard
A modern React application that displays job status, scores, and allows downloading generated resumes.
- **Technologies**: React, Vite, Framer Motion, Vanilla CSS.

---

For any questions, refer to the [README.md](./README.md).
