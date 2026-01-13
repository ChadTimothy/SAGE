"""Tests for SAGE GraphQueries."""

from datetime import date, datetime

import pytest

from sage.graph import (
    ApplicationEvent,
    ApplicationStatus,
    Concept,
    ConceptStatus,
    DemoType,
    Edge,
    EdgeType,
    GraphQueries,
    GraphStore,
    Learner,
    LearnerProfile,
    Outcome,
    OutcomeStatus,
    Proof,
    ProofExchange,
    Session,
)


@pytest.fixture
def store():
    """Create an in-memory store for testing."""
    return GraphStore(":memory:")


@pytest.fixture
def queries(store):
    """Create queries interface with store."""
    return GraphQueries(store)


@pytest.fixture
def populated_store(store):
    """Create a store with sample data."""
    # Create learner
    learner = Learner(profile=LearnerProfile(name="Test Learner"))
    store.create_learner(learner)

    # Create outcome
    outcome = Outcome(
        learner_id=learner.id,
        stated_goal="Learn pricing",
        status=OutcomeStatus.ACTIVE,
    )
    store.create_outcome(outcome)

    # Set active outcome
    learner.active_outcome_id = outcome.id
    store.update_learner(learner)

    # Create concepts
    concept1 = Concept(
        learner_id=learner.id,
        name="value-articulation",
        display_name="Value Articulation",
        discovered_from=outcome.id,
        status=ConceptStatus.UNDERSTOOD,
    )
    concept2 = Concept(
        learner_id=learner.id,
        name="pricing-psychology",
        display_name="Pricing Psychology",
        discovered_from=outcome.id,
        status=ConceptStatus.TEACHING,
    )
    concept3 = Concept(
        learner_id=learner.id,
        name="negotiation-tactics",
        display_name="Negotiation Tactics",
        discovered_from=outcome.id,
        status=ConceptStatus.IDENTIFIED,
    )
    store.create_concept(concept1)
    store.create_concept(concept2)
    store.create_concept(concept3)

    # Create session
    session = Session(learner_id=learner.id, outcome_id=outcome.id)
    store.create_session(session)

    # Create proof for concept1
    proof = Proof(
        learner_id=learner.id,
        concept_id=concept1.id,
        session_id=session.id,
        demonstration_type=DemoType.APPLICATION,
        evidence="Successfully explained value proposition",
        confidence=0.9,
        exchange=ProofExchange(
            prompt="Explain why your service is valuable",
            response="Great explanation...",
            analysis="Showed clear understanding",
        ),
    )
    store.create_proof(proof)

    # Create relates_to edge between concepts
    edge = Edge(
        from_id=concept1.id,
        from_type="concept",
        to_id=concept2.id,
        to_type="concept",
        edge_type=EdgeType.RELATES_TO,
        metadata={"relationship": "supports", "strength": 0.8},
    )
    store.create_edge(edge)

    # Create application event
    app_event = ApplicationEvent(
        learner_id=learner.id,
        concept_ids=[concept1.id],
        session_id=session.id,
        context="pricing call tomorrow",
        planned_date=date(2024, 1, 15),
        status=ApplicationStatus.COMPLETED,
        outcome_result="mixed",
        what_worked="Stated value clearly",
        what_struggled="Handled objection poorly",
    )
    store.create_application_event(app_event)

    return {
        "store": store,
        "learner": learner,
        "outcome": outcome,
        "concepts": [concept1, concept2, concept3],
        "session": session,
        "proof": proof,
        "edge": edge,
        "app_event": app_event,
    }


class TestGetLearnerState:
    """Tests for get_learner_state query."""

    def test_returns_none_for_nonexistent(self, queries):
        result = queries.get_learner_state("nonexistent")
        assert result is None

    def test_returns_complete_state(self, queries, populated_store):
        learner = populated_store["learner"]

        state = queries.get_learner_state(learner.id)

        assert state is not None
        assert state.learner.id == learner.id
        assert state.active_outcome is not None
        assert state.active_outcome.stated_goal == "Learn pricing"
        assert state.last_session is not None
        assert len(state.proven_concepts) == 1
        assert state.proven_concepts[0].name == "value-articulation"
        assert state.total_proofs == 1

    def test_returns_state_without_outcome(self, queries, store):
        learner = Learner()
        store.create_learner(learner)

        state = queries.get_learner_state(learner.id)

        assert state is not None
        assert state.active_outcome is None
        assert state.last_session is None
        assert len(state.proven_concepts) == 0


