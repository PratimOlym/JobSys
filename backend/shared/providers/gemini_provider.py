"""Google Gemini provider implementation.

Uses the google-generativeai SDK.  Token counts are extracted from
``response.usage_metadata`` when available (Gemini 1.5+ and 2.x).
Remaining quota is not exposed by the Gemini API so ``remaining_tokens``
is always ``None``.
"""

import logging
from typing import Optional

from ..llm_provider import LLMProvider
from ..llm_types import LLMResponse, TokenUsage

logger = logging.getLogger(__name__)

# Default model — can be overridden via SSM / env
DEFAULT_MODEL = "gemini-2.0-flash"


class GeminiProvider(LLMProvider):
    """LLM provider backed by Google Gemini."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        # Lazy import so other providers can be used without google-generativeai installed
        try:
            import google.generativeai as genai  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "google-generativeai package is required for GeminiProvider. "
                "Install it with: pip install google-generativeai"
            ) from exc

        genai.configure(api_key=api_key)
        self._model_name = model
        self._client = genai.GenerativeModel(model)
        self._genai = genai  # kept for potential future use (e.g. listing models)


    # ── LLMProvider interface ──────────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, prompt: str) -> LLMResponse:
        """Call Gemini and return a standardised LLMResponse."""
        response = self._client.generate_content(prompt)

        usage = _extract_usage(response)
        text = response.text.strip()
        request_id: Optional[str] = None  # Gemini SDK doesn't surface a request ID

        logger.debug(
            "Gemini [%s] tokens — prompt=%d completion=%d total=%d",
            self._model_name,
            usage.prompt_tokens,
            usage.completion_tokens,
            usage.total_tokens,
        )

        return LLMResponse(
            text=text,
            usage=usage,
            provider=self.provider_name,
            model=self._model_name,
            request_id=request_id,
        )


# ── helpers ──────────────────────────────────────────────────────────────────


def _extract_usage(response) -> TokenUsage:
    """Pull token counts from ``response.usage_metadata`` if present."""
    try:
        meta = response.usage_metadata
        if meta is not None:
            prompt_tokens = getattr(meta, "prompt_token_count", 0) or 0
            completion_tokens = getattr(meta, "candidates_token_count", 0) or 0
            total = getattr(meta, "total_token_count", 0) or (
                prompt_tokens + completion_tokens
            )
            return TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total,
                remaining_tokens=None,  # Gemini API does not expose quota remaining
            )
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not extract Gemini usage metadata: %s", exc)

    # Fallback: estimate prompt tokens by character count (~4 chars/token)
    return TokenUsage(remaining_tokens=None)
