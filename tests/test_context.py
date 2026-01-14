"""Tests for the context management module."""

from datetime import date, datetime, timedelta
import pytest

from sage.context import (
    ApplicationLifecycle,
    ApplicationSnapshot,
    ConceptSnapshot,
    FollowupResult,
    FullContext,
    FullContextLoader,
    GapIdentified,
    InsightsTracker,
    LearnerSnapshot,
    OutcomeProgress,
    OutcomeSnapshot,
    ProofEarned,
    ProofSnapshot,
    RelatedConcept,
    TurnChanges,
    TurnContext,
    TurnContextBuilder,
    TurnPersistence,
    UpcomingApplication,
    build_turn_context,
    detect_application_in_message,
    detect_application_patterns,
    generate_followup_prompt,
    persist_turn,
)
from sage.graph.learning_graph import LearningGraph
from sage.graph.models import (
    AgeGroup,
    ApplicationEvent,
    ApplicationStatus,
    Concept,
    ConceptStatus,
    DemoType,
    DialogueMode,
    Edge,
    EdgeType,
    EnergyLevel,
    IntentionStrength,
    Learner,
    LearnerInsights,
    LearnerPreferences,
    LearnerProfile,
    Outcome,
    OutcomeStatus,
    Proof,
    ProofExchange,
    Session,
    SessionContext,
    SkillLevel,
)


@pytest.fixture
def graph():
    """Create a fresh LearningGraph for each test."""
    return LearningGraph()


@pytest.fixture
def learner(graph):
    """Create a test learner."""
    learner = Learner(
        profile=LearnerProfile(
            name="Test User",
            context="Software developer",
            age_group=AgeGroup.ADULT,
            skill_level=SkillLevel.INTERMEDIATE,
        ),
        preferences=LearnerPreferences(session_length="medium"),
        insights=LearnerInsights(
            prefers_examples=True,
            prefers_theory_first=False,
        ),
    )
    return graph.create_learner(learner)


@pytest.fixture
def outcome(graph, learner):
    """Create a test outcome."""
    outcome = Outcome(
        learner_id=learner.id,
        stated_goal="Learn to price freelance services",
        clarified_goal="Confidently set and hold prices in client calls",
        success_criteria="Complete 3 pricing calls without caving on discounts",
        status=OutcomeStatus.ACTIVE,
    )
    outcome = graph.create_outcome_obj(outcome)

    # Set as active outcome
    learner.active_outcome_id = outcome.id
    graph.update_learner(learner)

    return outcome


@pytest.fixture
def concept(graph, learner, outcome):
    """Create a test concept."""
    concept = Concept(
        learner_id=learner.id,
        name="value-articulation",
        display_name="Value Articulation",
        description="How to clearly communicate your value to clients",
        discovered_from=outcome.id,
        status=ConceptStatus.UNDERSTOOD,
    )
    return graph.create_concept_obj(concept)


@pytest.fixture
def proof(graph, learner, concept):
    """Create a test proof."""
    session = Session(learner_id=learner.id)
    session = graph.create_session(session)

    proof = Proof(
        learner_id=learner.id,
        concept_id=concept.id,
        session_id=session.id,
        demonstration_type=DemoType.EXPLANATION,
        evidence="Correctly explained how to frame value to clients",
        confidence=0.9,
        exchange=ProofExchange(
            prompt="How would you explain your value to a client?",
            response="I focus on the outcomes they'll get, not hours worked",
            analysis="Shows understanding of value-based communication",
        ),
    )
    return graph.create_proof_obj(proof)


@pytest.fixture
def session(graph, learner, outcome):
    """Create a test session."""
    session = Session(
        learner_id=learner.id,
        outcome_id=outcome.id,
        context=SessionContext(
            energy=EnergyLevel.MEDIUM,
            mindset="focused and ready to learn",
            time_available="1 hour",
            intention_strength=IntentionStrength.LEARNING,
        ),
    )
    return graph.create_session(session)


# =============================================================================
# Snapshot Tests
# =============================================================================


