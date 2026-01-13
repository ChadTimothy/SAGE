"""Tests for SAGE Learning Graph models."""

import json
from datetime import date, datetime

import pytest

from sage.graph.models import (
    # Enums
    AgeGroup,
    ApplicationStatus,
    ConceptStatus,
    DemoType,
    DialogueMode,
    EdgeType,
    EnergyLevel,
    ExplorationDepth,
    IntentionStrength,
    OutcomeStatus,
    SkillLevel,
    # Node models
    ApplicationEvent,
    Concept,
    Edge,
    Learner,
    LearnerInsights,
    LearnerPreferences,
    LearnerProfile,
    Message,
    Outcome,
    Proof,
    ProofExchange,
    Session,
    SessionContext,
    SessionEndingState,
    # Edge metadata
    RelatesToMetadata,
    # Utilities
    gen_id,
)


class TestGenId:
    """Tests for ID generation."""

    def test_gen_id_returns_string(self):
        id_val = gen_id()
        assert isinstance(id_val, str)

    def test_gen_id_unique(self):
        ids = [gen_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique


class TestEnums:
    """Tests for enum definitions."""

    def test_outcome_status_values(self):
        assert OutcomeStatus.ACTIVE == "active"
        assert OutcomeStatus.ACHIEVED == "achieved"
        assert OutcomeStatus.PAUSED == "paused"
        assert OutcomeStatus.ABANDONED == "abandoned"

    def test_concept_status_values(self):
        assert ConceptStatus.IDENTIFIED == "identified"
        assert ConceptStatus.TEACHING == "teaching"
        assert ConceptStatus.UNDERSTOOD == "understood"

    def test_dialogue_mode_values(self):
        modes = [
            DialogueMode.CHECK_IN,
            DialogueMode.FOLLOWUP,
            DialogueMode.OUTCOME_DISCOVERY,
            DialogueMode.FRAMING,
            DialogueMode.PROBING,
            DialogueMode.TEACHING,
            DialogueMode.VERIFICATION,
            DialogueMode.OUTCOME_CHECK,
        ]
        assert len(modes) == 8

    def test_edge_type_values(self):
        edges = [
            EdgeType.REQUIRES,
            EdgeType.RELATES_TO,
            EdgeType.DEMONSTRATED_BY,
            EdgeType.EXPLORED_IN,
            EdgeType.BUILDS_ON,
            EdgeType.APPLIED_IN,
        ]
        assert len(edges) == 6

    def test_age_group_values(self):
        assert AgeGroup.CHILD == "child"
        assert AgeGroup.TEEN == "teen"
        assert AgeGroup.ADULT == "adult"

    def test_skill_level_values(self):
        assert SkillLevel.BEGINNER == "beginner"
        assert SkillLevel.INTERMEDIATE == "intermediate"
        assert SkillLevel.ADVANCED == "advanced"


class TestLearner:
    """Tests for Learner model."""

    def test_learner_defaults(self):
        learner = Learner()
        assert learner.id is not None
        assert learner.profile is not None
        assert learner.preferences is not None
        assert learner.insights is not None
        assert learner.active_outcome_id is None
        assert learner.total_sessions == 0
        assert learner.total_proofs == 0

    def test_learner_with_profile(self):
        learner = Learner(
            profile=LearnerProfile(
                name="Alice",
                context="freelance designer",
                age_group=AgeGroup.ADULT,
                skill_level=SkillLevel.INTERMEDIATE,
            )
        )
        assert learner.profile.name == "Alice"
        assert learner.profile.age_group == AgeGroup.ADULT
        assert learner.profile.skill_level == SkillLevel.INTERMEDIATE

    def test_learner_serialization(self):
        learner = Learner(
            profile=LearnerProfile(name="Bob", age_group=AgeGroup.TEEN)
        )
        json_str = learner.model_dump_json()
        data = json.loads(json_str)
        assert data["profile"]["name"] == "Bob"
        assert data["profile"]["age_group"] == "teen"

    def test_learner_deserialization(self):
        data = {
            "id": "test-123",
            "profile": {"name": "Charlie", "age_group": "child"},
            "total_sessions": 5,
        }
        learner = Learner.model_validate(data)
        assert learner.id == "test-123"
        assert learner.profile.name == "Charlie"
        assert learner.profile.age_group == AgeGroup.CHILD
        assert learner.total_sessions == 5


class TestOutcome:
    """Tests for Outcome model."""

    def test_outcome_required_fields(self):
        outcome = Outcome(learner_id="learner-1", stated_goal="Learn to code")
        assert outcome.id is not None
        assert outcome.learner_id == "learner-1"
        assert outcome.stated_goal == "Learn to code"
        assert outcome.status == OutcomeStatus.ACTIVE

    def test_outcome_with_all_fields(self):
        outcome = Outcome(
            learner_id="learner-1",
            stated_goal="Price freelance services better",
            clarified_goal="Confidently set and defend higher rates",
            motivation="I know I'm undercharging",
            success_criteria="Have a pricing conversation without anxiety",
            territory=["knowing your value", "articulating it", "handling pushback"],
        )
        assert outcome.territory is not None
        assert len(outcome.territory) == 3

    def test_outcome_serialization(self):
        outcome = Outcome(
            learner_id="learner-1",
            stated_goal="Test goal",
            status=OutcomeStatus.ACHIEVED,
        )
        data = json.loads(outcome.model_dump_json())
        assert data["status"] == "achieved"


class TestConcept:
    """Tests for Concept model."""

    def test_concept_creation(self):
        concept = Concept(
            learner_id="learner-1",
            name="value-articulation",
            display_name="Value Articulation",
            description="Being able to explain why your work is worth what you charge",
            discovered_from="outcome-1",
        )
        assert concept.status == ConceptStatus.IDENTIFIED
        assert concept.times_discussed == 0
        assert concept.understood_at is None

    def test_concept_status_progression(self):
        concept = Concept(
            learner_id="learner-1",
            name="test",
            display_name="Test",
            status=ConceptStatus.TEACHING,
        )
        assert concept.status == ConceptStatus.TEACHING


class TestProof:
    """Tests for Proof model."""

    def test_proof_creation(self):
        exchange = ProofExchange(
            prompt="Client says: 'Why should I pay you $2000?' What do you say?",
            response="You're not comparing the same thing...",
            analysis="Demonstrated value framing without mentioning costs.",
        )
        proof = Proof(
            learner_id="learner-1",
            concept_id="concept-1",
            session_id="session-1",
            demonstration_type=DemoType.APPLICATION,
            evidence="Successfully reframed a price objection",
            confidence=0.85,
            exchange=exchange,
        )
        assert proof.demonstration_type == DemoType.APPLICATION
        assert proof.confidence == 0.85
        assert proof.exchange.prompt.startswith("Client says")


class TestSession:
    """Tests for Session model."""

    def test_session_creation(self):
        session = Session(learner_id="learner-1", outcome_id="outcome-1")
        assert session.messages == []
        assert session.concepts_explored == []
        assert session.proofs_earned == []

    def test_session_with_context(self):
        context = SessionContext(
            energy=EnergyLevel.HIGH,
            mindset="excited to learn",
            time_available="2 hours",
            intention_strength=IntentionStrength.LEARNING,
        )
        session = Session(
            learner_id="learner-1",
            context=context,
        )
        assert session.context.energy == EnergyLevel.HIGH
        assert session.context.intention_strength == IntentionStrength.LEARNING

    def test_session_with_messages(self):
        messages = [
            Message(role="sage", content="What would you like to learn?"),
            Message(role="user", content="I want to learn about pricing."),
        ]
        session = Session(learner_id="learner-1", messages=messages)
        assert len(session.messages) == 2
        assert session.messages[0].role == "sage"
        assert session.messages[1].role == "user"

    def test_session_ending_state(self):
        ending = SessionEndingState(
            mode="probing",
            current_focus="value-articulation",
            next_step="Continue exploring pricing psychology",
        )
        session = Session(learner_id="learner-1", ending_state=ending)
        assert session.ending_state.mode == "probing"


class TestApplicationEvent:
    """Tests for ApplicationEvent model."""

    def test_application_event_creation(self):
        event = ApplicationEvent(
            learner_id="learner-1",
            concept_ids=["concept-1", "concept-2"],
            session_id="session-1",
            context="pricing call tomorrow at 2pm",
            planned_date=date(2024, 1, 16),
            stakes="high",
        )
        assert event.status == ApplicationStatus.UPCOMING
        assert len(event.concept_ids) == 2

    def test_application_event_followup(self):
        event = ApplicationEvent(
            learner_id="learner-1",
            concept_ids=["concept-1"],
            session_id="session-1",
            context="client meeting",
            status=ApplicationStatus.COMPLETED,
            outcome_result="mixed",
            what_worked="Stated price confidently",
            what_struggled="Caved on discount too quickly",
            gaps_revealed=["discount-negotiation"],
        )
        assert event.status == ApplicationStatus.COMPLETED
        assert event.gaps_revealed == ["discount-negotiation"]


class TestEdge:
    """Tests for Edge model."""

    def test_requires_edge(self):
        edge = Edge(
            from_id="outcome-1",
            from_type="outcome",
            to_id="concept-1",
            to_type="concept",
            edge_type=EdgeType.REQUIRES,
        )
        assert edge.edge_type == EdgeType.REQUIRES

    def test_relates_to_edge_with_metadata(self):
        metadata = RelatesToMetadata(
            relationship="Pricing psychology connects to negotiation tactics",
            strength=0.75,
            discovered_in="session-5",
        )
        edge = Edge(
            from_id="concept-1",
            from_type="concept",
            to_id="concept-2",
            to_type="concept",
            edge_type=EdgeType.RELATES_TO,
            metadata=metadata.model_dump(),
        )
        assert edge.metadata["strength"] == 0.75

    def test_edge_serialization(self):
        edge = Edge(
            from_id="concept-1",
            from_type="concept",
            to_id="proof-1",
            to_type="proof",
            edge_type=EdgeType.DEMONSTRATED_BY,
        )
        data = json.loads(edge.model_dump_json())
        assert data["edge_type"] == "demonstrated_by"


class TestJsonSerialization:
    """Tests for JSON serialization/deserialization round trips."""

    def test_learner_round_trip(self):
        original = Learner(
            profile=LearnerProfile(
                name="Test User",
                age_group=AgeGroup.ADULT,
                skill_level=SkillLevel.BEGINNER,
            ),
            insights=LearnerInsights(
                prefers_examples=True,
                effective_approaches=["analogies", "real-world examples"],
            ),
        )
        json_str = original.model_dump_json()
        restored = Learner.model_validate_json(json_str)
        assert restored.profile.name == original.profile.name
        assert restored.insights.effective_approaches == ["analogies", "real-world examples"]

    def test_session_round_trip(self):
        original = Session(
            learner_id="learner-1",
            context=SessionContext(energy=EnergyLevel.MEDIUM),
            messages=[
                Message(role="sage", content="Hello!"),
                Message(role="user", content="Hi there."),
            ],
            ending_state=SessionEndingState(mode="probing"),
        )
        json_str = original.model_dump_json()
        restored = Session.model_validate_json(json_str)
        assert len(restored.messages) == 2
        assert restored.context.energy == EnergyLevel.MEDIUM
