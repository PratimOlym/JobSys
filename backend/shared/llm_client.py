"""Public LLM facade for JobSys.

This is the single import point for all LLM-powered operations.
It is a drop-in replacement for ``shared.gemini_client``; every function
has an identical signature and return type.

Switch providers via the ``LLM_PROVIDER`` environment variable (or AWS SSM):
    ``gemini``      — Google Gemini  (default)
    ``openai``      — OpenAI
    ``huggingface`` — HuggingFace Inference API

Token usage is automatically logged and persisted to DynamoDB after every call.
"""

import json
import logging
from typing import Dict, List, Optional

from . import config as app_config
from .llm_provider import LLMProvider
from .llm_types import LLMResponse, TokenUsage
from .models import MatchResult

logger = logging.getLogger(__name__)

# ── Provider singleton (lazy) ─────────────────────────────────────────────────

_provider: Optional[LLMProvider] = None


def get_provider() -> LLMProvider:
    """Return the active provider singleton, initialising on first call."""
    global _provider
    if _provider is None:
        _provider = _build_provider()
    return _provider


def _build_provider() -> LLMProvider:
    """Instantiate the provider selected by configuration."""
    provider_name = app_config.get_llm_provider()
    logger.info("Initialising LLM provider: %s", provider_name)

    if provider_name == "openai":
        from .providers.openai_provider import OpenAIProvider
        api_key = app_config.get_openai_api_key()
        model = app_config.get_llm_model("openai")
        return OpenAIProvider(api_key=api_key, model=model)

    if provider_name == "huggingface":
        from .providers.huggingface_provider import HuggingFaceProvider
        api_key = app_config.get_hf_api_key()
        model = app_config.get_llm_model("huggingface")
        return HuggingFaceProvider(api_key=api_key, model=model)

    # Default: Gemini
    from .providers.gemini_provider import GeminiProvider
    api_key = app_config.get_gemini_api_key()
    model = app_config.get_llm_model("gemini")
    return GeminiProvider(api_key=api_key, model=model)


# ── Internal helpers ──────────────────────────────────────────────────────────


def _call(prompt: str, operation: str) -> LLMResponse:
    """Send *prompt* through the active provider, record usage, return response."""
    provider = get_provider()
    response = provider.generate(prompt)
    _record_usage(response, operation)
    return response


def _strip_fences(text: str) -> str:
    """Remove markdown code fences (``` … ```) that some models add."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _record_usage(response: LLMResponse, operation: str) -> None:
    """Log token usage and persist to DynamoDB (best-effort)."""
    u = response.usage
    logger.info(
        "Token usage [%s/%s] op=%s — prompt=%d completion=%d total=%d remaining=%s",
        response.provider,
        response.model,
        operation,
        u.prompt_tokens,
        u.completion_tokens,
        u.total_tokens,
        u.remaining_tokens if u.remaining_tokens is not None else "N/A",
    )
    try:
        app_config.record_token_usage(
            usage=u,
            provider=response.provider,
            model=response.model,
            operation=operation,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not persist token usage to DynamoDB: %s", exc)


# ── Public API (identical signatures to gemini_client.py) ────────────────────


def summarize_resume(resume_name: str, resume_text: str) -> Dict:
    """Generate a concise, structured summary of a resume.

    Args:
        resume_name: Filename / identifier of the resume.
        resume_text: Full extracted text of the resume.

    Returns:
        Dict with keys: resume_name, headline, total_experience_years, skills,
        key_strengths, education, summary_text.
    """
    prompt = f"""You are an expert resume analyst.

Analyze the following resume and produce a concise, structured summary.

## Resume: {resume_name}
{resume_text}

## Instructions
Return ONLY a JSON object with EXACTLY these fields:
{{
    "headline": "<one-line professional headline, e.g. 'Senior Full-Stack Engineer with 6 years in fintech'>",
    "total_experience_years": <number, estimated total years of professional experience>,
    "skills": ["<skill1>", "<skill2>", ...],
    "key_strengths": ["<strength1>", "<strength2>", "<strength3>"],
    "education": "<highest degree and institution>",
    "summary_text": "<2-3 sentence professional paragraph summarizing this person>"
}}

