"""Abstract base class for LLM providers.

All concrete providers (Gemini, OpenAI, HuggingFace) must implement this
interface so that the rest of the application can remain provider-agnostic.
"""

from abc import ABC, abstractmethod

from .llm_types import LLMResponse


class LLMProvider(ABC):
    """Common interface that every LLM provider must satisfy."""

    @abstractmethod
    def generate(self, prompt: str) -> LLMResponse:
        """Send *prompt* to the model and return a standardised response.

        Args:
            prompt: The complete prompt string to send.

        Returns:
            :class:`LLMResponse` containing the model output and token counts.

        Raises:
            Exception: Any provider-level error (rate limit, auth, network …).
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short lowercase identifier for this provider (e.g. ``"gemini"``)."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The exact model string used for API calls."""
