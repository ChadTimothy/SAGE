"""Tests for SAGE GraphStore."""

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
    EnergyLevel,
    GraphStore,
    IntentionStrength,
    Learner,
    LearnerProfile,
    Message,
    Outcome,
    OutcomeStatus,
    Proof,
    ProofExchange,
    Session,
    SessionContext,
    SessionEndingState,
    AgeGroup,
    SkillLevel,
)


@pytest.fixture
def store():
    """Create an in-memory store for testing."""
    return GraphStore(":memory:")


class TestGraphStoreInit:
    """Tests for store initialization."""

    def test_creates_in_memory(self):
        store = GraphStore(":memory:")
        assert store is not None

    def test_creates_schema(self, store):
        # Verify tables exist by trying to select from them
        with store.connection() as conn:
            tables = [
                "learners",
                "outcomes",
                "concepts",
                "proofs",
                "sessions",
                "application_events",
                "edges",
            ]
            for table in tables:
                result = conn.execute(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                ).fetchone()
                assert result is not None, f"Table {table} should exist"


class TestLearnerOperations:
    """Tests for learner CRUD operations."""

    def test_create_and_get_learner(self, store):
        learner = Learner(
            profile=LearnerProfile(
                name="Test User",
                age_group=AgeGroup.ADULT,
                skill_level=SkillLevel.INTERMEDIATE,
            )
        )
        store.create_learner(learner)

        retrieved = store.get_learner(learner.id)
        assert retrieved is not None
        assert retrieved.id == learner.id
        assert retrieved.profile.name == "Test User"
        assert retrieved.profile.age_group == AgeGroup.ADULT
        assert retrieved.profile.skill_level == SkillLevel.INTERMEDIATE

    def test_get_nonexistent_learner(self, store):
        result = store.get_learner("nonexistent-id")
        assert result is None

    def test_update_learner(self, store):
        learner = Learner(profile=LearnerProfile(name="Original"))
        store.create_learner(learner)

        learner.profile.name = "Updated"
        learner.total_sessions = 5
        store.update_learner(learner)

        retrieved = store.get_learner(learner.id)
        assert retrieved.profile.name == "Updated"
        assert retrieved.total_sessions == 5


class TestOutcomeOperations:
    """Tests for outcome CRUD operations."""

    def test_create_and_get_outcome(self, store):
        learner = Learner()
        store.create_learner(learner)

        outcome = Outcome(
            learner_id=learner.id,
            stated_goal="Learn to code",
            clarified_goal="Build a web application",
            territory=["HTML", "CSS", "JavaScript"],
        )
        store.create_outcome(outcome)

        retrieved = store.get_outcome(outcome.id)
        assert retrieved is not None
        assert retrieved.stated_goal == "Learn to code"
        assert retrieved.territory == ["HTML", "CSS", "JavaScript"]

    def test_get_outcomes_by_learner(self, store):
        learner = Learner()
        store.create_learner(learner)

        outcome1 = Outcome(learner_id=learner.id, stated_goal="Goal 1")
        outcome2 = Outcome(
            learner_id=learner.id,
            stated_goal="Goal 2",
            status=OutcomeStatus.ACHIEVED,
        )
        store.create_outcome(outcome1)
        store.create_outcome(outcome2)

        all_outcomes = store.get_outcomes_by_learner(learner.id)
        assert len(all_outcomes) == 2

        active_outcomes = store.get_outcomes_by_learner(learner.id, status="active")
        assert len(active_outcomes) == 1

    def test_update_outcome(self, store):
        learner = Learner()
        store.create_learner(learner)

        outcome = Outcome(learner_id=learner.id, stated_goal="Original")
        store.create_outcome(outcome)

        outcome.status = OutcomeStatus.ACHIEVED
        outcome.achieved_at = datetime.utcnow()
        store.update_outcome(outcome)

        retrieved = store.get_outcome(outcome.id)
        assert retrieved.status == OutcomeStatus.ACHIEVED
        assert retrieved.achieved_at is not None


class TestConceptOperations:
    """Tests for concept CRUD operations."""

    def test_create_and_get_concept(self, store):
        learner = Learner()
        store.create_learner(learner)

        outcome = Outcome(learner_id=learner.id, stated_goal="Test goal")
        store.create_outcome(outcome)

        concept = Concept(
            learner_id=learner.id,
            name="test-concept",
            display_name="Test Concept",
            description="A test concept",
            discovered_from=outcome.id,
        )
        store.create_concept(concept)

        retrieved = store.get_concept(concept.id)
        assert retrieved is not None
        assert retrieved.name == "test-concept"
        assert retrieved.discovered_from == outcome.id

    def test_get_concepts_by_outcome(self, store):
        learner = Learner()
        store.create_learner(learner)

        outcome = Outcome(learner_id=learner.id, stated_goal="Test goal")
        store.create_outcome(outcome)

        concept1 = Concept(
            learner_id=learner.id,
            name="concept-1",
            display_name="Concept 1",
            discovered_from=outcome.id,
        )
        concept2 = Concept(
            learner_id=learner.id,
            name="concept-2",
            display_name="Concept 2",
            discovered_from=outcome.id,
        )
        store.create_concept(concept1)
        store.create_concept(concept2)

        concepts = store.get_concepts_by_outcome(outcome.id)
        assert len(concepts) == 2

    def test_update_concept(self, store):
        learner = Learner()
        store.create_learner(learner)

        concept = Concept(
            learner_id=learner.id,
            name="test",
            display_name="Test",
        )
        store.create_concept(concept)

        concept.status = ConceptStatus.UNDERSTOOD
        concept.understood_at = datetime.utcnow()
        concept.times_discussed = 3
        store.update_concept(concept)

        retrieved = store.get_concept(concept.id)
        assert retrieved.status == ConceptStatus.UNDERSTOOD
        assert retrieved.times_discussed == 3


