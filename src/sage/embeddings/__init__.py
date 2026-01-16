"""Embedding service for semantic search in SAGE.

Provides vector embeddings for concepts, outcomes, and sessions
to enable semantic similarity search and GraphRAG capabilities.
"""

from .service import EmbeddingService
from .store import EmbeddingStore
from .search import SemanticSearch

__all__ = ["EmbeddingService", "EmbeddingStore", "SemanticSearch"]
