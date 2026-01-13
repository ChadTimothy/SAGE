"""Configuration for SAGE using environment variables."""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Environment Variables:
        LLM_API_KEY: API key for the LLM provider (required)
        LLM_BASE_URL: Base URL for the LLM API (default: Grok)
        LLM_MODEL: Model name to use (default: grok-3-mini)
        SAGE_DB_PATH: Path to SQLite database (default: ./data/sage.db)
        SAGE_LOG_LEVEL: Logging level (default: INFO)
    """

    # LLM Configuration
    llm_api_key: str = Field(
        default="",
        description="API key for the LLM provider",
    )
    llm_base_url: str = Field(
        default="https://api.x.ai/v1",
        description="Base URL for the LLM API (Grok, OpenAI, or compatible)",
    )
    llm_model: str = Field(
        default="grok-3-mini",
        description="Model name to use",
    )

    # Database Configuration
    db_path: Path = Field(
        default=Path("./data/sage.db"),
        description="Path to SQLite database",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    class Config:
        env_prefix = ""
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

        # Map environment variable names to field names
        fields = {
            "llm_api_key": {"env": "LLM_API_KEY"},
            "llm_base_url": {"env": "LLM_BASE_URL"},
            "llm_model": {"env": "LLM_MODEL"},
            "db_path": {"env": "SAGE_DB_PATH"},
            "log_level": {"env": "SAGE_LOG_LEVEL"},
        }

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