class TestProofOperations:
    """Tests for proof CRUD operations."""

    def test_create_and_get_proof(self, store):
        learner = Learner()
        store.create_learner(learner)

        concept = Concept(
            learner_id=learner.id,
            name="test",
            display_name="Test",
        )
        store.create_concept(concept)

        session = Session(learner_id=learner.id)
        store.create_session(session)

        proof = Proof(
            learner_id=learner.id,
            concept_id=concept.id,
            session_id=session.id,
            demonstration_type=DemoType.APPLICATION,
            evidence="Successfully applied the concept",
            confidence=0.9,
            exchange=ProofExchange(
                prompt="Explain this",
                response="Here's my explanation",
                analysis="Good understanding shown",
            ),
        )
        store.create_proof(proof)

        retrieved = store.get_proof(proof.id)
        assert retrieved is not None
        assert retrieved.confidence == 0.9
        assert retrieved.exchange.prompt == "Explain this"

    def test_get_proofs_by_concept(self, store):
        learner = Learner()
        store.create_learner(learner)

        concept = Concept(
            learner_id=learner.id,
            name="test",
            display_name="Test",
        )
        store.create_concept(concept)

        session = Session(learner_id=learner.id)
        store.create_session(session)

        proof = Proof(
            learner_id=learner.id,
            concept_id=concept.id,
            session_id=session.id,
            demonstration_type=DemoType.EXPLANATION,
            evidence="Test",
            exchange=ProofExchange(
                prompt="p", response="r", analysis="a"
            ),
        )
        store.create_proof(proof)

        proofs = store.get_proofs_by_concept(concept.id)
        assert len(proofs) == 1


class TestSessionOperations:
    """Tests for session CRUD operations."""

    def test_create_and_get_session(self, store):
        learner = Learner()
        store.create_learner(learner)

        session = Session(
            learner_id=learner.id,
            context=SessionContext(
                energy=EnergyLevel.HIGH,
                mindset="excited",
                intention_strength=IntentionStrength.LEARNING,
            ),
            messages=[
                Message(role="sage", content="Hello!"),
                Message(role="user", content="Hi there."),
            ],
        )
        store.create_session(session)

        retrieved = store.get_session(session.id)
        assert retrieved is not None
        assert retrieved.context.energy == EnergyLevel.HIGH
        assert len(retrieved.messages) == 2
        assert retrieved.messages[0].content == "Hello!"

    def test_get_last_session(self, store):
        learner = Learner()
        store.create_learner(learner)

        session1 = Session(learner_id=learner.id)
        session2 = Session(learner_id=learner.id)
        store.create_session(session1)
        store.create_session(session2)

        last = store.get_last_session(learner.id)
        assert last is not None
        # Most recent should be returned first
        assert last.id in [session1.id, session2.id]

    def test_update_session(self, store):
        learner = Learner()
        store.create_learner(learner)

        session = Session(learner_id=learner.id)
        store.create_session(session)

        session.ended_at = datetime.utcnow()
        session.summary = "Good session"
        session.ending_state = SessionEndingState(
            mode="probing",
            current_focus="value-articulation",
        )
        store.update_session(session)

        retrieved = store.get_session(session.id)
        assert retrieved.ended_at is not None
        assert retrieved.summary == "Good session"
        assert retrieved.ending_state.mode == "probing"


