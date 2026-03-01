"""LLM-powered semantic matching.

Combines keyword scoring with LLM semantic analysis for a comprehensive
resume-vs-JD matching score.  The active LLM provider is controlled by the
``LLM_PROVIDER`` environment variable (gemini | openai | huggingface).
"""

import logging
from typing import Dict

from shared.llm_client import score_resume_vs_jd
from shared.models import MatchResult
from resume_matcher.scorer import compute_keyword_score, compute_cosine_similarity

logger = logging.getLogger(__name__)

# Weights for combining scores
KEYWORD_WEIGHT = 0.3
COSINE_WEIGHT = 0.2
SEMANTIC_WEIGHT = 0.5


def match_resume_to_jd(
    resume_name: str,
    resume_text: str,
    jd_text: str,
    job_meta: Dict,
) -> MatchResult:
    """Perform a comprehensive match of a resume against a JD.

    Combines three scoring methods:
    1. Keyword overlap scoring (30% weight)
    2. Cosine similarity (20% weight)
    3. Gemini semantic analysis (50% weight)

    Args:
        resume_name: Identifier for this base resume.
        resume_text: Full text of the resume.
        jd_text: Full text of the job description.
        job_meta: Dict with job_title, company, location.

    Returns:
        MatchResult with combined scores and skill analysis.
    """
    # 1. Keyword-based scoring
    keyword_result = compute_keyword_score(jd_text, resume_text)
    keyword_score = keyword_result["score"]

    # 2. Cosine similarity
    cosine_sim = compute_cosine_similarity(jd_text, resume_text) * 100  # Scale to 0-100

    # 3. Gemini semantic scoring
    semantic_result = score_resume_vs_jd(resume_text, jd_text, job_meta)
    semantic_score = semantic_result.overall_score

    # Combined weighted score
    overall_score = (
        KEYWORD_WEIGHT * keyword_score
        + COSINE_WEIGHT * cosine_sim
        + SEMANTIC_WEIGHT * semantic_score
    )

    logger.info(
        f"Match scores for '{resume_name}': "
        f"keyword={keyword_score:.1f}, cosine={cosine_sim:.1f}, "
        f"semantic={semantic_score:.1f}, overall={overall_score:.1f}"
    )

    return MatchResult(
        resume_name=resume_name,
        overall_score=round(overall_score, 1),
        keyword_score=round(keyword_score, 1),
        semantic_score=round(semantic_score, 1),
        matched_skills=semantic_result.matched_skills or keyword_result.get("matched_keywords", []),
        missing_skills=semantic_result.missing_skills or keyword_result.get("missing_keywords", []),
        recommendation=semantic_result.recommendation,
    )
