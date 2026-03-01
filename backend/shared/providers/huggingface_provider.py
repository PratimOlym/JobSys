"""HuggingFace Inference API provider implementation.

Uses ``huggingface_hub`` to call hosted inference endpoints.
The free Inference API does **not** return token usage in its response,
so we estimate ``prompt_tokens`` via a simple word-count heuristic and
leave ``remaining_tokens`` as ``None``.

Configurable via:
  - ``HF_API_KEY``   env var or AWS Secrets Manager
  - ``HF_MODEL``     env var or AWS SSM Parameter Store
    Default: ``mistralai/Mistral-7B-Instruct-v0.3``
    (strong instruction-following, open-weights, low cost on HF Inference API)
"""

import json
import logging
from typing import Optional

from ..llm_provider import LLMProvider
from ..llm_types import LLMResponse, TokenUsage

logger = logging.getLogger(__name__)

# Default model — best free-tier option for structured JSON / resume tasks
DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"

# Approximate tokens-per-word for estimation (conservative)
_TOKENS_PER_WORD = 1.35


class HuggingFaceProvider(LLMProvider):
    """LLM provider backed by the HuggingFace Inference API."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        try:
            from huggingface_hub import InferenceClient  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "huggingface_hub package is required for HuggingFaceProvider. "
                "Install it with: pip install huggingface_hub"
            ) from exc

        self._client = InferenceClient(model=model, token=api_key)
        self._model_name = model

    # ── LLMProvider interface ──────────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return "huggingface"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, prompt: str) -> LLMResponse:
        """Call the HF Inference API and return a standardised LLMResponse.

        Uses the chat-completion endpoint when available, otherwise falls back
        to text-generation.  The prompt is wrapped in a standard user message.
        """
        try:
            # Prefer chat-completion endpoint (Mistral / Llama instruction models)
            result = self._client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.2,
            )
            text = result.choices[0].message.content or ""
            usage = _estimate_usage_chat(result, prompt)
        except Exception as chat_exc:
            logger.debug(
                "chat_completion failed for %s (%s); falling back to text_generation",
                self._model_name,
                chat_exc,
            )
            # Fallback: text-generation endpoint
            result = self._client.text_generation(
                prompt,
                max_new_tokens=2048,
                temperature=0.2,
                return_full_text=False,
            )
            text = result if isinstance(result, str) else str(result)
            usage = _estimate_usage_text(prompt, text)

        text = text.strip()
        logger.debug(
            "HuggingFace [%s] estimated tokens — prompt=%d completion=%d total=%d",
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
            request_id=None,  # HF Inference API doesn't surface a request ID
        )


# ── helpers ──────────────────────────────────────────────────────────────────


def _word_count_to_tokens(text: str) -> int:
    """Rough token estimate based on word count."""
    return max(1, int(len(text.split()) * _TOKENS_PER_WORD))


def _estimate_usage_chat(result, prompt: str) -> TokenUsage:
    """Extract or estimate token usage from a chat-completion result."""
    try:
        u = result.usage
        if u is not None:
            prompt_tokens = getattr(u, "prompt_tokens", 0) or 0
            completion_tokens = getattr(u, "completion_tokens", 0) or 0
            total = getattr(u, "total_tokens", 0) or (prompt_tokens + completion_tokens)
            return TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total,
                remaining_tokens=None,
            )
    except Exception:  # noqa: BLE001
        pass

    # Fallback estimation
    prompt_tokens = _word_count_to_tokens(prompt)
    completion_text = ""
    try:
        completion_text = result.choices[0].message.content or ""
    except Exception:  # noqa: BLE001
        pass
    completion_tokens = _word_count_to_tokens(completion_text)
    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        remaining_tokens=None,
    )


def _estimate_usage_text(prompt: str, completion: str) -> TokenUsage:
    """Estimate token usage for text-generation fallback."""
    prompt_tokens = _word_count_to_tokens(prompt)
    completion_tokens = _word_count_to_tokens(completion)
    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        remaining_tokens=None,
    )
