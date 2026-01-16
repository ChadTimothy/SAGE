"""Embedding generation service using OpenAI-compatible API.

Uses the same LLM configuration as the rest of SAGE, so works with
OpenAI, Grok, or any OpenAI-compatible provider.
"""

from typing import Optional
from openai import OpenAI

from sage.core.config import settings


class EmbeddingService:
    """Generate embeddings using OpenAI-compatible API."""

    def __init__(
        self,
        client: Optional[OpenAI] = None,
        model: str = "text-embedding-3-small",
    ):
        """Initialize the embedding service.

        Args:
            client: OpenAI client (uses default from settings if not provided)
            model: Embedding model to use (default: text-embedding-3-small)
        """
        self.client = client or OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
        self.model = model
        self._dimensions = 1536  # Default for text-embedding-3-small

    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        text = text.replace("\n", " ").strip()
        if not text:
            return [0.0] * self._dimensions

        response = self.client.embeddings.create(
            input=[text],
            model=self.model,
        )
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        cleaned = [t.replace("\n", " ").strip() for t in texts]
        non_empty = [(i, t) for i, t in enumerate(cleaned) if t]

        if not non_empty:
            return [[0.0] * self._dimensions for _ in texts]

        response = self.client.embeddings.create(
            input=[t for _, t in non_empty],
            model=self.model,
        )

        result = [[0.0] * self._dimensions for _ in texts]
        for (orig_idx, _), emb_data in zip(non_empty, response.data):
            result[orig_idx] = emb_data.embedding

        return result

    def embed_concept(self, name: str, description: Optional[str] = None) -> list[float]:
        """Generate embedding for a concept.

        Combines name and description for richer semantic representation.

        Args:
            name: Concept name
            description: Optional concept description

        Returns:
            Embedding vector
        """
        text = f"{name}: {description}" if description else name
        return self.embed(text)

    def embed_outcome(
        self,
        stated_goal: str,
        clarified_goal: Optional[str] = None,
        motivation: Optional[str] = None,
    ) -> list[float]:
        """Generate embedding for an outcome.

        Args:
            stated_goal: What the user said they want
            clarified_goal: Refined goal statement
            motivation: Why they want this

        Returns:
            Embedding vector
        """
        parts = [
            stated_goal,
            clarified_goal,
            f"Motivation: {motivation}" if motivation else None,
        ]
        return self.embed(" | ".join(p for p in parts if p))
