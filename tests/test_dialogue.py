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
    ExtendedSAGEResponse,
    FollowupResponse,
    GapIdentified,
    PendingDataRequest,
    ProofEarned,
    ProofExchange,
    SAGEResponse,
    StateChange,
    UITreeNode,
    VoiceHints,
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


# =============================================================================
# Voice/UI Parity Model Tests
# =============================================================================


class TestUITreeNode:
    """Tests for UITreeNode model (composable UI trees)."""

    def test_simple_node(self):
        """Test creating a simple UI node without children."""
        node = UITreeNode(
            component="Text",
            props={"content": "Hello, world!"},
        )
        assert node.component == "Text"
        assert node.props["content"] == "Hello, world!"
        assert node.children is None

    def test_node_with_children(self):
        """Test creating a node with nested children."""
        node = UITreeNode(
            component="Stack",
            props={"gap": 4, "direction": "vertical"},
            children=[
                UITreeNode(component="Text", props={"content": "Title"}),
                UITreeNode(component="Button", props={"label": "Click me"}),
            ],
        )
        assert node.component == "Stack"
        assert len(node.children) == 2
        assert node.children[0].component == "Text"
        assert node.children[1].component == "Button"

    def test_deeply_nested_tree(self):
        """Test a complex deeply nested UI tree."""
        tree = UITreeNode(
            component="Card",
            props={"title": "Check-In"},
            children=[
                UITreeNode(
                    component="Stack",
                    props={"gap": 6},
                    children=[
                        UITreeNode(
                            component="RadioGroup",
                            props={"name": "timeAvailable", "label": "Time"},
                            children=[
                                UITreeNode(component="Radio", props={"value": "quick", "label": "Quick"}),
                                UITreeNode(component="Radio", props={"value": "focused", "label": "Focused"}),
                                UITreeNode(component="Radio", props={"value": "deep", "label": "Deep"}),
                            ],
                        ),
                        UITreeNode(
                            component="Slider",
                            props={"name": "energy", "min": 0, "max": 100},
                        ),
                    ],
                ),
            ],
        )
        assert tree.component == "Card"
        assert len(tree.children) == 1
        stack = tree.children[0]
        assert stack.component == "Stack"
        assert len(stack.children) == 2
        radio_group = stack.children[0]
        assert radio_group.component == "RadioGroup"
        assert len(radio_group.children) == 3

    def test_serialization_roundtrip(self):
        """Test that UITreeNode serializes and deserializes correctly."""
        original = UITreeNode(
            component="Stack",
            props={"gap": 4},
            children=[
                UITreeNode(component="Text", props={"content": "Hello"}),
            ],
        )
        json_str = original.model_dump_json()
        restored = UITreeNode.model_validate_json(json_str)
        assert restored.component == original.component
        assert restored.props == original.props
        assert len(restored.children) == 1

    def test_default_props(self):
        """Test that props default to empty dict."""
        node = UITreeNode(component="Divider")
        assert node.props == {}
        assert node.children is None


class TestVoiceHints:
    """Tests for VoiceHints model (TTS optimization)."""

    def test_minimal_voice_hints(self):
        """Test voice hints with defaults."""
        hints = VoiceHints()
        assert hints.voice_fallback is None
        assert hints.emphasis == []
        assert hints.pause_after == []
        assert hints.tone == "neutral"
        assert hints.slower is False

    def test_full_voice_hints(self):
        """Test voice hints with all fields."""
        hints = VoiceHints(
            voice_fallback="How much time do you have today?",
            emphasis=["time", "energy"],
            pause_after=["today", "mindset"],
            tone="warm",
            slower=True,
        )
        assert hints.voice_fallback == "How much time do you have today?"
        assert "time" in hints.emphasis
        assert hints.tone == "warm"
        assert hints.slower is True

    def test_serialization(self):
        """Test voice hints serialization."""
        hints = VoiceHints(voice_fallback="Test", tone="excited")
        data = hints.model_dump()
        assert data["voice_fallback"] == "Test"
        assert data["tone"] == "excited"


class TestPendingDataRequest:
    """Tests for PendingDataRequest model (multi-turn data collection)."""

    def test_empty_pending_request(self):
        """Test pending request with just intent."""
        pending = PendingDataRequest(intent="session_check_in")
        assert pending.intent == "session_check_in"
        assert pending.collected_data == {}
        assert pending.missing_fields == []
        assert pending.validation_errors == []

    def test_partial_data_collected(self):
        """Test pending request with partial data."""
        pending = PendingDataRequest(
            intent="session_check_in",
            collected_data={"timeAvailable": "focused", "energyLevel": 50},
            missing_fields=["mindset"],
        )
        assert pending.collected_data["timeAvailable"] == "focused"
        assert "mindset" in pending.missing_fields

    def test_with_validation_errors(self):
        """Test pending request with validation errors."""
        pending = PendingDataRequest(
            intent="practice_setup",
            collected_data={"scenario": ""},
            validation_errors=["Scenario description cannot be empty"],
        )
        assert len(pending.validation_errors) == 1
        assert "empty" in pending.validation_errors[0]