class TestGetProvenConcepts:
    """Tests for get_proven_concepts query."""

    def test_returns_proven_concepts_with_proofs(self, queries, populated_store):
        learner = populated_store["learner"]

        proven = queries.get_proven_concepts(learner.id)

        assert len(proven) == 1
        concept, proof = proven[0]
        assert concept.name == "value-articulation"
        assert proof.confidence == 0.9

    def test_returns_empty_for_no_proofs(self, queries, store):
        learner = Learner()
        store.create_learner(learner)

        proven = queries.get_proven_concepts(learner.id)
        assert len(proven) == 0


class TestFindRelatedConcepts:
    """Tests for find_related_concepts query."""

    def test_finds_related_concepts(self, queries, populated_store):
        concepts = populated_store["concepts"]
        learner = populated_store["learner"]
        concept1 = concepts[0]  # value-articulation

        related = queries.find_related_concepts(concept1.id, learner.id)

        assert len(related) == 1
        assert related[0].concept.name == "pricing-psychology"
        assert related[0].relationship == "supports"
        assert related[0].strength == 0.8
        assert related[0].has_proof is False

    def test_marks_proven_concepts(self, queries, populated_store):
        concepts = populated_store["concepts"]
        learner = populated_store["learner"]
        concept2 = concepts[1]  # pricing-psychology

        # concept2 is related to concept1, which has a proof
        related = queries.find_related_concepts(concept2.id, learner.id)

        assert len(related) == 1
        assert related[0].concept.name == "value-articulation"
        assert related[0].has_proof is True

    def test_returns_empty_for_no_relations(self, queries, populated_store):
        concepts = populated_store["concepts"]
        learner = populated_store["learner"]
        concept3 = concepts[2]  # negotiation-tactics (no edges)

        related = queries.find_related_concepts(concept3.id, learner.id)
        assert len(related) == 0


class TestGetApplicationsForConcept:
    """Tests for get_applications_for_concept query."""

    def test_finds_applications(self, queries, populated_store):
        concepts = populated_store["concepts"]
        learner = populated_store["learner"]
        concept1 = concepts[0]

        apps = queries.get_applications_for_concept(concept1.id, learner.id)

        assert len(apps) == 1
        assert apps[0].outcome_result == "mixed"
        assert apps[0].what_worked == "Stated value clearly"

    def test_returns_empty_for_no_applications(self, queries, populated_store):
        concepts = populated_store["concepts"]
        learner = populated_store["learner"]
        concept2 = concepts[1]  # No applications for this concept

        apps = queries.get_applications_for_concept(concept2.id, learner.id)
        assert len(apps) == 0


class TestFindConnectionsToKnown:
    """Tests for find_connections_to_known query."""

    def test_finds_connections_to_proven_concepts(self, queries, populated_store):
        learner = populated_store["learner"]

        # pricing-psychology connects to value-articulation which is proven
        connections = queries.find_connections_to_known(
            "pricing-psychology", learner.id
        )

        assert len(connections) == 1
        assert connections[0].concept.name == "value-articulation"
        assert connections[0].has_proof is True

    def test_returns_empty_for_no_proven_connections(self, queries, populated_store):
        learner = populated_store["learner"]

        # negotiation-tactics has no edges at all
        connections = queries.find_connections_to_known(
            "negotiation-tactics", learner.id
        )
        assert len(connections) == 0


class TestGetOutcomeProgress:
    """Tests for get_outcome_progress query."""

    def test_returns_progress(self, queries, populated_store):
        outcome = populated_store["outcome"]

        progress = queries.get_outcome_progress(outcome.id)

        assert progress["outcome"] is not None
        assert progress["total_concepts"] == 3
        assert progress["concepts_understood"] == 1
        assert progress["concepts_teaching"] == 1
        assert progress["concepts_identified"] == 1

    def test_returns_empty_for_nonexistent(self, queries):
        progress = queries.get_outcome_progress("nonexistent")
        assert progress == {}


class TestGetLearningHistory:
    """Tests for get_learning_history query."""

    def test_returns_history(self, queries, populated_store):
        learner = populated_store["learner"]

        history = queries.get_learning_history(learner.id)

        assert len(history) == 1
        assert history[0]["session"] is not None

    def test_limits_results(self, queries, store):
        learner = Learner()
        store.create_learner(learner)

        # Create multiple sessions
        for i in range(5):
            session = Session(learner_id=learner.id)
            store.create_session(session)

        history = queries.get_learning_history(learner.id, limit=3)
        assert len(history) == 3
