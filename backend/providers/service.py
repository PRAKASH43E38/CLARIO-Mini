from typing import Any, Type, TypeVar
from pydantic import BaseModel
from backend.core.config import settings
from backend.providers.base import LLMProvider

T = TypeVar("T", bound=BaseModel)


def _provider_credentials(provider_name: str) -> tuple[str, str]:
    key_name = {
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "mistral": "MISTRAL_API_KEY",
    }[provider_name]
    model_name = {
        "gemini": "GEMINI_MODEL",
        "groq": "GROQ_MODEL",
        "openrouter": "OPENROUTER_MODEL",
        "mistral": "MISTRAL_MODEL",
    }[provider_name]
    api_key = getattr(settings, key_name)
    if not api_key:
        raise RuntimeError(f"{key_name} is not configured in .env")
    return api_key, getattr(settings, model_name)


def _chat_model(provider_name: str):
    """Create a LangChain chat model for the selected configured provider."""
    try:
        from langchain.chat_models import init_chat_model
    except ImportError as exc:
        raise RuntimeError("Install backend/requirements.txt to use LangChain models") from exc

    api_key, model = _provider_credentials(provider_name)
    options: dict[str, Any] = {
        "model": model,
        "model_provider": {
            "gemini": "google_genai",
            "groq": "groq",
            "openrouter": "openai",
            "mistral": "mistralai",
        }[provider_name],
        "api_key": api_key,
        "temperature": 0.2,
    }
    if provider_name == "openrouter":
        options["base_url"] = "https://openrouter.ai/api/v1"
    return init_chat_model(**options)


async def _langchain_text(provider_name: str, prompt: str, system_prompt: str | None, **kwargs: Any) -> str:
    model = _chat_model(provider_name)
    messages = []
    if system_prompt:
        messages.append(("system", system_prompt))
    messages.append(("human", prompt))
    response = await model.ainvoke(messages, config=kwargs.get("config"))
    return str(response.content)


async def _langchain_structured(
    provider_name: str,
    prompt: str,
    output_schema: Type[T],
    system_prompt: str | None,
    **kwargs: Any,
) -> T:
    model = _chat_model(provider_name).with_structured_output(output_schema)
    messages = []
    if system_prompt:
        messages.append(("system", system_prompt))
    messages.append(("human", prompt))
    response = await model.ainvoke(messages, config=kwargs.get("config"))
    return response if isinstance(response, output_schema) else output_schema.model_validate(response)

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """Google Gemini model provider implementation."""

    @property
    def provider_name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        return bool(settings.GEMINI_API_KEY)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        return await _langchain_text("gemini", prompt, system_prompt, **kwargs)

    async def generate_structured(
        self,
        prompt: str,
        output_schema: Type[T],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> T:
        return await _langchain_structured("gemini", prompt, output_schema, system_prompt, **kwargs)


class GroqProvider(LLMProvider):
    """Groq model provider implementation."""

    @property
    def provider_name(self) -> str:
        return "groq"

    def is_available(self) -> bool:
        return bool(settings.GROQ_API_KEY)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        return await _langchain_text("groq", prompt, system_prompt, **kwargs)

    async def generate_structured(
        self,
        prompt: str,
        output_schema: Type[T],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> T:
        return await _langchain_structured("groq", prompt, output_schema, system_prompt, **kwargs)


class OpenRouterProvider(LLMProvider):
    """OpenRouter model provider implementation."""

    @property
    def provider_name(self) -> str:
        return "openrouter"

    def is_available(self) -> bool:
        return bool(settings.OPENROUTER_API_KEY)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        return await _langchain_text("openrouter", prompt, system_prompt, **kwargs)

    async def generate_structured(
        self,
        prompt: str,
        output_schema: Type[T],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> T:
        return await _langchain_structured("openrouter", prompt, output_schema, system_prompt, **kwargs)


class MistralProvider(LLMProvider):
    """Mistral model provider implementation."""

    @property
    def provider_name(self) -> str:
        return "mistral"

    def is_available(self) -> bool:
        return bool(settings.MISTRAL_API_KEY)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        return await _langchain_text("mistral", prompt, system_prompt, **kwargs)

    async def generate_structured(
        self,
        prompt: str,
        output_schema: Type[T],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> T:
        return await _langchain_structured("mistral", prompt, output_schema, system_prompt, **kwargs)


class ProviderService:
    """
    Central provider manager and service abstraction.
    Agents interact exclusively through this service.

    Future fallback order:
    1. Gemini
    2. Groq
    3. OpenRouter
    4. Mistral
    """

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {
            "gemini": GeminiProvider(),
            "groq": GroqProvider(),
            "openrouter": OpenRouterProvider(),
            "mistral": MistralProvider(),
        }
        self.fallback_order = ["gemini", "groq", "openrouter", "mistral"]

    def get_provider(self, name: str | None = None) -> LLMProvider:
        """Retrieve a specific provider or the default primary provider."""
        target = name.lower() if name else self.fallback_order[0]
        if target not in self._providers:
            raise ValueError(f"Unknown LLM provider: {name}. Supported: {list(self._providers.keys())}")
        return self._providers[target]

    def list_available_providers(self) -> list[str]:
        """List all providers that have active credentials configured."""
        return [name for name, p in self._providers.items() if p.is_available()]

    async def generate_content(
        self,
        prompt: str,
        response_format: Type[T] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> T | str:
        """
        Universal generation interface.
        If response_format is provided, uses structured generation.
        Otherwise, uses text generation.
        """
        provider = next((self._providers[name] for name in self.fallback_order if self._providers[name].is_available()), None)
        if provider is None:
            raise RuntimeError("No LLM provider API key is configured. Add GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, or MISTRAL_API_KEY to .env")

        if response_format:
            return await provider.generate_structured(
                prompt=prompt,
                output_schema=response_format,
                system_prompt=system_prompt,
                **kwargs
            )

        return await provider.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            **kwargs
        )

provider_service = ProviderService()
