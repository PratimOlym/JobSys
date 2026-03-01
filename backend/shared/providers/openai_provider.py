"""OpenAI provider implementation.

Uses the official ``openai`` Python SDK (v1+).  Token counts come from
``response.usage``.  For models with a known context window we also compute
``remaining_tokens`` so callers can see how much headroom is left.

Configurable via:
  - ``OPENAI_API_KEY``  env var or AWS Secrets Manager
  - ``OPENAI_MODEL``    env var or AWS SSM Parameter Store
    Default: ``gpt-4o-mini``  (fastest, cheapest, great at JSON tasks)
"""

import logging
from typing import Optional

from ..llm_provider import LLMProvider
from ..llm_types import LLMResponse, TokenUsage

logger = logging.getLogger(__name__)

# Default model — optimal balance of cost and quality for resume tasks
DEFAULT_MODEL = "gpt-4o-mini"

# Known context windows (input tokens) for cost estimation
_CONTEXT_WINDOWS: dict = {
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-3.5-turbo": 16_385,
    "gpt-3.5-turbo-16k": 16_385,
}


class OpenAIProvider(LLMProvider):
    """LLM provider backed by OpenAI."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        # Import here so Lambda packages without openai still run other providers
        try:
            from openai import OpenAI  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "openai package is required for OpenAIProvider. "
                "Install it with: pip install openai"
            ) from exc

        self._client = OpenAI(api_key=api_key)
        self._model_name = model

    # ── LLMProvider interface ──────────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, prompt: str) -> LLMResponse:
        """Call OpenAI chat completions and return a standardised LLMResponse."""
        response = self._client.chat.completions.create(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  # Low temp for deterministic JSON outputs
        )

        choice = response.choices[0]
        text = (choice.message.content or "").strip()
        request_id: Optional[str] = getattr(response, "id", None)

        usage = _extract_usage(response, self._model_name)

        logger.debug(
            "OpenAI [%s] tokens — prompt=%d completion=%d total=%d remaining=%s",
            self._model_name,
            usage.prompt_tokens,
            usage.completion_tokens,
            usage.total_tokens,
            usage.remaining_tokens,
        )

        return LLMResponse(
            text=text,
            usage=usage,
            provider=self.provider_name,
            model=self._model_name,
            request_id=request_id,
        )


# ── helpers ──────────────────────────────────────────────────────────────────


def _extract_usage(response, model: str) -> TokenUsage:
    """Pull token counts from the OpenAI response and compute remaining."""
    try:
        u = response.usage
        prompt_tokens = u.prompt_tokens or 0
        completion_tokens = u.completion_tokens or 0
        total_tokens = u.total_tokens or (prompt_tokens + completion_tokens)

        # Compute remaining based on context window
        context_window = _CONTEXT_WINDOWS.get(model)
        remaining: Optional[int] = None
        if context_window is not None:
            remaining = max(0, context_window - total_tokens)

        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            remaining_tokens=remaining,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not extract OpenAI usage: %s", exc)
        return TokenUsage(remaining_tokens=None)