class TestSnapshots:
    """Tests for snapshot models."""

    def test_learner_snapshot_from_learner(self, learner):
        """Test creating LearnerSnapshot from Learner."""
        snapshot = LearnerSnapshot.from_learner(learner)

        assert snapshot.id == learner.id
        assert snapshot.name == "Test User"
        assert snapshot.age_group == "adult"
        assert snapshot.skill_level == "intermediate"
        assert snapshot.prefers_examples is True
        assert snapshot.prefers_theory_first is False

    def test_outcome_snapshot_from_outcome(self, outcome):
        """Test creating OutcomeSnapshot from Outcome."""
        snapshot = OutcomeSnapshot.from_outcome(outcome)

        assert snapshot.id == outcome.id
        assert snapshot.stated_goal == "Learn to price freelance services"
        assert snapshot.status == "active"

    def test_concept_snapshot_from_concept(self, concept, proof):
        """Test creating ConceptSnapshot from Concept with proof."""
        snapshot = ConceptSnapshot.from_concept(concept, proof)

        assert snapshot.id == concept.id
        assert snapshot.name == "value-articulation"
        assert snapshot.display_name == "Value Articulation"
        assert snapshot.has_proof is True
        assert snapshot.proof_confidence == 0.9

    def test_concept_snapshot_without_proof(self, concept):
        """Test creating ConceptSnapshot without proof."""
        snapshot = ConceptSnapshot.from_concept(concept)

        assert snapshot.has_proof is False
        assert snapshot.proof_confidence is None

    def test_application_snapshot(self, graph, learner, concept, session):
        """Test creating ApplicationSnapshot."""
        app = ApplicationEvent(
            learner_id=learner.id,
            concept_ids=[concept.id],
            session_id=session.id,
            context="pricing call with new client",
            planned_date=date.today(),
            status=ApplicationStatus.UPCOMING,
        )
        app = graph.create_application_event_obj(app)

        concept_names = {concept.id: concept.display_name}
        snapshot = ApplicationSnapshot.from_application_event(app, concept_names)

        assert snapshot.id == app.id
        assert snapshot.context == "pricing call with new client"
        assert "Value Articulation" in snapshot.concepts_applied

    def test_outcome_progress(self, outcome, concept, proof):
        """Test OutcomeProgress calculation."""
        progress = OutcomeProgress.from_outcome_and_concepts(
            outcome=outcome,
            concepts=[concept],
            proofs=[proof],
        )

        assert progress.outcome_id == outcome.id
        assert progress.concepts_identified == 1
        assert progress.concepts_proven == 1


# =============================================================================
# Full Context Tests
# =============================================================================


class TestFullContext:
    """Tests for FullContext loading."""

    def test_load_basic_context(self, graph, learner):
        """Test loading basic context for a learner."""
        loader = FullContextLoader(graph)
        context = loader.load(learner.id)

        assert context.learner.id == learner.id
        assert context.insights is not None
        assert context.proven_concepts == []
        assert context.active_outcome is None

    def test_load_with_outcome(self, graph, learner, outcome):
        """Test loading context with active outcome."""
        loader = FullContextLoader(graph)
        context = loader.load(learner.id)

        assert context.active_outcome is not None
        assert context.active_outcome.id == outcome.id

    def test_load_with_proven_concepts(self, graph, learner, concept, proof):
        """Test loading context with proven concepts."""
        loader = FullContextLoader(graph)
        context = loader.load(learner.id)

        assert len(context.proven_concepts) == 1
        assert context.proven_concepts[0].id == concept.id

    def test_load_pending_followups(self, graph, learner, concept, session):
        """Test loading pending follow-ups."""
        # Create an application that's past due
        app = ApplicationEvent(
            learner_id=learner.id,
            concept_ids=[concept.id],
            session_id=session.id,
            context="past pricing call",
            planned_date=date.today() - timedelta(days=2),
            status=ApplicationStatus.UPCOMING,
        )
        graph.create_application_event_obj(app)

        loader = FullContextLoader(graph)
        context = loader.load(learner.id)

        assert len(context.pending_followups) == 1

    def test_load_nonexistent_learner(self, graph):
        """Test loading context for nonexistent learner raises error."""
        loader = FullContextLoader(graph)

        with pytest.raises(ValueError, match="Learner not found"):
            loader.load("nonexistent-id")


# =============================================================================
# Turn Context Tests
# =============================================================================