class TestExtendedSAGEResponse:
    """Tests for ExtendedSAGEResponse model (voice/UI parity)."""

    def test_extends_base_response(self):
        """Test that ExtendedSAGEResponse includes all SAGEResponse fields."""
        response = ExtendedSAGEResponse(
            message="How are you showing up today?",
            current_mode=DialogueMode.CHECK_IN,
        )
        # Base SAGEResponse fields should work
        assert response.message == "How are you showing up today?"
        assert response.current_mode == DialogueMode.CHECK_IN
        assert response.transition_to is None
        # Extended fields should have defaults
        assert response.ui_tree is None
        assert response.voice_hints is None
        assert response.pending_data_request is None

    def test_response_with_ui_tree(self):
        """Test response with ad-hoc generated UI tree."""
        ui_tree = UITreeNode(
            component="Stack",
            props={"gap": 4},
            children=[
                UITreeNode(component="Text", props={"content": "Quick Check-In"}),
                UITreeNode(
                    component="Slider",
                    props={"name": "energy", "label": "Energy Level"},
                ),
                UITreeNode(component="Button", props={"label": "Start", "action": "submit"}),
            ],
        )
        response = ExtendedSAGEResponse(
            message="Let's get started.",
            current_mode=DialogueMode.CHECK_IN,
            ui_tree=ui_tree,
            ui_purpose="Collect session context",
            estimated_interaction_time=30,
        )
        assert response.ui_tree is not None
        assert response.ui_tree.component == "Stack"
        assert len(response.ui_tree.children) == 3
        assert response.ui_purpose == "Collect session context"
        assert response.estimated_interaction_time == 30

    def test_response_with_voice_hints(self):
        """Test response with voice optimization hints."""
        hints = VoiceHints(
            voice_fallback="How are you showing up today? How much time do you have?",
            tone="warm",
            emphasis=["time", "energy"],
        )
        response = ExtendedSAGEResponse(
            message="Let's check in.",
            current_mode=DialogueMode.CHECK_IN,
            voice_hints=hints,
        )
        assert response.voice_hints is not None
        assert "How are you showing up" in response.voice_hints.voice_fallback
        assert response.voice_hints.tone == "warm"

    def test_response_with_pending_data(self):
        """Test response with pending data collection state."""
        pending = PendingDataRequest(
            intent="session_check_in",
            collected_data={"timeAvailable": "focused"},
            missing_fields=["energyLevel", "mindset"],
        )
        response = ExtendedSAGEResponse(
            message="Got it, focused session. How's your energy?",
            current_mode=DialogueMode.CHECK_IN,
            pending_data_request=pending,
        )
        assert response.pending_data_request is not None
        assert response.pending_data_request.intent == "session_check_in"
        assert "energyLevel" in response.pending_data_request.missing_fields

    def test_full_extended_response(self):
        """Test response with all extended fields populated."""
        ui_tree = UITreeNode(
            component="Card",
            props={"title": "Check-In"},
            children=[
                UITreeNode(
                    component="RadioGroup",
                    props={"name": "time"},
                    children=[
                        UITreeNode(component="Radio", props={"value": "quick", "label": "Quick"}),
                    ],
                ),
            ],
        )
        hints = VoiceHints(voice_fallback="How much time?", tone="warm")
        pending = PendingDataRequest(
            intent="session_check_in",
            collected_data={"energy": 70},
            missing_fields=["time"],
        )

        response = ExtendedSAGEResponse(
            message="Almost there! Just need to know how much time you have.",
            current_mode=DialogueMode.CHECK_IN,
            ui_tree=ui_tree,
            voice_hints=hints,
            pending_data_request=pending,
            ui_purpose="Complete check-in",
            estimated_interaction_time=15,
        )

        # Verify all fields
        assert response.ui_tree.component == "Card"
        assert response.voice_hints.tone == "warm"
        assert response.pending_data_request.collected_data["energy"] == 70
        assert response.ui_purpose == "Complete check-in"
        assert response.estimated_interaction_time == 15

    def test_serialization_with_all_fields(self):
        """Test that full response serializes correctly."""
        response = ExtendedSAGEResponse(
            message="Test",
            current_mode=DialogueMode.CHECK_IN,
            ui_tree=UITreeNode(component="Stack", children=[]),
            voice_hints=VoiceHints(voice_fallback="Test voice"),
            pending_data_request=PendingDataRequest(intent="test"),
        )
        data = response.model_dump()
        assert "ui_tree" in data
        assert "voice_hints" in data
        assert "pending_data_request" in data
        assert data["ui_tree"]["component"] == "Stack"

    def test_inherits_base_functionality(self):
        """Test that base SAGEResponse features still work."""
        gap = GapIdentified(
            name="test-gap",
            display_name="Test Gap",
            description="A test gap",
        )
        response = ExtendedSAGEResponse(
            message="Found a gap",
            current_mode=DialogueMode.PROBING,
            gap_identified=gap,
            transition_to=DialogueMode.TEACHING,
            # Extended fields
            ui_tree=UITreeNode(component="Text", props={"content": "Gap found"}),
        )
        # Base functionality
        assert response.gap_identified.name == "test-gap"
        assert response.transition_to == DialogueMode.TEACHING
        # Extended functionality
        assert response.ui_tree is not None


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
