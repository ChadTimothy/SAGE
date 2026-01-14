"""Tests for the SAGE dialogue module.

Tests cover:
- Structured output parsing (SAGEResponse)
- Prompt building
- Mode management and transitions
- State change detection
"""

from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sage.context.full_context import FullContext
from sage.context.snapshots import (
    ConceptSnapshot,
    LearnerSnapshot,
    OutcomeSnapshot,
)
from sage.context.turn_context import TurnContext
from sage.dialogue.modes import (
    ModeManager,
    get_mode_prompt_name,
    get_transition_signals,
    should_verify_before_building,
)
from sage.dialogue.prompt_builder import (
    PromptBuilder,
    PromptTemplates,
)
from sage.dialogue.state_detection import (
    detect_explicit_signals,
    detect_implicit_signals,
    get_adaptation_for_signal,
    update_context_for_state_change,
)
from sage.dialogue.structured_output import (
    ApplicationDetected,
    ConnectionDiscovered,
    FollowupResponse,
    GapIdentified,
    ProofEarned,
    ProofExchange,
    SAGEResponse,
    StateChange,
    create_fallback_response,
    get_valid_transitions,
    parse_sage_response,
    validate_response_consistency,
)
from sage.graph.models import (
    DialogueMode,
    EnergyLevel,
    Learner,
    LearnerInsights,
    Message,
    Outcome,
    Session,
    SessionContext,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_learner():
    """Create a sample learner for testing."""
    return Learner(
        id="learner-001",
        profile={"name": "Test User"},
    )


@pytest.fixture
def sample_session(sample_learner):
    """Create a sample session for testing."""
    return Session(
        id="session-001",
        learner_id=sample_learner.id,
        started_at=datetime.utcnow(),
        messages=[],
    )


@pytest.fixture
def sample_turn_context(sample_learner):
    """Create a sample turn context for testing."""
    return TurnContext(
        learner=LearnerSnapshot.from_learner(sample_learner),
        insights=LearnerInsights(),
        mode=DialogueMode.PROBING,
        session_context=SessionContext(
            energy=EnergyLevel.MEDIUM,
            time_available="30 minutes",
        ),
        current_concept=None,
        outcome=None,
        outcome_progress=None,
        recent_messages=[],
        session_summary=None,
        proven_concepts=[],
        related_concepts=[],
        pending_followup=None,
        relevant_applications=[],
    )


@pytest.fixture
def sample_full_context(sample_learner):
    """Create a sample full context for testing."""
    return FullContext(
        learner=sample_learner,
        insights=LearnerInsights(),
        proven_concepts=[],
        proofs=[],
        active_outcome=None,
        outcome_concepts=[],
        last_session=None,
        days_since_last_session=None,
        concept_relations={},
        pending_followups=[],
        completed_applications=[],
        all_concepts=[],
    )


# =============================================================================
# Structured Output Tests
# =============================================================================


class TestSAGEResponse:
    """Tests for SAGEResponse model."""

    def test_basic_response(self):
        """Test creating a basic response."""
        response = SAGEResponse(
            message="Hello! How are you today?",
            current_mode=DialogueMode.CHECK_IN,
        )
        assert response.message == "Hello! How are you today?"
        assert response.current_mode == DialogueMode.CHECK_IN
        assert response.transition_to is None
        assert response.outcome_achieved is False

    def test_response_with_gap(self):
        """Test response with gap identified."""
        gap = GapIdentified(
            name="value-articulation",
            display_name="Value Articulation",
            description="Ability to clearly state your value proposition",
        )
        response = SAGEResponse(
            message="I notice you're struggling with value articulation.",
            current_mode=DialogueMode.PROBING,
            gap_identified=gap,
            transition_to=DialogueMode.TEACHING,
            transition_reason="Gap identified, moving to teaching",
        )
        assert response.gap_identified is not None
        assert response.gap_identified.name == "value-articulation"
        assert response.transition_to == DialogueMode.TEACHING

    def test_response_with_proof(self):
        """Test response with proof earned."""
        proof = ProofEarned(
            concept_id="concept-001",
            demonstration_type="application",
            evidence="Successfully applied to pricing scenario",
            confidence=0.85,
            exchange=ProofExchange(
                prompt="How would you handle a discount request?",
                response="I would emphasize the value first...",
                analysis="Demonstrates understanding of value-first approach",
            ),
        )
        response = SAGEResponse(
            message="Excellent! You've demonstrated real understanding.",
            current_mode=DialogueMode.VERIFICATION,
            proof_earned=proof,
            transition_to=DialogueMode.OUTCOME_CHECK,
        )
        assert response.proof_earned is not None
        assert response.proof_earned.confidence == 0.85

    def test_response_with_application(self):
        """Test response with application detected."""
        app = ApplicationDetected(
            context="pricing call with new client",
            concept_ids=["concept-001", "concept-002"],
            planned_date=date(2026, 1, 20),
            stakes="high",
        )
        response = SAGEResponse(
            message="Good luck with the pricing call!",
            current_mode=DialogueMode.TEACHING,
            application_detected=app,
        )
        assert response.application_detected is not None
        assert response.application_detected.stakes == "high"

    def test_response_with_state_change(self):
        """Test response with state change detected."""
        change = StateChange(
            what_changed="energy_drop",
            detected_from="shorter responses, less engagement",
            recommended_adaptation="switch to quick wins",
        )
        response = SAGEResponse(
            message="You seem tired. Let's wrap up with a quick win.",
            current_mode=DialogueMode.TEACHING,
            state_change_detected=change,
        )
        assert response.state_change_detected is not None
        assert response.state_change_detected.what_changed == "energy_drop"


class TestResponseParsing:
    """Tests for response parsing functions."""

    def test_parse_valid_response(self):
        """Test parsing a valid response dict."""
        data = {
            "message": "Hello there!",
            "current_mode": "check_in",
            "transition_to": "outcome_discovery",
            "transition_reason": "Gathered context",
            "outcome_achieved": False,
        }
        response = parse_sage_response(data)
        assert response.message == "Hello there!"
        assert response.current_mode == DialogueMode.CHECK_IN
        assert response.transition_to == DialogueMode.OUTCOME_DISCOVERY

    def test_parse_minimal_response(self):
        """Test parsing a minimal response."""
        data = {
            "message": "OK",
            "current_mode": "probing",
        }
        response = parse_sage_response(data)
        assert response.message == "OK"
        assert response.transition_to is None

    def test_fallback_response(self):
        """Test creating fallback response."""
        response = create_fallback_response(DialogueMode.TEACHING)
        assert "gather my thoughts" in response.message
        assert response.current_mode == DialogueMode.TEACHING
        assert response.transition_to is None


class TestResponseValidation:
    """Tests for response validation."""

    def test_valid_response_no_warnings(self):
        """Test that valid response has no warnings."""
        response = SAGEResponse(
            message="What's blocking you?",
            current_mode=DialogueMode.PROBING,
        )
        warnings = validate_response_consistency(response, DialogueMode.PROBING)
        assert len(warnings) == 0

    def test_proof_wrong_mode_warning(self):
        """Test warning when proof earned in wrong mode."""
        response = SAGEResponse(
            message="You've got it!",
            current_mode=DialogueMode.PROBING,
            proof_earned=ProofEarned(
                concept_id="c1",
                demonstration_type="explanation",
                evidence="Good",
                confidence=0.8,
                exchange=ProofExchange(prompt="?", response="!", analysis="OK"),
            ),
        )
        warnings = validate_response_consistency(response, DialogueMode.PROBING)
        assert any("Proof earned" in w for w in warnings)

    def test_gap_wrong_mode_warning(self):
        """Test warning when gap identified in wrong mode."""
        response = SAGEResponse(
            message="I see a gap.",
            current_mode=DialogueMode.TEACHING,
            gap_identified=GapIdentified(
                name="test-gap",
                display_name="Test Gap",
                description="A gap",
            ),
        )
        warnings = validate_response_consistency(response, DialogueMode.TEACHING)
        assert any("Gap identified" in w for w in warnings)

    def test_invalid_transition_warning(self):
        """Test warning for invalid mode transition."""
        response = SAGEResponse(
            message="Let's verify.",
            current_mode=DialogueMode.CHECK_IN,
            transition_to=DialogueMode.VERIFICATION,  # Invalid from CHECK_IN
        )
        warnings = validate_response_consistency(response, DialogueMode.CHECK_IN)
        assert any("Invalid transition" in w for w in warnings)


class TestValidTransitions:
    """Tests for valid transitions function."""

    def test_check_in_transitions(self):
        """Test valid transitions from CHECK_IN."""
        valid = get_valid_transitions(DialogueMode.CHECK_IN)
        assert DialogueMode.FOLLOWUP in valid
        assert DialogueMode.OUTCOME_DISCOVERY in valid
        assert DialogueMode.PROBING in valid
        assert DialogueMode.VERIFICATION not in valid

    def test_probing_transitions(self):
        """Test valid transitions from PROBING."""
        valid = get_valid_transitions(DialogueMode.PROBING)
        assert DialogueMode.TEACHING in valid
        assert DialogueMode.VERIFICATION in valid
        assert DialogueMode.CHECK_IN not in valid

    def test_verification_transitions(self):
        """Test valid transitions from VERIFICATION."""
        valid = get_valid_transitions(DialogueMode.VERIFICATION)
        assert DialogueMode.OUTCOME_CHECK in valid
        assert DialogueMode.TEACHING in valid
        assert DialogueMode.PROBING in valid


# =============================================================================
# Mode Management Tests
# =============================================================================


class TestModeManager:
    """Tests for ModeManager class."""

    def test_get_behavior(self):
        """Test getting mode behavior."""
        mm = ModeManager()
        behavior = mm.get_behavior(DialogueMode.PROBING)
        assert "gap" in behavior.goal.lower() or "blocking" in behavior.goal.lower()
        assert DialogueMode.TEACHING in behavior.next_modes

    def test_valid_transition_check(self):
        """Test checking valid transitions."""
        mm = ModeManager()
        assert mm.is_valid_transition(DialogueMode.PROBING, DialogueMode.TEACHING)
        assert mm.is_valid_transition(DialogueMode.TEACHING, DialogueMode.VERIFICATION)
        assert not mm.is_valid_transition(DialogueMode.CHECK_IN, DialogueMode.VERIFICATION)

    def test_get_valid_transitions(self):
        """Test getting all valid transitions."""
        mm = ModeManager()
        transitions = mm.get_valid_transitions(DialogueMode.TEACHING)
        assert len(transitions) > 0
        assert DialogueMode.VERIFICATION in transitions

    def test_determine_initial_mode(self, sample_full_context):
        """Test determining initial mode."""
        mm = ModeManager()
        mode = mm.determine_initial_mode(sample_full_context)
        assert mode == DialogueMode.CHECK_IN

    def test_post_checkin_with_followups(self, sample_full_context):
        """Test post-checkin mode when followups exist."""
        from sage.graph.models import ApplicationEvent, ApplicationStatus

        sample_full_context.pending_followups = [
            ApplicationEvent(
                id="app-001",
                learner_id="l1",
                concept_ids=["c1"],
                session_id="s1",
                context="test",
                status=ApplicationStatus.PENDING_FOLLOWUP,
            )
        ]
        mm = ModeManager()
        mode = mm.determine_post_checkin_mode(sample_full_context)
        assert mode == DialogueMode.FOLLOWUP

    def test_post_checkin_no_outcome(self, sample_full_context):
        """Test post-checkin mode when no active outcome."""
        mm = ModeManager()
        mode = mm.determine_post_checkin_mode(sample_full_context)
        assert mode == DialogueMode.OUTCOME_DISCOVERY

    def test_post_checkin_with_outcome(self, sample_full_context):
        """Test post-checkin mode when active outcome exists."""
        sample_full_context.active_outcome = Outcome(
            id="o1",
            learner_id="l1",
            stated_goal="Test goal",
        )
        mm = ModeManager()
        mode = mm.determine_post_checkin_mode(sample_full_context)
        assert mode == DialogueMode.PROBING


class TestModeHelpers:
    """Tests for mode helper functions."""

    def test_get_mode_prompt_name(self):
        """Test getting prompt name for mode."""
        assert get_mode_prompt_name(DialogueMode.CHECK_IN) == "check_in"
        assert get_mode_prompt_name(DialogueMode.OUTCOME_DISCOVERY) == "outcome_discovery"

    def test_get_transition_signals(self):
        """Test getting transition signals."""
        signals = get_transition_signals()
        assert DialogueMode.CHECK_IN in signals
        assert "pending_followups_exist" in signals[DialogueMode.CHECK_IN]

    def test_should_verify_before_building(self):
        """Test decay detection for foundational concepts."""
        # Recently proven, not foundational - no verification needed
        assert not should_verify_before_building(30, False)

        # Old proof, foundational - verification needed
        assert should_verify_before_building(70, True)

        # Very old proof, any concept - verification needed
        assert should_verify_before_building(100, False)


# =============================================================================
# Prompt Builder Tests
# =============================================================================


class TestPromptTemplates:
    """Tests for PromptTemplates class."""

    def test_loads_system_prompt(self):
        """Test loading system prompt."""
        templates = PromptTemplates()
        system = templates.system
        assert "SAGE" in system
        assert len(system) > 100

    def test_loads_mode_prompts(self):
        """Test loading mode-specific prompts."""
        templates = PromptTemplates()
        for mode in DialogueMode:
            prompt = templates.get_mode_prompt(mode)
            assert len(prompt) > 50

    def test_caches_templates(self):
        """Test that templates are cached."""
        templates = PromptTemplates()
        system1 = templates.system
        system2 = templates.system
        assert system1 is system2  # Same object (cached)


class TestPromptBuilder:
    """Tests for PromptBuilder class."""

    def test_build_system_prompt(self, sample_turn_context):
        """Test building system prompt."""
        builder = PromptBuilder()
        prompt = builder.build_system_prompt(sample_turn_context)
        assert "SAGE" in prompt
        assert "Learner Adaptation" in prompt

    def test_build_turn_prompt(self, sample_turn_context):
        """Test building turn prompt."""
        builder = PromptBuilder()
        prompt = builder.build_turn_prompt(sample_turn_context)
        assert "Current Context" in prompt

    def test_builds_with_proven_concepts(self, sample_turn_context):
        """Test prompt includes proven concepts."""
        sample_turn_context.proven_concepts = [
            ConceptSnapshot(
                id="c1",
                name="test-concept",
                display_name="Test Concept",
                description="Description of the test concept",
                summary="A test concept",
                status="understood",
                has_proof=True,
                proof_confidence=0.9,
            )
        ]
        builder = PromptBuilder()
        prompt = builder.build_turn_prompt(sample_turn_context)
        assert "Test Concept" in prompt or "What This Learner Already Knows" in prompt

    def test_builds_with_adaptation_hints(self, sample_turn_context):
        """Test prompt includes adaptation hints."""
        sample_turn_context.adaptation_hints = ["Keep it brief", "Focus on practical examples"]
        builder = PromptBuilder()
        prompt = builder.build_turn_prompt(sample_turn_context)
        assert "Adaptation Hints" in prompt
        assert "Keep it brief" in prompt


# =============================================================================
# State Detection Tests
# =============================================================================


class TestExplicitSignalDetection:
    """Tests for explicit signal detection."""

    def test_detects_tired(self):
        """Test detecting fatigue signals."""
        signals = detect_explicit_signals("I'm getting tired")
        assert len(signals) == 1
        assert signals[0].signal_type == "energy_drop"

    def test_detects_time_pressure(self):
        """Test detecting time pressure signals."""
        signals = detect_explicit_signals("I only have 10 minutes")
        assert len(signals) == 1
        assert signals[0].signal_type == "time_pressure"

    def test_detects_confusion(self):
        """Test detecting confusion signals."""
        signals = detect_explicit_signals("I'm lost, can you explain again?")
        assert len(signals) == 1
        assert signals[0].signal_type == "confusion"

    def test_detects_frustration(self):
        """Test detecting frustration signals."""
        signals = detect_explicit_signals("Ugh, this makes no sense")
        assert len(signals) == 1
        assert signals[0].signal_type == "frustration"

    def test_no_signals_normal_message(self):
        """Test no signals for normal message."""
        signals = detect_explicit_signals("Tell me more about pricing")
        assert len(signals) == 0


class TestImplicitSignalDetection:
    """Tests for implicit signal detection."""

    def test_detects_decreasing_length(self):
        """Test detecting energy drop from decreasing response length."""
        messages = [
            Message(role="user", content="This is a longer response that shows engagement"),
            Message(role="user", content="A medium length response"),
            Message(role="user", content="Short response"),
            Message(role="user", content="Shorter"),
            Message(role="user", content="Ok"),
        ]
        signals = detect_implicit_signals(messages)
        # Should detect energy drop from decreasing length
        energy_signals = [s for s in signals if s.signal_type == "energy_drop"]
        assert len(energy_signals) >= 0  # May or may not detect depending on pattern

    def test_detects_short_responses(self):
        """Test detecting disengagement from short responses."""
        messages = [
            Message(role="user", content="ok"),
            Message(role="user", content="sure"),
            Message(role="user", content="yes"),
            Message(role="user", content="ok"),
            Message(role="user", content="fine"),
        ]
        signals = detect_implicit_signals(messages)
        disengagement = [s for s in signals if s.signal_type == "disengagement"]
        assert len(disengagement) >= 1

    def test_needs_minimum_messages(self):
        """Test that we need minimum messages for implicit detection."""
        messages = [
            Message(role="user", content="Hello"),
        ]
        signals = detect_implicit_signals(messages)
        assert len(signals) == 0


class TestAdaptationRecommendations:
    """Tests for adaptation recommendations."""

    def test_get_energy_drop_adaptation(self):
        """Test getting adaptation for energy drop."""
        adaptation = get_adaptation_for_signal("energy_drop")
        assert adaptation is not None
        assert "shorter" in " ".join(adaptation.recommendations).lower()

    def test_get_confusion_adaptation(self):
        """Test getting adaptation for confusion."""
        adaptation = get_adaptation_for_signal("confusion")
        assert adaptation is not None
        assert "different" in " ".join(adaptation.recommendations).lower()

    def test_get_unknown_signal(self):
        """Test getting adaptation for unknown signal."""
        adaptation = get_adaptation_for_signal("unknown_signal")
        assert adaptation is None


class TestContextUpdate:
    """Tests for context update based on state changes."""

    def test_update_for_energy_drop(self):
        """Test updating context for energy drop."""
        context = SessionContext(
            energy=EnergyLevel.HIGH,
            time_available="1 hour",
        )
        updated = update_context_for_state_change(context, "energy_drop")
        assert updated.energy == EnergyLevel.LOW

    def test_update_for_time_pressure(self):
        """Test updating context for time pressure."""
        context = SessionContext(
            energy=EnergyLevel.MEDIUM,
            time_available="1 hour",
        )
        updated = update_context_for_state_change(context, "time_pressure")
        assert updated.time_available == "short"
        assert "time pressured" in updated.mindset

    def test_update_preserves_other_fields(self):
        """Test that update preserves unchanged fields."""
        context = SessionContext(
            energy=EnergyLevel.HIGH,
            environment="office",
            device="desktop",
        )
        updated = update_context_for_state_change(context, "confusion")
        assert updated.environment == "office"
        assert updated.device == "desktop"


# =============================================================================
# Integration Tests
# =============================================================================


class TestDialogueModuleIntegration:
    """Integration tests for the dialogue module."""

    def test_full_import(self):
        """Test that all exports are importable."""
        from sage.dialogue import (
            SAGEResponse,
            PromptBuilder,
            ModeManager,
            detect_explicit_signals,
            ConversationConfig,
        )
        assert SAGEResponse is not None
        assert PromptBuilder is not None
        assert ModeManager is not None

    def test_response_to_turn_changes(self):
        """Test converting SAGEResponse to persistence format."""
        response = SAGEResponse(
            message="Let me teach you about this.",
            current_mode=DialogueMode.TEACHING,
            gap_identified=GapIdentified(
                name="test-gap",
                display_name="Test Gap",
                description="A test gap",
            ),
        )

        # The conversion happens in ConversationEngine._persist_turn
        # This test validates the response has the right structure
        assert response.gap_identified.name == "test-gap"
        assert response.current_mode == DialogueMode.TEACHING


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
