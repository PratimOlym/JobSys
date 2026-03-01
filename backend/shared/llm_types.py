"""Standard data types for all LLM providers in JobSys.

Every provider returns an LLMResponse wrapping the text plus token usage.
Callers never need to know which underlying SDK was used.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TokenUsage:
    """Token consumption for a single LLM request.

    Attributes:
        prompt_tokens: Tokens consumed by the input prompt.
        completion_tokens: Tokens generated in the model response.
        total_tokens: Sum of prompt + completion tokens.
        remaining_tokens: Estimated tokens remaining in the current quota
            window/context.  ``None`` when the provider does not expose this
            information (e.g. Gemini free-tier, HuggingFace Inference API).
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    remaining_tokens: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "remaining_tokens": self.remaining_tokens,
        }


@dataclass
class LLMResponse:
    """Standardised response from any LLM provider.

    Attributes:
        text: Raw text returned by the model (may be JSON, plain text, etc.).
        usage: Token consumption for this call.
        provider: Provider identifier — ``"gemini"``, ``"openai"``, or
            ``"huggingface"``.
        model: Specific model used (e.g. ``"gemini-2.0-flash"``).
        request_id: Provider-level request / trace ID when available.
    """

    text: str
    usage: TokenUsage
    provider: str
    model: str
    request_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "usage": self.usage.to_dict(),
            "provider": self.provider,
            "model": self.model,
            "request_id": self.request_id,
        }
