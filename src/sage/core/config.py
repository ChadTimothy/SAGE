"""Configuration for SAGE using environment variables."""

import logging
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Environment Variables:
        LLM_API_KEY: API key for the LLM provider (required)
        LLM_BASE_URL: Base URL for the LLM API (default: Grok)
        LLM_MODEL: Model name to use (default: grok-3-mini)
        SAGE_DB_PATH: Path to SQLite database (default: ./data/sage.db)
        SAGE_LOG_LEVEL: Logging level (default: INFO)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Configuration
    llm_api_key: str = Field(
        default="",
        validation_alias="LLM_API_KEY",
        description="API key for the LLM provider",
    )
    llm_base_url: str = Field(
        default="https://api.x.ai/v1",
        validation_alias="LLM_BASE_URL",
        description="Base URL for the LLM API (Grok, OpenAI, or compatible)",
    )
    llm_model: str = Field(
        default="grok-3-mini",
        validation_alias="LLM_MODEL",
        description="Model name to use",
    )

    # Database Configuration
    db_path: Path = Field(
        default=Path("./data/sage.db"),
        validation_alias="SAGE_DB_PATH",
        description="Path to SQLite database",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        validation_alias="SAGE_LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    # Authentication
    nextauth_secret: str = Field(
        default="",
        validation_alias="NEXTAUTH_SECRET",
        description="Secret for NextAuth.js JWT signing (required for auth)",
    )

    # OAuth 2.1 Configuration (for ChatGPT App)
    oauth_signing_key: str = Field(
        default="",
        validation_alias="OAUTH_SIGNING_KEY",
        description="Signing key for OAuth 2.1 JWTs (defaults to NEXTAUTH_SECRET)",
    )
    oauth_base_url: str = Field(
        default="http://localhost:8000",
        validation_alias="OAUTH_BASE_URL",
        description="Base URL for OAuth endpoints (used in metadata)",
    )

    @property
    def log_level_int(self) -> int:
        """Get log level as integer for logging module."""
        return getattr(logging, self.log_level.upper(), logging.INFO)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience access
settings = get_settings()


def get_llm_client():
    """Get configured OpenAI client for LLM access.

    Returns:
        OpenAI client configured for the current provider

    Raises:
        ValueError: If LLM_API_KEY is not set
    """
    from openai import OpenAI

    if not settings.llm_api_key:
        raise ValueError(
            "LLM_API_KEY environment variable is required. "
            "Set it to your API key for Grok, OpenAI, or compatible provider."
        )

    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )
