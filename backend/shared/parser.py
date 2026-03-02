"""Shared parsing utilities for JobSys.

Parses content from various formats: HTML pages, PDF files, and DOCX files.
Extracts structured fields from raw job posting text or resumes.
"""

import io
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedJobDetails:
    """Structured fields extracted from a raw job description."""
    title: str = ""
    company: str = ""
    location: str = ""
    date_posted: str = ""
    description: str = ""
    requirements: str = ""
    responsibilities: str = ""
    salary_range: str = ""
    employment_type: str = ""
    experience_level: str = ""


def parse_jd_text(raw_text: str) -> ParsedJobDetails:
    """Parse raw JD text and extract structured fields.

    Uses regex patterns to identify common sections in job postings.
    """
    parsed = ParsedJobDetails()
    parsed.description = raw_text

    # Extract sections by common headings
    sections = _split_into_sections(raw_text)

    for heading, content in sections.items():
        heading_lower = heading.lower()
        if any(kw in heading_lower for kw in ["requirement", "qualification", "must have", "skills needed"]):
            parsed.requirements = content
        elif any(kw in heading_lower for kw in ["responsibilit", "duties", "what you'll do", "role"]):
            parsed.responsibilities = content
        elif any(kw in heading_lower for kw in ["salary", "compensation", "pay"]):
            parsed.salary_range = content
        elif any(kw in heading_lower for kw in ["experience", "level", "seniority"]):
            parsed.experience_level = content

    # Try to extract employment type
    emp_match = re.search(
        r"\b(full[- ]time|part[- ]time|contract|freelance|temporary|intern(?:ship)?)\b",
        raw_text, re.IGNORECASE
    )
    if emp_match:
        parsed.employment_type = emp_match.group(0)

    return parsed


def parse_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text content from a PDF file's bytes.

    Uses PyPDF2 for extraction; falls back gracefully if not available.
    """
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        
        text = "\n\n".join(text_parts)
        # Collapse multiple newlines (3+) to just 2, and normalize spaces
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()
    except ImportError:
        logger.warning("PyPDF2 not available — PDF parsing skipped")
        return ""
    except Exception as e:
        logger.error(f"PDF parsing failed: {e}")
        return ""


def parse_docx_bytes(docx_bytes: bytes) -> str:
    """Extract text content from a DOCX file's bytes."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(docx_bytes))
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except ImportError:
        logger.warning("python-docx not available — DOCX parsing skipped")
        return ""
    except Exception as e:
        logger.error(f"DOCX parsing failed: {e}")
        return ""


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Extract text from a file based on its extension.

    Args:
        file_bytes: Raw file content.
        filename: Filename to determine format.

    Returns:
        Extracted text string.
    """
    if not filename:
        return ""
        
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        return parse_pdf_bytes(file_bytes)
    elif ext == "docx":
        return parse_docx_bytes(file_bytes)
    elif ext in ("txt", "text", "md"):
        try:
            return file_bytes.decode("utf-8", errors="replace")
        except Exception:
            return ""
    else:
        # Try as plain text
        try:
            return file_bytes.decode("utf-8", errors="replace")
        except Exception:
            return ""


# ── Internal Helpers ───────────────────────────────────────────────────────────

def _split_into_sections(text: str) -> dict:
    """Split text into sections based on heading-like patterns.

    Common patterns: "Requirements:", "## Responsibilities", "QUALIFICATIONS", etc.
    """
    # Match lines that look like section headings
    heading_pattern = re.compile(
        r"^(?:#{1,4}\s+)?([A-Z][A-Za-z\s/&,]{2,50}):?\s*$",
        re.MULTILINE
    )

    sections = {}
    matches = list(heading_pattern.finditer(text))

    for i, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if content:
            sections[heading] = content

    return sections