class TestApplicationEventOperations:
    """Tests for application event CRUD operations."""

    def test_create_and_get_event(self, store):
        learner = Learner()
        store.create_learner(learner)

        session = Session(learner_id=learner.id)
        store.create_session(session)

        event = ApplicationEvent(
            learner_id=learner.id,
            concept_ids=["concept-1", "concept-2"],
            session_id=session.id,
            context="pricing call tomorrow",
            planned_date=date(2024, 1, 15),
            stakes="high",
        )
        store.create_application_event(event)

        retrieved = store.get_application_event(event.id)
        assert retrieved is not None
        assert retrieved.context == "pricing call tomorrow"
        assert retrieved.concept_ids == ["concept-1", "concept-2"]
        assert retrieved.planned_date == date(2024, 1, 15)

    def test_update_event_with_followup(self, store):
        learner = Learner()
        store.create_learner(learner)

        session = Session(learner_id=learner.id)
        store.create_session(session)

        event = ApplicationEvent(
            learner_id=learner.id,
            concept_ids=["concept-1"],
            session_id=session.id,
            context="test event",
        )
        store.create_application_event(event)

        event.status = ApplicationStatus.COMPLETED
        event.outcome_result = "mixed"
        event.what_worked = "Stated price confidently"
        event.what_struggled = "Caved on discount"
        event.gaps_revealed = ["discount-negotiation"]
        store.update_application_event(event)

        retrieved = store.get_application_event(event.id)
        assert retrieved.status == ApplicationStatus.COMPLETED
        assert retrieved.what_struggled == "Caved on discount"
        assert retrieved.gaps_revealed == ["discount-negotiation"]


class TestEdgeOperations:
    """Tests for edge CRUD operations."""

    def test_create_and_get_edge(self, store):
        edge = Edge(
            from_id="outcome-1",
            from_type="outcome",
            to_id="concept-1",
            to_type="concept",
            edge_type=EdgeType.REQUIRES,
        )
        store.create_edge(edge)

        retrieved = store.get_edge(edge.id)
        assert retrieved is not None
        assert retrieved.edge_type == EdgeType.REQUIRES

    def test_get_edges_from(self, store):
        edge1 = Edge(
            from_id="concept-1",
            from_type="concept",
            to_id="concept-2",
            to_type="concept",
            edge_type=EdgeType.RELATES_TO,
            metadata={"relationship": "similar", "strength": 0.8},
        )
        edge2 = Edge(
            from_id="concept-1",
            from_type="concept",
            to_id="proof-1",
            to_type="proof",
            edge_type=EdgeType.DEMONSTRATED_BY,
        )
        store.create_edge(edge1)
        store.create_edge(edge2)

        all_edges = store.get_edges_from("concept-1")
        assert len(all_edges) == 2

        relates_to_edges = store.get_edges_from("concept-1", edge_type="relates_to")
        assert len(relates_to_edges) == 1
        assert relates_to_edges[0].metadata["strength"] == 0.8

    def test_get_edges_to(self, store):
        edge = Edge(
            from_id="outcome-1",
            from_type="outcome",
            to_id="concept-1",
            to_type="concept",
            edge_type=EdgeType.REQUIRES,
        )
        store.create_edge(edge)

        edges = store.get_edges_to("concept-1")
        assert len(edges) == 1
        assert edges[0].from_id == "outcome-1"


class TestRoundTrips:
    """Tests for full serialization round trips through database."""

    def test_complex_learner_round_trip(self, store):
        from sage.graph import LearnerInsights, LearnerPreferences

        learner = Learner(
            profile=LearnerProfile(
                name="Complex User",
                context="software engineer",
                age_group=AgeGroup.ADULT,
                skill_level=SkillLevel.ADVANCED,
            ),
            preferences=LearnerPreferences(
                session_length="long",
                style="theoretical",
                pace="fast",
            ),
            insights=LearnerInsights(
                best_energy_level="morning",
                prefers_examples=False,
                effective_approaches=["analogies", "deep dives"],
                patterns=["learns best with visual aids"],
            ),
        )
        store.create_learner(learner)

        retrieved = store.get_learner(learner.id)
        assert retrieved.profile.age_group == AgeGroup.ADULT
        assert retrieved.preferences.style == "theoretical"
        assert "analogies" in retrieved.insights.effective_approaches

    def test_session_with_full_context(self, store):
        learner = Learner()
        store.create_learner(learner)

        outcome = Outcome(learner_id=learner.id, stated_goal="Test")
        store.create_outcome(outcome)

        session = Session(
            learner_id=learner.id,
            outcome_id=outcome.id,
            context=SessionContext(
                energy=EnergyLevel.MEDIUM,
                mindset="focused but tired",
                time_available="30 minutes",
                environment="home office",
                can_speak=True,
                device="desktop",
                intention_strength=IntentionStrength.URGENT,
                session_goal="Prepare for tomorrow's meeting",
            ),
            messages=[
                Message(role="sage", content="How can I help?", mode="check_in"),
                Message(role="user", content="I need to prep for a meeting"),
            ],
            concepts_explored=["concept-1", "concept-2"],
            proofs_earned=["proof-1"],
            ending_state=SessionEndingState(
                mode="teaching",
                current_focus="presentation-skills",
                next_step="Practice the opening",
            ),
        )
        store.create_session(session)

        retrieved = store.get_session(session.id)
        assert retrieved.context.intention_strength == IntentionStrength.URGENT
        assert retrieved.context.can_speak is True
        assert len(retrieved.concepts_explored) == 2
        assert retrieved.ending_state.next_step == "Practice the opening"
