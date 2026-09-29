from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Core application settings for CLARIO."""

    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    DATA_DIR: Path = BASE_DIR / "backend" / "data"
    USER_DB_PATH: Path = BASE_DIR / "backend" / "data" / "user.db"
    NOVA_DB_PATH: Path = BASE_DIR / "backend" / "data" / "nova.db"
    CLARIO_AI_DB_PATH: Path = BASE_DIR / "backend" / "data" / "clario_ai.db"

    GEMINI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    MISTRAL_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    MISTRAL_MODEL: str = "mistral-large-latest"

    # LangSmith tracing is opt-in; LangChain integrations read these standard names.
    LANGSMITH_API_KEY: str | None = None
    LANGSMITH_TRACING: bool = False
    LANGSMITH_PROJECT: str = "clario"
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"

    # Auth session storage
    SESSION_DIR: Path = BASE_DIR / "backend" / "data"
    SESSION_DB_PATH: Path = BASE_DIR / "backend" / "data" / "sessions.db"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
