"""Tests for SAGE embeddings module.

Tests semantic search capabilities including embedding storage,
cosine similarity, and integration with the learning graph.
"""

import pytest
from unittest.mock import MagicMock, patch

from sage.embeddings.store import EmbeddingStore, _cosine_similarity
from sage.embeddings.search import SemanticSearch
from sage.graph.models import Concept, Outcome
from sage.graph.store import GraphStore


class TestCosineSimilarity:
    """Test cosine similarity calculation."""

    def test_identical_vectors_return_one(self) -> None:
        """Identical vectors should have similarity of 1.0."""
        vec = [1.0, 2.0, 3.0]
        assert abs(_cosine_similarity(vec, vec) - 1.0) < 0.0001

    def test_orthogonal_vectors_return_zero(self) -> None:
        """Orthogonal vectors should have similarity of 0.0."""
        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        assert abs(_cosine_similarity(vec1, vec2)) < 0.0001

    def test_opposite_vectors_return_negative_one(self) -> None:
        """Opposite vectors should have similarity of -1.0."""
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        assert abs(_cosine_similarity(vec1, vec2) + 1.0) < 0.0001

    def test_zero_vector_returns_zero(self) -> None:
        """Zero vector should return 0 similarity."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]
        assert _cosine_similarity(vec1, vec2) == 0.0

    def test_different_lengths_return_zero(self) -> None:
        """Vectors of different lengths should return 0."""
        vec1 = [1.0, 2.0]
        vec2 = [1.0, 2.0, 3.0]
        assert _cosine_similarity(vec1, vec2) == 0.0


class TestEmbeddingStore:
    """Test embedding storage and retrieval."""

    @pytest.fixture
    def store(self) -> EmbeddingStore:
        """Create an in-memory embedding store."""
        return EmbeddingStore(":memory:")

    def test_store_and_retrieve(self, store: EmbeddingStore) -> None:
        """Should store and retrieve embeddings."""
        embedding = [0.1, 0.2, 0.3]
        store.store(
            entity_type="concept",
            entity_id="c1",
            learner_id="l1",
            text="Test concept",
            embedding=embedding,
        )

        record = store.get("concept", "c1")
        assert record is not None
        assert record.entity_type == "concept"
        assert record.entity_id == "c1"
        assert record.learner_id == "l1"
        assert record.text == "Test concept"
        assert record.embedding == embedding

    def test_update_existing(self, store: EmbeddingStore) -> None:
        """Should update existing embedding on conflict."""
        store.store("concept", "c1", "l1", "Original", [0.1, 0.2])
        store.store("concept", "c1", "l1", "Updated", [0.3, 0.4])

        record = store.get("concept", "c1")
        assert record.text == "Updated"
        assert record.embedding == [0.3, 0.4]

    def test_delete(self, store: EmbeddingStore) -> None:
        """Should delete embeddings."""
        store.store("concept", "c1", "l1", "Test", [0.1])
        assert store.delete("concept", "c1") is True
        assert store.get("concept", "c1") is None

    def test_search_similar(self, store: EmbeddingStore) -> None:
        """Should find similar embeddings."""
        store.store("concept", "c1", "l1", "Pricing", [1.0, 0.0, 0.0])
        store.store("concept", "c2", "l1", "Value", [0.9, 0.1, 0.0])
        store.store("concept", "c3", "l1", "Marketing", [0.0, 1.0, 0.0])

        results = store.search_similar(
            query_embedding=[1.0, 0.0, 0.0],
            learner_id="l1",
            limit=2,
            threshold=0.5,
        )

        assert len(results) == 2
        assert results[0][0].entity_id == "c1"
        assert results[0][1] > 0.99  # Nearly identical
        assert results[1][0].entity_id == "c2"

    def test_search_filters_by_learner(self, store: EmbeddingStore) -> None:
        """Search should only return embeddings for specified learner."""
        store.store("concept", "c1", "l1", "Test", [1.0, 0.0])
        store.store("concept", "c2", "l2", "Test", [1.0, 0.0])

        results = store.search_similar([1.0, 0.0], "l1", threshold=0.0)
        assert len(results) == 1
        assert results[0][0].learner_id == "l1"

    def test_search_filters_by_type(self, store: EmbeddingStore) -> None:
        """Search can filter by entity type."""
        store.store("concept", "c1", "l1", "Test", [1.0, 0.0])
        store.store("outcome", "o1", "l1", "Goal", [1.0, 0.0])

        results = store.search_similar(
            [1.0, 0.0], "l1", entity_type="concept", threshold=0.0
        )
        assert len(results) == 1
        assert results[0][0].entity_type == "concept"


class TestSemanticSearch:
    """Test semantic search integration."""

    @pytest.fixture
    def mock_embedding_service(self) -> MagicMock:
        """Create mock embedding service."""
        service = MagicMock()
        service.embed.return_value = [1.0, 0.0, 0.0]
        service.embed_concept.return_value = [1.0, 0.0, 0.0]
        service.embed_outcome.return_value = [0.0, 1.0, 0.0]
        return service

    @pytest.fixture
    def graph_store(self) -> GraphStore:
        """Create an in-memory graph store."""
        return GraphStore(":memory:")

    @pytest.fixture
    def embedding_store(self) -> EmbeddingStore:
        """Create an in-memory embedding store."""
        return EmbeddingStore(":memory:")

    @pytest.fixture
    def search(
        self,
        graph_store: GraphStore,
        embedding_store: EmbeddingStore,
        mock_embedding_service: MagicMock,
    ) -> SemanticSearch:
        """Create semantic search instance."""
        return SemanticSearch(graph_store, embedding_store, mock_embedding_service)

    def test_index_concept(
        self,
        search: SemanticSearch,
        embedding_store: EmbeddingStore,
    ) -> None:
        """Should index concepts for search."""
        concept = Concept(
            id="c1",
            learner_id="l1",
            name="pricing",
            display_name="Pricing Strategy",
            description="How to price services",
        )
        search.index_concept(concept)

        record = embedding_store.get("concept", "c1")
        assert record is not None
        assert record.learner_id == "l1"
        assert "Pricing Strategy" in record.text

    def test_index_outcome(
        self,
        search: SemanticSearch,
        embedding_store: EmbeddingStore,
    ) -> None:
        """Should index outcomes for search."""
        outcome = Outcome(
            id="o1",
            learner_id="l1",
            stated_goal="Learn to price freelance work",
            clarified_goal="Set confident prices for design services",
        )
        search.index_outcome(outcome)

        record = embedding_store.get("outcome", "o1")
        assert record is not None
        assert "freelance" in record.text.lower()

    def test_search_concepts(
        self,
        search: SemanticSearch,
        graph_store: GraphStore,
        embedding_store: EmbeddingStore,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Should search concepts by semantic similarity."""
        # Create and index a concept
        concept = Concept(
            id="c1",
            learner_id="l1",
            name="value-articulation",
            display_name="Value Articulation",
            description="Communicating value to clients",
        )
        graph_store.create_concept(concept)
        embedding_store.store("concept", "c1", "l1", "Value Articulation", [1.0, 0.0, 0.0])

        results = search.search_concepts("value", "l1", threshold=0.5)

        assert len(results) == 1
        assert results[0].concept is not None
        assert results[0].concept.id == "c1"

    def test_find_related_to_concept(
        self,
        search: SemanticSearch,
        graph_store: GraphStore,
        embedding_store: EmbeddingStore,
    ) -> None:
        """Should find semantically related concepts."""
        # Create two related concepts
        concept1 = Concept(
            id="c1", learner_id="l1", name="pricing", display_name="Pricing"
        )
        concept2 = Concept(
            id="c2", learner_id="l1", name="value", display_name="Value Prop"
        )
        graph_store.create_concept(concept1)
        graph_store.create_concept(concept2)

        embedding_store.store("concept", "c1", "l1", "Pricing", [1.0, 0.0, 0.0])
        embedding_store.store("concept", "c2", "l1", "Value", [0.95, 0.05, 0.0])

        results = search.find_related_to_concept(concept1, "l1", threshold=0.5)

        assert len(results) == 1
        assert results[0].entity_id == "c2"


