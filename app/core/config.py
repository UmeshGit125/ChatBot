"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./mock.db"

    # LLM Provider
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Application
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    QUERY_LOG_FILE: str = "query_logs.json"

    # Week definition
    WEEK_DEFINITION: str = "calendar"  # "calendar" (Mon-Sun) or "rolling7"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 10

    # Query timeout in seconds
    QUERY_TIMEOUT_SECONDS: int = 10

    # Backend URL (for Streamlit)
    BACKEND_URL: str = "http://localhost:8000"

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.DATABASE_URL

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
