"""Semantic search functionality for SAGE.

Provides high-level search capabilities combining embeddings
with the learning graph for smarter context retrieval.
"""

from dataclasses import dataclass
from typing import Optional

from sage.graph.models import Concept, Outcome
from sage.graph.store import GraphStore

from .service import EmbeddingService
from .store import EmbeddingStore


@dataclass
class SemanticMatch:
    """A semantic search result."""

    entity_type: str
    entity_id: str
    text: str
    similarity: float
    concept: Optional[Concept] = None
    outcome: Optional[Outcome] = None


class SemanticSearch:
    """Semantic search over the learning graph.

    Combines embedding-based similarity search with graph queries
    for rich, context-aware retrieval.
    """

    def __init__(
        self,
        graph_store: GraphStore,
        embedding_store: EmbeddingStore,
        embedding_service: EmbeddingService,
    ):
        """Initialize semantic search.

        Args:
            graph_store: The learning graph store
            embedding_store: Store for embeddings
            embedding_service: Service for generating embeddings
        """
        self.graph_store = graph_store
        self.embedding_store = embedding_store
        self.embedding_service = embedding_service

    def index_concept(self, concept: Concept) -> None:
        """Index a concept for semantic search.

        Args:
            concept: The concept to index
        """
        embedding = self.embedding_service.embed_concept(
            concept.display_name or concept.name,
            concept.description,
        )
        self.embedding_store.store(
            entity_type="concept",
            entity_id=concept.id,
            learner_id=concept.learner_id,
            text=f"{concept.display_name}: {concept.description or ''}".strip(": "),
            embedding=embedding,
        )

    def index_outcome(self, outcome: Outcome) -> None:
        """Index an outcome for semantic search.

        Args:
            outcome: The outcome to index
        """
        embedding = self.embedding_service.embed_outcome(
            outcome.stated_goal,
            outcome.clarified_goal,
            outcome.motivation,
        )
        text_parts = [outcome.stated_goal]
        if outcome.clarified_goal:
            text_parts.append(outcome.clarified_goal)
        self.embedding_store.store(
            entity_type="outcome",
            entity_id=outcome.id,
            learner_id=outcome.learner_id,
            text=" | ".join(text_parts),
            embedding=embedding,
        )

    def search_concepts(
        self,
        query: str,
        learner_id: str,
        limit: int = 5,
        threshold: float = 0.5,
    ) -> list[SemanticMatch]:
        """Search for concepts semantically similar to the query.

        Args:
            query: Natural language search query
            learner_id: Learner whose concepts to search
            limit: Maximum results
            threshold: Minimum similarity (0-1)

        Returns:
            List of matching concepts with similarity scores
        """
        query_embedding = self.embedding_service.embed(query)
        results = self.embedding_store.search_similar(
            query_embedding,
            learner_id,
            entity_type="concept",
            limit=limit,
            threshold=threshold,
        )

        matches = []
        for record, similarity in results:
            concept = self.graph_store.get_concept(record.entity_id)
            if concept:
                matches.append(
                    SemanticMatch(
                        entity_type="concept",
                        entity_id=record.entity_id,
                        text=record.text,
                        similarity=similarity,
                        concept=concept,
                    )
                )
        return matches

    def search_outcomes(
        self,
        query: str,
        learner_id: str,
        limit: int = 5,
        threshold: float = 0.5,
    ) -> list[SemanticMatch]:
        """Search for outcomes semantically similar to the query.

        Args:
            query: Natural language search query
            learner_id: Learner whose outcomes to search
            limit: Maximum results
            threshold: Minimum similarity (0-1)

        Returns:
            List of matching outcomes with similarity scores
        """
        query_embedding = self.embedding_service.embed(query)
        results = self.embedding_store.search_similar(
            query_embedding,
            learner_id,
            entity_type="outcome",
            limit=limit,
            threshold=threshold,
        )

        matches = []
        for record, similarity in results:
            outcome = self.graph_store.get_outcome(record.entity_id)
            if outcome:
                matches.append(
                    SemanticMatch(
                        entity_type="outcome",
                        entity_id=record.entity_id,
                        text=record.text,
                        similarity=similarity,
                        outcome=outcome,
                    )
                )
        return matches

    def search_all(
        self,
        query: str,
        learner_id: str,
        limit: int = 10,
        threshold: float = 0.5,
    ) -> list[SemanticMatch]:
        """Search across all entity types.

        Args:
            query: Natural language search query
            learner_id: Learner to search
            limit: Maximum results
            threshold: Minimum similarity (0-1)

        Returns:
            List of all matching entities, sorted by similarity
        """
        query_embedding = self.embedding_service.embed(query)
        results = self.embedding_store.search_similar(
            query_embedding,
            learner_id,
            entity_type=None,  # Search all types
            limit=limit,
            threshold=threshold,
        )

        matches = []
        for record, similarity in results:
            match = SemanticMatch(
                entity_type=record.entity_type,
                entity_id=record.entity_id,
                text=record.text,
                similarity=similarity,
            )

            if record.entity_type == "concept":
                match.concept = self.graph_store.get_concept(record.entity_id)
            elif record.entity_type == "outcome":
                match.outcome = self.graph_store.get_outcome(record.entity_id)

            matches.append(match)

        return matches

    def find_related_to_concept(
        self,
        concept: Concept,
        learner_id: str,
        limit: int = 5,
        threshold: float = 0.6,
    ) -> list[SemanticMatch]:
        """Find concepts semantically related to a given concept.

        This goes beyond explicit graph edges to find concepts
        that are similar in meaning.

        Args:
            concept: The concept to find relations for
            learner_id: Learner to search
            limit: Maximum results
            threshold: Minimum similarity (0-1)

        Returns:
            List of semantically related concepts
        """
        text = f"{concept.display_name}: {concept.description or ''}".strip(": ")
        matches = self.search_concepts(text, learner_id, limit + 1, threshold)
        return [m for m in matches if m.entity_id != concept.id][:limit]

    def reindex_learner(self, learner_id: str) -> dict:
        """Reindex all embeddings for a learner.

        Useful when embedding model changes or for initialization.

        Args:
            learner_id: The learner to reindex

        Returns:
            Dict with counts of indexed entities
        """
        concepts = self.graph_store.get_concepts_by_learner(learner_id)
        for concept in concepts:
            self.index_concept(concept)

        outcomes = self.graph_store.get_outcomes_by_learner(learner_id)
        for outcome in outcomes:
            self.index_outcome(outcome)

        return {
            "concepts": len(concepts),
            "outcomes": len(outcomes),
        }
