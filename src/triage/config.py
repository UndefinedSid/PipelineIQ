"""Application Configuration Module."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App Settings
    APP_NAME: str = "AI CI/CD Failure Triage Assistant"
    DEBUG: bool = False
    PORT: int = 8080

    # LLM Settings
    LLM_PROVIDER: str = "mock"  # "openai", "gemini", "ollama", "mock"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    LLM_TIMEOUT_SECONDS: float = 8.0

    # GitHub Settings
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_WEBHOOK_SECRET: Optional[str] = None

    # Slack Settings
    SLACK_WEBHOOK_URL: Optional[str] = None

    # Triage Configuration
    MAX_LOG_WINDOW_LINES: int = 200
    CONTEXT_BEFORE_ERROR: int = 50
    CONFIDENCE_THRESHOLD: float = 0.85


settings = Settings()
