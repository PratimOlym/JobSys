"""Data models for the JobSys application."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List
import uuid


class JobStatus(str, Enum):
    """Status flow: new → resume-match-done → documents-ready → error."""
    NEW = "new"
    RESUME_MATCH_DONE = "resume-match-done"
    DOCUMENTS_READY = "documents-ready"
    ERROR = "error"


@dataclass
class Job:
    """Represents a job listing in the system."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_url: str = ""
    job_title: str = ""
    company: str = ""
    location: str = ""
    date_posted: str = ""
    job_details: str = ""
    status: str = JobStatus.NEW
    jd_s3_path: str = ""
    best_resume_name: str = ""
    match_score: float = 0.0
    match_details: Optional[Dict] = None
    optimized_resume_path: str = ""
    cover_letter_path: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dynamo_item(self) -> dict:
        """Convert to DynamoDB item format."""
        item = {
            "job_id": {"S": self.job_id},
            "job_url": {"S": self.job_url},
            "job_title": {"S": self.job_title},
            "company": {"S": self.company},
            "location": {"S": self.location},
            "date_posted": {"S": self.date_posted},
            "job_details": {"S": self.job_details},
            "status": {"S": self.status},
            "jd_s3_path": {"S": self.jd_s3_path},
            "best_resume_name": {"S": self.best_resume_name},
            "match_score": {"N": str(self.match_score)},
            "optimized_resume_path": {"S": self.optimized_resume_path},
            "cover_letter_path": {"S": self.cover_letter_path},
            "created_at": {"S": self.created_at},
            "updated_at": {"S": self.updated_at},
        }
        if self.match_details:
            # Store match_details as a JSON string in a String attribute
            import json
            item["match_details"] = {"S": json.dumps(self.match_details)}
        return item

    @classmethod
    def from_dynamo_item(cls, item: dict) -> "Job":
        """Create a Job from a DynamoDB item."""
        import json
        match_details = None
        if "match_details" in item and item["match_details"].get("S"):
            try:
                match_details = json.loads(item["match_details"]["S"])
            except (json.JSONDecodeError, TypeError):
                match_details = None

        return cls(
            job_id=item.get("job_id", {}).get("S", ""),
            job_url=item.get("job_url", {}).get("S", ""),
            job_title=item.get("job_title", {}).get("S", ""),
            company=item.get("company", {}).get("S", ""),
            location=item.get("location", {}).get("S", ""),
            date_posted=item.get("date_posted", {}).get("S", ""),
            job_details=item.get("job_details", {}).get("S", ""),
            status=item.get("status", {}).get("S", JobStatus.NEW),
            jd_s3_path=item.get("jd_s3_path", {}).get("S", ""),
            best_resume_name=item.get("best_resume_name", {}).get("S", ""),
            match_score=float(item.get("match_score", {}).get("N", "0")),
            match_details=match_details,
            optimized_resume_path=item.get("optimized_resume_path", {}).get("S", ""),
            cover_letter_path=item.get("cover_letter_path", {}).get("S", ""),
            created_at=item.get("created_at", {}).get("S", ""),
            updated_at=item.get("updated_at", {}).get("S", ""),
        )


@dataclass
class MatchResult:
    """Result of matching a resume against a JD."""
    resume_name: str
    overall_score: float
    keyword_score: float
    semantic_score: float
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict:
        return {
            "resume_name": self.resume_name,
            "overall_score": self.overall_score,
            "keyword_score": self.keyword_score,
            "semantic_score": self.semantic_score,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "recommendation": self.recommendation,
        }


@dataclass
class ResumeConfig:
    """User configuration for resume generation."""
    user_name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    job_source_urls: List[str] = field(default_factory=list)


@dataclass
class TokenUsageRecord:
    """A single LLM token-usage record stored in the ``jobsys-token-usage`` table.

    One record is written per LLM API call.  The ``remaining_tokens`` field is
    ``None`` for providers that do not expose quota information (Gemini, HF).
    """
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    provider: str = ""         # "gemini" | "openai" | "huggingface"
    model: str = ""            # e.g. "gpt-4o-mini"
    operation: str = ""        # e.g. "summarize_resume"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    remaining_tokens: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "record_id":         self.record_id,
            "timestamp":         self.timestamp,
            "provider":          self.provider,
            "model":             self.model,
            "operation":         self.operation,
            "prompt_tokens":     self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens":      self.total_tokens,
            "remaining_tokens":  self.remaining_tokens,
        }
