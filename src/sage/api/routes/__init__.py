"""API routes."""

from .chat import router as chat_router
from .graph import router as graph_router
from .learners import router as learners_router
from .practice import router as practice_router
from .sessions import router as sessions_router
from .voice import router as voice_router

__all__ = [
    "chat_router",
    "graph_router",
    "learners_router",
    "practice_router",
    "sessions_router",
    "voice_router",
]