class TestEmbeddingServiceMock:
    """Test embedding service with mocked API calls."""

    def test_embed_concept_combines_name_and_description(self) -> None:
        """embed_concept should combine name and description."""
        with patch("sage.embeddings.service.OpenAI") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1, 0.2])]
            mock_client.embeddings.create.return_value = mock_response
            mock_client_class.return_value = mock_client

            from sage.embeddings.service import EmbeddingService
            service = EmbeddingService(client=mock_client)
            service.embed_concept("Pricing", "How to set prices")

            call_args = mock_client.embeddings.create.call_args
            input_text = call_args.kwargs["input"][0]
            assert "Pricing" in input_text
            assert "How to set prices" in input_text

    def test_embed_batch_handles_empty_strings(self) -> None:
        """embed_batch should handle empty strings gracefully."""
        with patch("sage.embeddings.service.OpenAI") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
            mock_client.embeddings.create.return_value = mock_response
            mock_client_class.return_value = mock_client

            from sage.embeddings.service import EmbeddingService
            service = EmbeddingService(client=mock_client)
            results = service.embed_batch(["hello", "", "world"])

            # Should only call API for non-empty strings
            call_args = mock_client.embeddings.create.call_args
            assert len(call_args.kwargs["input"]) == 2
            assert len(results) == 3
            assert results[1] == [0.0] * 1536  # Empty string gets zero vector
