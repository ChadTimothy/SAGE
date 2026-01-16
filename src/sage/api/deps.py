"""API dependencies for dependency injection."""

from functools import lru_cache
from typing import Annotated, Generator

from fastapi import Depends

from sage.core.config import get_settings
from sage.graph.learning_graph import LearningGraph

from .auth import CurrentUser, get_current_user, get_current_user_optional
from .guards import OwnershipVerifier


@lru_cache
def get_settings_cached():
    """Get cached settings."""
    return get_settings()


def get_graph() -> Generator[LearningGraph, None, None]:
    """Get LearningGraph instance for request."""
    settings = get_settings_cached()
    yield LearningGraph(str(settings.db_path))


def get_verifier(
    graph: LearningGraph = Depends(get_graph),
) -> OwnershipVerifier:
    """Get ownership verifier with graph."""
    return OwnershipVerifier(graph)


# Type aliases for cleaner route signatures
Graph = Annotated[LearningGraph, Depends(get_graph)]
User = Annotated[CurrentUser, Depends(get_current_user)]
UserOptional = Annotated[CurrentUser | None, Depends(get_current_user_optional)]
Verifier = Annotated[OwnershipVerifier, Depends(get_verifier)]
