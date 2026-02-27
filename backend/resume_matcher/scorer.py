"""Keyword-based resume scoring using TF-IDF and cosine similarity."""

import logging
import math
import re
from collections import Counter
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Common English stop words to exclude from keyword analysis
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "he", "in", "is", "it", "its", "of", "on", "or", "she", "that",
    "the", "to", "was", "were", "will", "with", "this", "but", "they", "not",
    "we", "you", "our", "your", "all", "can", "had", "i", "would", "their",
    "what", "so", "up", "out", "if", "about", "who", "get", "which", "go",
    "me", "when", "make", "like", "no", "just", "over", "such", "us", "also",
    "been", "do", "than", "other", "into", "more", "some", "any", "how",
    "may", "each", "should", "her", "him", "being", "did", "very", "must",
    "my", "could", "these", "here", "through", "between", "both", "under",
    "etc", "able", "work", "working", "well", "years", "year", "using",
    "experience", "team", "role", "company", "job", "position", "looking",
    "candidate", "required", "preferred", "strong", "good", "excellent",
}


def extract_keywords(text: str, top_n: int = 50) -> List[Tuple[str, float]]:
    """Extract the top-N keywords from text using term frequency.

    Args:
        text: Input text to analyze.
        top_n: Number of top keywords to return.

    Returns:
        List of (keyword, score) tuples, sorted by score descending.
    """
    tokens = _tokenize(text)
    if not tokens:
        return []

    tf = Counter(tokens)
    total = len(tokens)

    # Compute normalized TF scores
    scored = [
        (word, count / total)
        for word, count in tf.items()
        if word not in STOP_WORDS and len(word) > 2
    ]

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]


def compute_keyword_score(jd_text: str, resume_text: str) -> Dict:
    """Compute a keyword overlap score between a JD and a resume.

    Args:
        jd_text: Job description text.
        resume_text: Resume text.

    Returns:
        Dict with score (0-100), matched keywords, and missing keywords.
    """
    jd_keywords = extract_keywords(jd_text, top_n=40)
    resume_keywords = extract_keywords(resume_text, top_n=60)

    jd_keyword_set = {kw for kw, _ in jd_keywords}
    resume_keyword_set = {kw for kw, _ in resume_keywords}

    # Also check for keywords in the full resume text (not just top-N)
    resume_tokens = set(_tokenize(resume_text))

    matched = []
    missing = []

    for kw, weight in jd_keywords:
        if kw in resume_keyword_set or kw in resume_tokens:
            matched.append(kw)
        else:
            missing.append(kw)

    # Score: percentage of JD keywords found in resume
    score = (len(matched) / len(jd_keyword_set) * 100) if jd_keyword_set else 0

    return {
        "score": round(score, 1),
        "matched_keywords": matched,
        "missing_keywords": missing,
    }


def compute_cosine_similarity(text_a: str, text_b: str) -> float:
    """Compute cosine similarity between two text documents.

    Uses simple bag-of-words (term frequency) vectors.

    Returns:
        Similarity score between 0.0 and 1.0.
    """
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    # Build term frequency vectors
    tf_a = Counter(t for t in tokens_a if t not in STOP_WORDS and len(t) > 2)
    tf_b = Counter(t for t in tokens_b if t not in STOP_WORDS and len(t) > 2)

    # Find common terms
    common_terms = set(tf_a.keys()) & set(tf_b.keys())

    if not common_terms:
        return 0.0

    dot_product = sum(tf_a[term] * tf_b[term] for term in common_terms)
    magnitude_a = math.sqrt(sum(v ** 2 for v in tf_a.values()))
    magnitude_b = math.sqrt(sum(v ** 2 for v in tf_b.values()))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


# ── Internal Helpers ───────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words."""
    text = text.lower()
    # Keep alphanumeric, hyphens, dots (for tech terms like "node.js", "c++")
    text = re.sub(r"[^a-z0-9.\-+#]", " ", text)
    tokens = text.split()
    # Clean up tokens
    return [t.strip(".-") for t in tokens if len(t.strip(".-")) > 1]
