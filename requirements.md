# CV Optimization and Job Application System — Requirements

## Overview

This system automates job application preparation by scanning job listings, matching them against base resumes, generating optimized ATS-ready resumes and cover letters, and tracking the full workflow through a database-driven pipeline.

---

## Phase 1 — Job Ingestion & Registration

### 1.1 Scanning & Sourcing
- The program scans a **configurable list of job links** (maintained in a configuration file/table).
- It can also read job details from **PDFs/DOCs stored in cloud storage (S3)**.

### 1.2 Identification & Parsing
- Each job source is parsed to identify **new job listings** not already present in the database.
- **Duplicate detection** is performed using the **job URL** — if a URL already exists in the database, the job is skipped.

### 1.3 Database Registration
New jobs are registered in a DynamoDB table with the following fields:

| Field           | Description                          |
|-----------------|--------------------------------------|
| Job Name/Title  | The title of the job posting         |
| Location        | Job location                         |
| Date of Posting | When the job was posted              |
| Company         | The hiring company                   |
| Job Details     | Full job description text            |
| Status          | Set to `new` on initial registration |

---

## Phase 2 — Job Description (JD) & Resume Storage

### 2.1 JD Storage
- The JD for each new job is saved to a designated S3 folder: **`job-descriptions/`**
- The folder/filename incorporates the job's **unique DB ID** and **job title**.
- The DB record is updated with the **S3 path/link** to the stored JD.

### 2.2 Base Resume Storage
- A collection of standard/base CVs is maintained in an S3 folder: **`base-resumes/`**
- These serve as templates that get optimized per-job.

---

## Phase 3 — Resume Optimization & Matching (Automated)

### 3.1 Scheduled Scan
- The program runs on a **scheduled trigger** (e.g., daily at 1 AM via EventBridge) and scans the DB for job records with status = `new`.

### 3.2 Matching & Scoring
For each pending job:
1. The relevant JD is retrieved from the **`job-descriptions/`** S3 folder.
2. Each base resume from **`base-resumes/`** is scored against the JD.
3. The **highest-scoring base resume** is selected.

**Matching approach:**
- Keyword extraction + cosine similarity scoring
- Enhanced by **LLM-based semantic matching** (Google Gemini)
- Leverages job details (location, date, company, description) to improve matching

### 3.3 Database Update (Matching Results)
The DB record is updated with:

| Field              | Description                              |
|--------------------|------------------------------------------|
| Field-matching info| Which fields/skills matched              |
| Base-resume score  | The match score of the best base resume  |
| Status             | Updated to `resume-match-done`           |

---

## Phase 4 — Optimized Document Generation

### 4.1 Optimized Resume Generation
Using the selected base resume and the JD, the system generates an **ATS-ready, professional resume**:
- Expands/optimizes the base resume specifically for the JD
- Focuses only on **relevant skills and keywords**
- Output includes only content that requires updating based on the JD

### 4.2 Optimized Resume Storage
- Stored in S3 folder: **`resume-optimized/`**
- Filename format: `{MyName}_{JobName}_{JobID}.docx`

### 4.3 Cover Letter Generation
- A **job-optimized cover letter** is generated and stored in S3 folder: **`cover-letters/`**
- Output format: DOCX

---

## Phase 5 — Final Database Updates

### 5.1 Record Finalization
The DB table is updated with the final application information:

| Field                     | Description                                |
|---------------------------|--------------------------------------------|
| Status                    | Updated to `documents-ready`               |
| Path to Optimized Resume  | S3 path to the generated resume            |
| Path to Cover Letter      | S3 path to the generated cover letter      |

---

## Technology Decisions

| Component        | Choice                                   |
|------------------|------------------------------------------|
| Compute          | AWS Lambda (serverless)                  |
| Storage          | AWS S3                                   |
| Database         | AWS DynamoDB                             |
| LLM Provider     | Google Gemini                            |
| Scheduler        | AWS EventBridge                          |
| Document Format  | DOCX                                     |
| Duplicate Check  | By job URL                               |
| Job Sources      | Configurable list of links               |
| UI               | Web dashboard (static site or React)     |
| IaC              | Terraform                                |

---

## Status Flow

```
new → resume-match-done → documents-ready
```
