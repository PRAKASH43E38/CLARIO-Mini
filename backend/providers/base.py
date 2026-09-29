from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Abstract base class for all LLM providers in CLARIO."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g., 'gemini', 'groq', 'openrouter', 'mistral')."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider credentials and configuration are available."""
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate a raw text response for the given prompt."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        output_schema: Type[T],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Generate a validated structured response matching the Pydantic schema."""
        pass