class TestTurnContext:
    """Tests for TurnContext building."""

    def test_build_basic_context(self, graph, learner, session):
        """Test building basic turn context."""
        loader = FullContextLoader(graph)
        full_context = loader.load(learner.id)

        builder = TurnContextBuilder(full_context, session)
        turn_ctx = builder.build(DialogueMode.PROBING)

        assert turn_ctx.mode == DialogueMode.PROBING
        assert turn_ctx.learner.id == learner.id

    def test_build_with_current_concept(self, graph, learner, concept, session):
        """Test building context with current concept."""
        loader = FullContextLoader(graph)
        full_context = loader.load(learner.id)

        builder = TurnContextBuilder(full_context, session)
        turn_ctx = builder.build(DialogueMode.TEACHING, current_concept=concept)

        assert turn_ctx.current_concept is not None
        assert turn_ctx.current_concept.name == "value-articulation"

    def test_adaptation_hints_low_energy(self, graph, learner):
        """Test adaptation hints for low energy."""
        session = Session(
            learner_id=learner.id,
            context=SessionContext(energy=EnergyLevel.LOW),
        )
        session = graph.create_session(session)

        loader = FullContextLoader(graph)
        full_context = loader.load(learner.id)

        builder = TurnContextBuilder(full_context, session)
        turn_ctx = builder.build(DialogueMode.TEACHING)

        assert any("SHORT" in h for h in turn_ctx.adaptation_hints)

    def test_adaptation_hints_urgent(self, graph, learner):
        """Test adaptation hints for urgent intention."""
        session = Session(
            learner_id=learner.id,
            context=SessionContext(intention_strength=IntentionStrength.URGENT),
        )
        session = graph.create_session(session)

        loader = FullContextLoader(graph)
        full_context = loader.load(learner.id)

        builder = TurnContextBuilder(full_context, session)
        turn_ctx = builder.build(DialogueMode.TEACHING)

        assert any("theory" in h.lower() for h in turn_ctx.adaptation_hints)

    def test_build_turn_context_convenience(self, graph, learner, session):
        """Test convenience function for building turn context."""
        loader = FullContextLoader(graph)
        full_context = loader.load(learner.id)

        turn_ctx = build_turn_context(
            full_context, session, DialogueMode.CHECK_IN
        )

        assert turn_ctx.mode == DialogueMode.CHECK_IN


# =============================================================================
# Persistence Tests
# =============================================================================


class TestPersistence:
    """Tests for turn persistence."""

    def test_persist_messages(self, graph, learner, session):
        """Test persisting messages."""
        changes = TurnChanges(
            user_message="I want to learn pricing",
            sage_message="Great! Let's explore what's blocking you.",
            sage_mode=DialogueMode.PROBING,
        )

        updated_session = persist_turn(graph, session, changes)

        assert len(updated_session.messages) == 2
        assert updated_session.messages[0].role == "user"
        assert updated_session.messages[1].role == "sage"

    def test_persist_gap_identified(self, graph, learner, outcome, session):
        """Test persisting identified gap."""
        changes = TurnChanges(
            user_message="I don't know how to handle objections",
            sage_message="Let's work on that.",
            sage_mode=DialogueMode.PROBING,
            gap_identified=GapIdentified(
                name="handling-objections",
                display_name="Handling Objections",
                description="How to respond when clients push back",
                blocking_outcome_id=outcome.id,
            ),
        )

        updated_session = persist_turn(graph, session, changes)

        # Check concept was created
        concepts = graph.get_concepts_by_learner(learner.id)
        assert any(c.name == "handling-objections" for c in concepts)

    def test_persist_proof_earned(self, graph, learner, concept, session):
        """Test persisting earned proof."""
        changes = TurnChanges(
            user_message="I would explain the outcomes they get",
            sage_message="Exactly right!",
            sage_mode=DialogueMode.VERIFICATION,
            proof_earned=ProofEarned(
                concept_id=concept.id,
                demonstration_type="explanation",
                evidence="Correctly explained value-based pricing",
                confidence=0.85,
                prompt="How would you explain your value?",
                response="I focus on outcomes, not hours",
                analysis="Shows clear understanding",
            ),
        )

        # Get initial proof count
        initial_proofs = learner.total_proofs

        updated_session = persist_turn(graph, session, changes)

        # Check proof was created
        proofs = graph.get_proofs_by_learner(learner.id)
        assert len(proofs) >= 1

        # Check session tracks proof
        assert len(updated_session.proofs_earned) == 1


# =============================================================================
# Insights Tests
# =============================================================================


