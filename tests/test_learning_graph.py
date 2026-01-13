"""Tests for SAGE LearningGraph interface."""

from datetime import date

import pytest

from sage.graph import (
    DemoType,
    EnergyLevel,
    IntentionStrength,
    LearnerProfile,
    LearningGraph,
    Message,
    OutcomeStatus,
    ProofExchange,
    SessionContext,
    SessionEndingState,
    AgeGroup,
    SkillLevel,
)


@pytest.fixture
def graph():
    """Create an in-memory learning graph for testing."""
    return LearningGraph(":memory:")


class TestLearnerOperations:
    """Tests for learner operations."""

    def test_get_or_create_new_learner(self, graph):
        learner = graph.get_or_create_learner()
        assert learner is not None
        assert learner.id is not None

    def test_get_or_create_with_profile(self, graph):
        profile = LearnerProfile(
            name="Test User",
            age_group=AgeGroup.ADULT,
            skill_level=SkillLevel.INTERMEDIATE,
        )
        learner = graph.get_or_create_learner(profile=profile)
        assert learner.profile.name == "Test User"
        assert learner.profile.age_group == AgeGroup.ADULT

    def test_get_or_create_existing(self, graph):
        learner1 = graph.get_or_create_learner()
        learner2 = graph.get_or_create_learner(learner_id=learner1.id)
        assert learner1.id == learner2.id

    def test_update_learner(self, graph):
        learner = graph.get_or_create_learner()
        learner.profile.name = "Updated Name"
        graph.update_learner(learner)

        retrieved = graph.get_learner(learner.id)
        assert retrieved.profile.name == "Updated Name"

    def test_get_learner_state(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")
        session = graph.start_session(learner.id, outcome.id)

        state = graph.get_learner_state(learner.id)
        assert state is not None
        assert state.learner.id == learner.id
        assert state.active_outcome.id == outcome.id


class TestOutcomeOperations:
    """Tests for outcome operations."""

    def test_create_outcome(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(
            learner.id,
            stated_goal="Learn to price services",
            motivation="I'm undercharging",
        )
        assert outcome is not None
        assert outcome.stated_goal == "Learn to price services"
        assert outcome.motivation == "I'm undercharging"

    def test_create_outcome_sets_active(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")

        retrieved_learner = graph.get_learner(learner.id)
        assert retrieved_learner.active_outcome_id == outcome.id

    def test_get_active_outcome(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")

        active = graph.get_active_outcome(learner.id)
        assert active is not None
        assert active.id == outcome.id

    def test_mark_achieved(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")

        graph.mark_achieved(outcome.id)

        retrieved = graph.get_outcome(outcome.id)
        assert retrieved.status == OutcomeStatus.ACHIEVED
        assert retrieved.achieved_at is not None


class TestConceptOperations:
    """Tests for concept operations."""

    def test_create_concept(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")

        concept = graph.create_concept(
            learner.id,
            name="value-articulation",
            display_name="Value Articulation",
            discovered_from=outcome.id,
            description="How to explain your value",
        )

        assert concept is not None
        assert concept.name == "value-articulation"

    def test_get_concepts_for_outcome(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")

        graph.create_concept(
            learner.id, "concept-1", "Concept 1", outcome.id
        )
        graph.create_concept(
            learner.id, "concept-2", "Concept 2", outcome.id
        )

        concepts = graph.get_concepts_for_outcome(outcome.id)
        assert len(concepts) == 2


class TestProofOperations:
    """Tests for proof operations."""

    def test_create_proof(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")
        concept = graph.create_concept(
            learner.id, "test", "Test", outcome.id
        )
        session = graph.start_session(learner.id, outcome.id)

        proof = graph.create_proof(
            learner.id,
            concept.id,
            session.id,
            demonstration_type=DemoType.APPLICATION,
            evidence="Successfully demonstrated",
            exchange=ProofExchange(
                prompt="Explain this",
                response="Here's my answer",
                analysis="Good understanding",
            ),
            confidence=0.85,
        )

        assert proof is not None
        assert proof.confidence == 0.85

    def test_create_proof_marks_concept_understood(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")
        concept = graph.create_concept(
            learner.id, "test", "Test", outcome.id
        )
        session = graph.start_session(learner.id, outcome.id)

        graph.create_proof(
            learner.id,
            concept.id,
            session.id,
            demonstration_type=DemoType.EXPLANATION,
            evidence="Test",
            exchange=ProofExchange(prompt="p", response="r", analysis="a"),
        )

        retrieved = graph.get_concept(concept.id)
        assert retrieved.understood_at is not None

    def test_create_proof_increments_learner_total(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")
        concept = graph.create_concept(
            learner.id, "test", "Test", outcome.id
        )
        session = graph.start_session(learner.id, outcome.id)

        assert learner.total_proofs == 0

        graph.create_proof(
            learner.id,
            concept.id,
            session.id,
            demonstration_type=DemoType.EXPLANATION,
            evidence="Test",
            exchange=ProofExchange(prompt="p", response="r", analysis="a"),
        )

        retrieved = graph.get_learner(learner.id)
        assert retrieved.total_proofs == 1

    def test_has_proof(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")
        concept = graph.create_concept(
            learner.id, "test", "Test", outcome.id
        )
        session = graph.start_session(learner.id, outcome.id)

        assert graph.has_proof(concept.id) is False

        graph.create_proof(
            learner.id,
            concept.id,
            session.id,
            demonstration_type=DemoType.EXPLANATION,
            evidence="Test",
            exchange=ProofExchange(prompt="p", response="r", analysis="a"),
        )

        assert graph.has_proof(concept.id) is True


class TestSessionOperations:
    """Tests for session operations."""

    def test_start_session(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")

        session = graph.start_session(
            learner.id,
            outcome.id,
            context=SessionContext(
                energy=EnergyLevel.HIGH,
                intention_strength=IntentionStrength.LEARNING,
            ),
        )

        assert session is not None
        assert session.context.energy == EnergyLevel.HIGH

    def test_start_session_increments_count(self, graph):
        learner = graph.get_or_create_learner()
        assert learner.total_sessions == 0

        graph.start_session(learner.id)

        retrieved = graph.get_learner(learner.id)
        assert retrieved.total_sessions == 1

    def test_end_session(self, graph):
        learner = graph.get_or_create_learner()
        session = graph.start_session(learner.id)

        graph.end_session(
            session,
            summary="Good session",
            ending_state=SessionEndingState(
                mode="probing",
                current_focus="value-articulation",
            ),
        )

        retrieved = graph.get_session(session.id)
        assert retrieved.ended_at is not None
        assert retrieved.summary == "Good session"

    def test_add_message(self, graph):
        learner = graph.get_or_create_learner()
        session = graph.start_session(learner.id)

        graph.add_message(session, Message(role="sage", content="Hello!"))
        graph.add_message(session, Message(role="user", content="Hi!"))

        retrieved = graph.get_session(session.id)
        assert len(retrieved.messages) == 2


class TestEdgeOperations:
    """Tests for edge operations."""

    def test_add_concept_relation(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")
        concept1 = graph.create_concept(
            learner.id, "concept-1", "Concept 1", outcome.id
        )
        concept2 = graph.create_concept(
            learner.id, "concept-2", "Concept 2", outcome.id
        )
        session = graph.start_session(learner.id, outcome.id)

        edge = graph.add_concept_relation(
            concept1.id,
            concept2.id,
            relationship="supports",
            strength=0.8,
            session_id=session.id,
        )

        assert edge is not None
        assert edge.metadata["strength"] == 0.8

    def test_find_related_concepts(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")
        concept1 = graph.create_concept(
            learner.id, "concept-1", "Concept 1", outcome.id
        )
        concept2 = graph.create_concept(
            learner.id, "concept-2", "Concept 2", outcome.id
        )
        session = graph.start_session(learner.id, outcome.id)

        graph.add_concept_relation(
            concept1.id,
            concept2.id,
            relationship="supports",
            strength=0.8,
            session_id=session.id,
        )

        related = graph.find_related_concepts(concept1.id, learner.id)
        assert len(related) == 1
        assert related[0].concept.name == "concept-2"


class TestApplicationEventOperations:
    """Tests for application event operations."""

    def test_create_application_event(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")
        concept = graph.create_concept(
            learner.id, "test", "Test", outcome.id
        )
        session = graph.start_session(learner.id, outcome.id)

        event = graph.create_application_event(
            learner.id,
            session.id,
            concept_ids=[concept.id],
            context="pricing call tomorrow",
            planned_date=date(2024, 1, 15),
            stakes="high",
        )

        assert event is not None
        assert event.context == "pricing call tomorrow"
        assert event.stakes == "high"

    def test_record_followup(self, graph):
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Test goal")
        concept = graph.create_concept(
            learner.id, "test", "Test", outcome.id
        )
        session = graph.start_session(learner.id, outcome.id)

        event = graph.create_application_event(
            learner.id,
            session.id,
            concept_ids=[concept.id],
            context="test event",
        )

        followup_session = graph.start_session(learner.id, outcome.id)
        updated = graph.record_followup(
            event.id,
            followup_session.id,
            outcome_result="mixed",
            what_worked="Said price confidently",
            what_struggled="Caved on discount",
            gaps_revealed=["discount-negotiation"],
            insights="Need more practice with objections",
        )

        assert updated.outcome_result == "mixed"
        assert updated.gaps_revealed == ["discount-negotiation"]


class TestEndToEndScenario:
    """End-to-end test simulating a learning session."""

    def test_complete_learning_flow(self, graph):
        # 1. Create learner
        learner = graph.get_or_create_learner(
            profile=LearnerProfile(
                name="Alice",
                context="freelance designer",
                age_group=AgeGroup.ADULT,
            )
        )
        assert learner.profile.name == "Alice"

        # 2. Create outcome (goal)
        outcome = graph.create_outcome(
            learner.id,
            stated_goal="Price freelance services confidently",
            motivation="I know I'm undercharging",
        )
        assert outcome.stated_goal == "Price freelance services confidently"

        # 3. Start session
        session = graph.start_session(
            learner.id,
            outcome.id,
            context=SessionContext(
                energy=EnergyLevel.MEDIUM,
                mindset="focused but nervous",
                intention_strength=IntentionStrength.LEARNING,
            ),
        )
        assert session.context.energy == EnergyLevel.MEDIUM

        # 4. Discover gap (create concept)
        concept = graph.create_concept(
            learner.id,
            name="value-articulation",
            display_name="Value Articulation",
            discovered_from=outcome.id,
            description="How to explain why your work is worth what you charge",
        )
        assert concept.discovered_from == outcome.id

        # 5. Add some conversation
        graph.add_message(
            session,
            Message(role="sage", content="What's blocking you from charging more?"),
        )
        graph.add_message(
            session,
            Message(role="user", content="I don't know how to explain my value"),
        )

        # 6. Create proof (learner demonstrated understanding)
        proof = graph.create_proof(
            learner.id,
            concept.id,
            session.id,
            demonstration_type=DemoType.APPLICATION,
            evidence="Successfully reframed price as value investment",
            exchange=ProofExchange(
                prompt="How would you respond to 'Why so expensive?'",
                response="You're not buying a logo, you're buying...",
                analysis="Correctly reframed from cost to value",
            ),
            confidence=0.85,
        )
        assert proof.confidence == 0.85

        # 7. Create application event (they'll use this in real world)
        event = graph.create_application_event(
            learner.id,
            session.id,
            concept_ids=[concept.id],
            context="pricing call with new client tomorrow",
            stakes="high",
        )
        assert event.stakes == "high"

        # 8. End session
        graph.end_session(
            session,
            summary="Found value articulation gap, taught reframing, earned proof",
            ending_state=SessionEndingState(
                mode="verification",
                current_focus="value-articulation",
                next_step="Check on pricing call result",
            ),
        )

        # 9. Verify final state
        state = graph.get_learner_state(learner.id)
        assert state.total_proofs == 1
        assert len(state.proven_concepts) == 1
        assert state.proven_concepts[0].name == "value-articulation"

        progress = graph.get_outcome_progress(outcome.id)
        assert progress["concepts_understood"] == 1
