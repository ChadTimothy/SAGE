"""API dependencies for dependency injection."""

from functools import lru_cache
from typing import Generator

from sage.core.config import get_settings
from sage.graph.learning_graph import LearningGraph


@lru_cache
def get_settings_cached():
    """Get cached settings."""
    return get_settings()


def get_graph() -> Generator[LearningGraph, None, None]:
    """Get LearningGraph instance for request."""
    settings = get_settings_cached()
    yield LearningGraph(str(settings.db_path))