Respond with ONLY the JSON object, no other text.
"""
    try:
        response = _call(prompt, "summarize_resume")
        data = json.loads(_strip_fences(response.text))
        data["resume_name"] = resume_name
        return data
    except Exception as e:
        logger.error("Resume summarization failed for '%s': %s", resume_name, e)
        return {
            "resume_name": resume_name,
            "headline": "Summary generation failed",
            "total_experience_years": 0,
            "skills": [],
            "key_strengths": [],
            "education": "",
            "summary_text": f"Error: {str(e)}",
        }


def match_jd_against_summaries(
    jd_text: str, summaries: List[Dict], job_meta: Dict = None
) -> List[Dict]:
    """Score a JD against a list of resume summaries.

    Args:
        jd_text: Full text of the job description.
        summaries: List of resume summary dicts (from load_resume_summaries).
        job_meta: Optional dict with job_title, company, location.

    Returns:
        List of result dicts ordered by overall_score descending.
    """
    if not summaries:
        return []

    job_meta = job_meta or {}

    summaries_block = ""
    for i, s in enumerate(summaries, 1):
        summaries_block += f"""
--- Resume {i}: {s.get('resume_name', f'Resume_{i}')} ---
Headline: {s.get('headline', '')}
Experience: {s.get('total_experience_years', 'N/A')} years
Education: {s.get('education', '')}
Skills: {', '.join(s.get('skills', []))}
Key Strengths: {', '.join(s.get('key_strengths', []))}
Summary: {s.get('summary_text', '')}
"""

    prompt = f"""You are an expert ATS analyst and career advisor.

## Job Information
- Title: {job_meta.get('job_title', 'Not specified')}
- Company: {job_meta.get('company', 'Not specified')}
- Location: {job_meta.get('location', 'Not specified')}

## Job Description
{jd_text}

## Resume Summaries to Evaluate
{summaries_block}

## Instructions
For EACH resume above, evaluate how well it matches this job description.
Return a JSON array where each element corresponds to one resume (in the same order):
[
  {{
    "resume_name": "<exact resume name from the summary header>",
    "overall_score": <integer 0-100, overall match percentage>,
    "keyword_score": <integer 0-100, keyword/skill overlap>,
    "semantic_score": <integer 0-100, experience & context alignment>,
    "matched_skills": ["<skill found in both JD and resume>", ...],
    "missing_skills": ["<important JD skill NOT in this resume>", ...],
    "recommendation": "<one-sentence actionable suggestion for this resume>"
  }},
  ...
]

Important:
- Be precise and differentiated — avoid giving everyone the same score.
- Base scores on the summary data, not fabricated assumptions.
- Respond with ONLY the JSON array, no other text.
"""

    try:
        response = _call(prompt, "match_jd_against_summaries")
        results = json.loads(_strip_fences(response.text))
        results.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
        return results
    except Exception as e:
        logger.error("JD matching failed: %s", e)
        return [
            {
                "resume_name": s.get("resume_name", f"Resume_{i}"),
                "overall_score": 0,
                "keyword_score": 0,
                "semantic_score": 0,
                "matched_skills": [],
                "missing_skills": [],
                "recommendation": f"Scoring failed: {str(e)}",
            }
            for i, s in enumerate(summaries, 1)
        ]


def score_resume_vs_jd(resume_text: str, jd_text: str, job_meta: Dict) -> MatchResult:
    """Semantically score a resume against a job description.

    Args:
        resume_text: Full text of the base resume.
        jd_text: Full text of the job description.
        job_meta: Additional job metadata (title, company, location).

    Returns:
        MatchResult with scores and skill analysis.
    """
    prompt = f"""You are an expert ATS (Applicant Tracking System) analyst and career advisor.

Analyze the following resume against the job description and provide a detailed matching assessment.

## Job Information
- **Title**: {job_meta.get('job_title', 'N/A')}
- **Company**: {job_meta.get('company', 'N/A')}
- **Location**: {job_meta.get('location', 'N/A')}

## Job Description
{jd_text}

## Resume
{resume_text}

## Instructions
Provide your analysis as a JSON object with EXACTLY these fields:
{{
    "overall_score": <number 0-100, overall match percentage>,
    "keyword_score": <number 0-100, how well keywords match>,
    "semantic_score": <number 0-100, how well experience/skills semantically align>,
    "matched_skills": [<list of skills/keywords found in both resume and JD>],
    "missing_skills": [<list of important JD skills/keywords NOT in the resume>],
    "recommendation": "<brief recommendation on which areas of the resume to enhance>"
}}