class TestInsights:
    """Tests for learner insights tracking."""

    def test_add_pattern(self, graph, learner):
        """Test adding a pattern observation."""
        tracker = InsightsTracker(graph)
        tracker.add_pattern(learner.id, "Responds well to analogies")

        updated_learner = graph.get_learner(learner.id)
        assert "Responds well to analogies" in updated_learner.insights.patterns

    def test_add_effective_approach(self, graph, learner):
        """Test adding an effective approach."""
        tracker = InsightsTracker(graph)
        tracker.add_effective_approach(learner.id, "Socratic questioning")

        updated_learner = graph.get_learner(learner.id)
        assert "Socratic questioning" in updated_learner.insights.effective_approaches

    def test_update_preferences(self, graph, learner):
        """Test updating preferences."""
        tracker = InsightsTracker(graph)
        insights = tracker.update_preferences(
            learner.id,
            prefers_theory_first=True,
            needs_frequent_checks=True,
        )

        assert insights.prefers_theory_first is True
        assert insights.needs_frequent_checks is True

    def test_detect_application_patterns(self, graph, learner, concept, session):
        """Test detecting patterns in applications."""
        # Create multiple completed applications with same struggle
        for i in range(2):
            app = ApplicationEvent(
                learner_id=learner.id,
                concept_ids=[concept.id],
                session_id=session.id,
                context=f"call {i}",
                status=ApplicationStatus.COMPLETED,
                what_struggled="caved on discount",
            )
            graph.create_application_event_obj(app)

        patterns = detect_application_patterns(graph, learner.id)

        assert any("caved on discount" in p for p in patterns)


# =============================================================================
# Application Lifecycle Tests
# =============================================================================


class TestApplicationLifecycle:
    """Tests for application event lifecycle."""

    def test_create_application(self, graph, learner, concept, session):
        """Test creating an application event."""
        lifecycle = ApplicationLifecycle(graph)

        app = lifecycle.create_application(
            learner_id=learner.id,
            session_id=session.id,
            application=UpcomingApplication(
                context="pricing call tomorrow",
                concept_ids=[concept.id],
                outcome_id=None,
                planned_date=date.today() + timedelta(days=1),
                stakes="high",
            ),
        )

        assert app.status == ApplicationStatus.UPCOMING
        assert app.context == "pricing call tomorrow"

    def test_get_pending_followups(self, graph, learner, concept, session):
        """Test getting pending follow-ups."""
        lifecycle = ApplicationLifecycle(graph)

        # Create past-due application
        app = ApplicationEvent(
            learner_id=learner.id,
            concept_ids=[concept.id],
            session_id=session.id,
            context="past call",
            planned_date=date.today() - timedelta(days=1),
            status=ApplicationStatus.UPCOMING,
        )
        graph.create_application_event_obj(app)

        pending = lifecycle.get_pending_followups(learner.id)

        assert len(pending) == 1
        assert pending[0].status == ApplicationStatus.PENDING_FOLLOWUP

    def test_complete_followup(self, graph, learner, concept, session):
        """Test completing a follow-up."""
        lifecycle = ApplicationLifecycle(graph)

        # Create application
        app = ApplicationEvent(
            learner_id=learner.id,
            concept_ids=[concept.id],
            session_id=session.id,
            context="pricing call",
            status=ApplicationStatus.PENDING_FOLLOWUP,
        )
        app = graph.create_application_event_obj(app)

        # Complete followup
        result = FollowupResult(
            outcome_result="mixed",
            what_worked="Stated price confidently",
            what_struggled="Caved on discount request",
            gaps_revealed=["handling-discount-pressure"],
            learner_insight="I need to practice saying no",
        )

        updated_app, new_concepts = lifecycle.complete_followup(
            app.id, session.id, result
        )

        assert updated_app.status == ApplicationStatus.COMPLETED
        assert updated_app.what_worked == "Stated price confidently"
        assert len(new_concepts) == 1
        assert new_concepts[0].name == "handling-discount-pressure"

    def test_generate_followup_prompt(self, graph, learner, concept, session):
        """Test generating follow-up prompt."""
        app = ApplicationEvent(
            learner_id=learner.id,
            concept_ids=[concept.id],
            session_id=session.id,
            context="pricing call",
            planned_date=date.today() - timedelta(days=1),
            stakes="high",
        )

        prompt = generate_followup_prompt(app)

        assert "pricing call" in prompt
        assert "important" in prompt.lower()

    def test_detect_application_in_message(self):
        """Test detecting application mentions in messages."""
        message = "I have a pricing call tomorrow with a new client"

        app = detect_application_in_message(message, ["concept-123"])

        assert app is not None
        assert "pricing call" in app.context
        assert "concept-123" in app.concept_ids

    def test_no_application_in_message(self):
        """Test that non-application messages return None."""
        message = "I understand the concept now"

        app = detect_application_in_message(message, ["concept-123"])

        assert app is None
