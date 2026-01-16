"""API routes."""

from .auth import router as auth_router
from .chat import router as chat_router
from .graph import router as graph_router
from .learners import router as learners_router
from .practice import router as practice_router
from .scenarios import router as scenarios_router
from .sessions import router as sessions_router
from .voice import router as voice_router

__all__ = [
    "auth_router",
    "chat_router",
    "graph_router",
    "learners_router",
    "practice_router",
    "scenarios_router",
    "sessions_router",
    "voice_router",
]