Respond with ONLY the JSON object, no other text.
"""

    try:
        response = _call(prompt, "score_resume_vs_jd")
        data = json.loads(_strip_fences(response.text))
        return MatchResult(
            resume_name="",  # Filled in by caller
            overall_score=float(data.get("overall_score", 0)),
            keyword_score=float(data.get("keyword_score", 0)),
            semantic_score=float(data.get("semantic_score", 0)),
            matched_skills=data.get("matched_skills", []),
            missing_skills=data.get("missing_skills", []),
            recommendation=data.get("recommendation", ""),
        )
    except Exception as e:
        logger.error("Resume scoring failed: %s", e)
        return MatchResult(
            resume_name="",
            overall_score=0,
            keyword_score=0,
            semantic_score=0,
            recommendation=f"Error during scoring: {str(e)}",
        )


def generate_optimized_resume_content(
    base_resume_text: str, jd_text: str, job_meta: Dict, match_result: MatchResult
) -> Dict:
    """Generate optimized resume content tailored to the JD.

    Args:
        base_resume_text: Text of the best-matching base resume.
        jd_text: Full job description text.
        job_meta: Job metadata dict.
        match_result: Previous matching analysis.

    Returns:
        Dict with structured resume sections ready for DOCX generation.
    """
    prompt = f"""You are an expert resume writer specializing in ATS-optimized resumes.

Your task is to optimize the following base resume for the specific job description below.
Focus ONLY on relevant skills and keywords. Make the resume ATS-friendly and professional.

## Job Information
- **Title**: {job_meta.get('job_title', 'N/A')}
- **Company**: {job_meta.get('company', 'N/A')}
- **Location**: {job_meta.get('location', 'N/A')}

## Job Description
{jd_text}

## Base Resume
{base_resume_text}

## Previous Analysis
- **Matched Skills**: {', '.join(match_result.matched_skills)}
- **Missing Skills**: {', '.join(match_result.missing_skills)}
- **Recommendation**: {match_result.recommendation}

## Instructions
Generate an optimized resume as a JSON object with these sections:
{{
    "contact_info": {{
        "name": "<name from base resume>",
        "email": "<email>",
        "phone": "<phone>",
        "linkedin": "<linkedin url if available>",
        "location": "<location>"
    }},
    "professional_summary": "<2-3 sentence summary tailored to this specific role>",
    "skills": ["<skill1>", "<skill2>", ...],
    "experience": [
        {{
            "title": "<job title>",
            "company": "<company>",
            "duration": "<date range>",
            "bullets": ["<achievement 1>", "<achievement 2>", ...]
        }}
    ],
    "education": [
        {{
            "degree": "<degree>",
            "institution": "<school>",
            "year": "<graduation year>"
        }}
    ],
    "certifications": ["<cert1>", "<cert2>", ...],
    "additional_sections": {{}}
}}

IMPORTANT:
- Keep all factual information from the base resume intact.
- Rephrase and optimize bullet points to align with JD keywords.
- Highlight missing skills only if they can be reasonably inferred from existing experience.
- Do NOT fabricate experience or qualifications.

Respond with ONLY the JSON object, no other text.
"""

    try:
        response = _call(prompt, "generate_optimized_resume_content")
        return json.loads(_strip_fences(response.text))
    except Exception as e:
        logger.error("Resume generation failed: %s", e)
        raise


def generate_cover_letter_content(
    resume_text: str, jd_text: str, job_meta: Dict, user_profile: Dict
) -> str:
    """Generate a tailored cover letter.

    Args:
        resume_text: The optimized resume text.
        jd_text: Full job description text.
        job_meta: Job metadata dict.
        user_profile: User's profile info (name, email, etc.).

    Returns:
        Cover letter text as a string.
    """
    user_name = user_profile.get("name", "Applicant")

    prompt = f"""You are an expert cover letter writer.

Write a compelling, professional cover letter for the following job application.

## Applicant
- **Name**: {user_name}
- **Email**: {user_profile.get('email', '')}
- **Phone**: {user_profile.get('phone', '')}

## Job Information
- **Title**: {job_meta.get('job_title', 'N/A')}
- **Company**: {job_meta.get('company', 'N/A')}
- **Location**: {job_meta.get('location', 'N/A')}

## Job Description
{jd_text}

## Applicant's Resume Summary
{resume_text[:3000]}

## Instructions
- Write a professional cover letter (3-4 paragraphs).
- Address it to the Hiring Manager.
- Highlight the most relevant experience and skills.
- Show enthusiasm for the specific company and role.
- Keep it concise and impactful.
- Do NOT include any JSON formatting — return plain text only.
- Include the date, applicant's address/contact at the top, and proper sign-off.

Write the complete cover letter below:
"""

    try:
        response = _call(prompt, "generate_cover_letter_content")
        return response.text.strip()
    except Exception as e:
        logger.error("Cover letter generation failed: %s", e)
        raise
