"""Tests for the SAGE Orchestrator."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from sage.dialogue.structured_output import PendingDataRequest, SAGEResponse
from sage.graph.models import DialogueMode
from sage.orchestration.normalizer import InputModality, NormalizedInput
from sage.orchestration.orchestrator import (
    OrchestratorDecision,
    OutputStrategy,
    SAGEOrchestrator,
    _OUTPUT_STRATEGY_MAP,
)


def make_request_more_decision(
    intent: str,
    missing_fields: list[str],
) -> OrchestratorDecision:
    """Create a request_more decision for testing."""
    return OrchestratorDecision(
        action="request_more",
        output_strategy=OutputStrategy.TEXT_ONLY,
        pending_data_request=PendingDataRequest(
            intent=intent,
            missing_fields=missing_fields,
        ),
    )


def make_normalized_input(
    intent: str,
    missing_fields: list[str],
    modality: InputModality = InputModality.CHAT,
    validation_errors: list[str] | None = None,
) -> NormalizedInput:
    """Create a normalized input for testing."""
    return NormalizedInput(
        intent=intent,
        missing_fields=missing_fields,
        validation_errors=validation_errors or [],
        source_modality=modality,
    )


def make_mock_extraction_response(content: str) -> MagicMock:
    """Create a mock LLM extraction response."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=content))
    ]
    return mock_response


@pytest.fixture
def mock_graph():
    """Create mock LearningGraph."""
    return MagicMock()


@pytest.fixture
def mock_llm_client():
    """Create mock OpenAI client."""
    return MagicMock()


@pytest.fixture
def orchestrator(mock_graph, mock_llm_client):
    """Create orchestrator with mocks."""
    return SAGEOrchestrator(mock_graph, mock_llm_client)


class TestOutputStrategy:
    """Test OutputStrategy enum."""

    def test_enum_values(self):
        """Test all strategy values exist."""
        assert OutputStrategy.TEXT_ONLY.value == "text_only"
        assert OutputStrategy.UI_TREE.value == "ui_tree"
        assert OutputStrategy.VOICE_DESCRIPTION.value == "voice_description"
        assert OutputStrategy.HYBRID.value == "hybrid"


class TestOrchestratorDecision:
    """Test OrchestratorDecision dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        decision = OrchestratorDecision(
            action="process",
            output_strategy=OutputStrategy.TEXT_ONLY,
        )
        assert decision.action == "process"
        assert decision.output_strategy == OutputStrategy.TEXT_ONLY
        assert decision.context_for_llm == {}
        assert decision.pending_data_request is None

    def test_custom_values(self):
        """Test custom values are preserved."""
        pending = PendingDataRequest(
            intent="session_check_in",
            collected_data={"energyLevel": 75},
            missing_fields=["timeAvailable"],
        )
        decision = OrchestratorDecision(
            action="request_more",
            output_strategy=OutputStrategy.UI_TREE,
            context_for_llm={"intent": "test"},
            pending_data_request=pending,
        )
        assert decision.action == "request_more"
        assert decision.output_strategy == OutputStrategy.UI_TREE
        assert decision.context_for_llm == {"intent": "test"}
        assert decision.pending_data_request == pending


class TestOutputStrategyMapping:
    """Test output strategy determination."""

    def test_session_check_in_form_uses_ui_tree(self):
        """Test form check-in uses UI tree."""
        key = ("session_check_in", InputModality.FORM)
        assert _OUTPUT_STRATEGY_MAP[key] == OutputStrategy.UI_TREE

    def test_session_check_in_voice_uses_voice_description(self):
        """Test voice check-in uses voice description."""
        key = ("session_check_in", InputModality.VOICE)
        assert _OUTPUT_STRATEGY_MAP[key] == OutputStrategy.VOICE_DESCRIPTION

    def test_practice_setup_voice_uses_hybrid(self):
        """Test voice practice setup uses hybrid."""
        key = ("practice_setup", InputModality.VOICE)
        assert _OUTPUT_STRATEGY_MAP[key] == OutputStrategy.HYBRID

    def test_verification_uses_text_only(self):
        """Test verification always uses text."""
        assert _OUTPUT_STRATEGY_MAP[("verification", InputModality.FORM)] == OutputStrategy.TEXT_ONLY
        assert _OUTPUT_STRATEGY_MAP[("verification", InputModality.VOICE)] == OutputStrategy.TEXT_ONLY


class TestSAGEOrchestratorInit:
    """Test SAGEOrchestrator initialization."""

    def test_init_creates_components(self, mock_graph, mock_llm_client):
        """Test initialization creates required components."""
        orchestrator = SAGEOrchestrator(mock_graph, mock_llm_client)
        assert orchestrator.graph == mock_graph
        assert orchestrator.llm_client == mock_llm_client
        assert orchestrator.normalizer is not None
        assert orchestrator.intent_extractor is not None
        assert orchestrator.conversation_engine is not None

    def test_init_accepts_custom_model(self, mock_graph, mock_llm_client):
        """Test custom extraction model can be specified."""
        orchestrator = SAGEOrchestrator(
            mock_graph,
            mock_llm_client,
            extraction_model="custom-model",
        )
        assert orchestrator.intent_extractor.model == "custom-model"


class TestNormalizeInput:
    """Test _normalize_input method."""

    def test_normalize_form_input(self, orchestrator):
        """Test form input normalization."""
        result = orchestrator._normalize_input(
            "",
            InputModality.FORM,
            form_id="check-in-123",
            form_data={"energyLevel": 80},
        )
        assert result.intent == "session_check_in"
        assert result.source_modality == InputModality.FORM

    def test_normalize_voice_input(self, orchestrator):
        """Test voice input normalization."""
        result = orchestrator._normalize_input(
            "I have 30 minutes",
            InputModality.VOICE,
            form_id=None,
            form_data=None,
        )
        assert result.intent == "pending_extraction"
        assert result.source_modality == InputModality.VOICE
        assert result.raw_input == "I have 30 minutes"

    def test_normalize_chat_input(self, orchestrator):
        """Test chat input normalization."""
        result = orchestrator._normalize_input(
            "Hello",
            InputModality.CHAT,
            form_id=None,
            form_data=None,
        )
        assert result.intent == "pending_extraction"
        assert result.source_modality == InputModality.CHAT

    def test_normalize_hybrid_input(self, orchestrator):
        """Test hybrid input normalization."""
        result = orchestrator._normalize_input(
            "I'm tired",
            InputModality.HYBRID,
            form_id=None,
            form_data={"timeAvailable": "focused"},
        )
        assert result.intent == "pending_extraction"
        assert result.source_modality == InputModality.HYBRID
        assert result.data["timeAvailable"] == "focused"


class TestMakeDecision:
    """Test _make_decision method."""

    def test_complete_data_returns_process(self, orchestrator):
        """Test complete data triggers process action."""
        normalized = NormalizedInput(
            intent="session_check_in",
            data={"energyLevel": 80},
            data_complete=True,
            source_modality=InputModality.FORM,
        )
        decision = orchestrator._make_decision(normalized, "session-1")
        assert decision.action == "process"
        assert decision.pending_data_request is None

    def test_incomplete_data_returns_request_more(self, orchestrator):
        """Test incomplete data triggers request_more action."""
        normalized = NormalizedInput(
            intent="practice_setup",
            data={"difficulty": "hard"},
            data_complete=False,
            missing_fields=["scenario_type"],
            source_modality=InputModality.FORM,
        )
        decision = orchestrator._make_decision(normalized, "session-1")
        assert decision.action == "request_more"
        assert decision.pending_data_request is not None
        assert "scenario_type" in decision.pending_data_request.missing_fields

    def test_pending_request_stored(self, orchestrator):
        """Test pending request is stored in session state."""
        normalized = NormalizedInput(
            intent="practice_setup",
            data={},
            data_complete=False,
            missing_fields=["scenario_type"],
            source_modality=InputModality.CHAT,
        )
        orchestrator._make_decision(normalized, "session-123")
        pending = orchestrator.get_pending_request("session-123")
        assert pending is not None
        assert pending.intent == "practice_setup"

    def test_pending_request_cleared_on_complete(self, orchestrator):
        """Test pending request is cleared when data is complete."""
        # First, create a pending request
        normalized_incomplete = NormalizedInput(
            intent="practice_setup",
            data={},
            data_complete=False,
            missing_fields=["scenario_type"],
            source_modality=InputModality.CHAT,
        )
        orchestrator._make_decision(normalized_incomplete, "session-456")
        assert orchestrator.get_pending_request("session-456") is not None

        # Then complete the data
        normalized_complete = NormalizedInput(
            intent="practice_setup",
            data={"scenario_type": "pricing_call"},
            data_complete=True,
            source_modality=InputModality.CHAT,
        )
        orchestrator._make_decision(normalized_complete, "session-456")
        assert orchestrator.get_pending_request("session-456") is None


class TestDetermineOutputStrategy:
    """Test _determine_output_strategy method."""

    def test_known_intent_returns_mapped_strategy(self, orchestrator):
        """Test known intent/modality returns correct strategy."""
        strategy = orchestrator._determine_output_strategy(
            "session_check_in",
            InputModality.FORM,
        )
        assert strategy == OutputStrategy.UI_TREE

    def test_unknown_intent_returns_default(self, orchestrator):
        """Test unknown intent returns text_only default."""
        strategy = orchestrator._determine_output_strategy(
            "unknown_intent",
            InputModality.CHAT,
        )
        assert strategy == OutputStrategy.TEXT_ONLY


@pytest.mark.asyncio
class TestCreateDataRequestResponse:
    """Test _create_data_request_response method."""

    async def test_form_uses_template_message(self, orchestrator):
        """Test form modality uses template-based messages."""
        decision = make_request_more_decision("practice_setup", ["scenario_type"])
        normalized = make_normalized_input(
            "practice_setup",
            ["scenario_type"],
            modality=InputModality.FORM,
        )

        response = await orchestrator._create_data_request_response(decision, normalized)

        assert "scenario_type" in response.message
        assert response.pending_data_request is not None

    async def test_form_multiple_missing_fields(self, orchestrator):
        """Test form message for multiple missing fields."""
        fields = ["scenario_type", "difficulty"]
        decision = make_request_more_decision("practice_setup", fields)
        normalized = make_normalized_input("practice_setup", fields, modality=InputModality.FORM)

        response = await orchestrator._create_data_request_response(decision, normalized)

        assert "scenario_type" in response.message
        assert "difficulty" in response.message

    async def test_form_validation_errors_included(self, orchestrator):
        """Test validation errors are included in form message."""
        decision = make_request_more_decision("session_check_in", [])
        normalized = make_normalized_input(
            "session_check_in",
            [],
            modality=InputModality.FORM,
            validation_errors=["Invalid energy level"],
        )

        response = await orchestrator._create_data_request_response(decision, normalized)

        assert "Invalid energy level" in response.message

    async def test_voice_uses_llm_probe(self, orchestrator, mock_llm_client):
        """Test voice modality generates conversational probe via LLM."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Got it, 30 minutes. How are you feeling energy-wise?"))
        ]
        mock_llm_client.chat.completions.create.return_value = mock_response

        decision = make_request_more_decision("session_check_in", ["energyLevel"])
        normalized = make_normalized_input(
            "session_check_in",
            ["energyLevel"],
            modality=InputModality.VOICE,
        )
        normalized.data = {"timeAvailable": "focused"}

        response = await orchestrator._create_data_request_response(decision, normalized)

        assert "energy" in response.message.lower()
        assert mock_llm_client.chat.completions.create.called

    async def test_chat_uses_llm_probe(self, orchestrator, mock_llm_client):
        """Test chat modality generates conversational probe via LLM."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="What kind of scenario would you like to practice?"))
        ]
        mock_llm_client.chat.completions.create.return_value = mock_response

        decision = make_request_more_decision("practice_setup", ["scenario_type"])
        normalized = make_normalized_input(
            "practice_setup",
            ["scenario_type"],
            modality=InputModality.CHAT,
        )

        response = await orchestrator._create_data_request_response(decision, normalized)

        assert response.message == "What kind of scenario would you like to practice?"
        assert mock_llm_client.chat.completions.create.called

    async def test_llm_error_falls_back_to_template(self, orchestrator, mock_llm_client):
        """Test LLM failure falls back to template message."""
        mock_llm_client.chat.completions.create.side_effect = Exception("API error")

        decision = make_request_more_decision("session_check_in", ["energyLevel"])
        normalized = make_normalized_input(
            "session_check_in",
            ["energyLevel"],
            modality=InputModality.VOICE,
        )

        response = await orchestrator._create_data_request_response(decision, normalized)

        assert "energyLevel" in response.message
        assert response.pending_data_request is not None


class TestPendingRequestManagement:
    """Test pending request getter and clearer."""

    def test_get_nonexistent_returns_none(self, orchestrator):
        """Test getting nonexistent pending request returns None."""
        assert orchestrator.get_pending_request("no-such-session") is None

    def test_clear_nonexistent_no_error(self, orchestrator):
        """Test clearing nonexistent pending request doesn't error."""
        orchestrator.clear_pending_request("no-such-session")  # Should not raise

    def test_clear_existing_request(self, orchestrator):
        """Test clearing existing pending request."""
        # Create a pending request
        orchestrator._pending_requests["test-session"] = PendingDataRequest(
            intent="test",
        )
        assert orchestrator.get_pending_request("test-session") is not None

        orchestrator.clear_pending_request("test-session")
        assert orchestrator.get_pending_request("test-session") is None


@pytest.mark.asyncio
class TestProcessInput:
    """Test process_input async method."""

    async def test_form_input_complete(self, orchestrator):
        """Test processing complete form input."""
        # Mock the conversation engine to return a response
        mock_response = SAGEResponse(
            message="Welcome to your session!",
            current_mode=DialogueMode.CHECK_IN,
        )
        orchestrator.conversation_engine.resume_session = MagicMock()
        orchestrator.conversation_engine.process_turn_streaming = AsyncMock(
            return_value=mock_response
        )

        response = await orchestrator.process_input(
            raw_input="",
            source_modality=InputModality.FORM,
            session_id="test-session",
            form_id="check-in-123",
            form_data={"energyLevel": 80, "timeAvailable": "focused"},
        )

        assert response.message == "Welcome to your session!"
        assert response.pending_data_request is None

    async def test_form_input_incomplete(self, orchestrator):
        """Test processing incomplete form input."""
        response = await orchestrator.process_input(
            raw_input="",
            source_modality=InputModality.FORM,
            session_id="test-session",
            form_id="practice-setup",
            form_data={"difficulty": "hard"},  # Missing scenario_type
        )

        assert response.pending_data_request is not None
        assert "scenario_type" in response.pending_data_request.missing_fields

    async def test_voice_input_triggers_extraction(self, orchestrator, mock_llm_client):
        """Test voice input triggers intent extraction."""
        mock_llm_client.chat.completions.create.return_value = make_mock_extraction_response(
            '{"intent": "session_check_in", "data": {"timeAvailable": "focused"}, "confidence": 0.9}'
        )
        orchestrator.conversation_engine.resume_session = MagicMock()
        orchestrator.conversation_engine.process_turn_streaming = AsyncMock(
            return_value=SAGEResponse(
                message="Got it, 30 minutes.",
                current_mode=DialogueMode.CHECK_IN,
            )
        )

        response = await orchestrator.process_input(
            raw_input="I have 30 minutes",
            source_modality=InputModality.VOICE,
            session_id="test-session",
        )

        assert response.message == "Got it, 30 minutes."

    async def test_pending_context_passed_to_extractor(self, orchestrator, mock_llm_client):
        """Test pending context is passed to intent extractor."""
        orchestrator._pending_requests["test-session"] = PendingDataRequest(
            intent="session_check_in",
            collected_data={"timeAvailable": "focused"},
        )
        mock_llm_client.chat.completions.create.return_value = make_mock_extraction_response(
            '{"intent": "session_check_in", "data": {"energyLevel": 80}, "confidence": 0.9}'
        )
        orchestrator.conversation_engine.resume_session = MagicMock()
        orchestrator.conversation_engine.process_turn_streaming = AsyncMock(
            return_value=SAGEResponse(
                message="Great!",
                current_mode=DialogueMode.CHECK_IN,
            )
        )

        await orchestrator.process_input(
            raw_input="I'm feeling good",
            source_modality=InputModality.VOICE,
            session_id="test-session",
        )

        assert mock_llm_client.chat.completions.create.called


class TestBuildProbePrompt:
    """Test _build_probe_prompt function."""

    def test_includes_intent_context(self):
        """Test prompt includes intent-appropriate context."""
        from sage.orchestration.orchestrator import _build_probe_prompt

        prompt = _build_probe_prompt(
            intent="session_check_in",
            collected_data={"timeAvailable": "focused"},
            missing_fields=["energyLevel"],
        )

        assert "energy" in prompt.lower() or "energyLevel" in prompt
        assert "session_check_in" in prompt or "showing up today" in prompt
        assert "timeAvailable=focused" in prompt

    def test_handles_empty_collected_data(self):
        """Test prompt handles no collected data."""
        from sage.orchestration.orchestrator import _build_probe_prompt

        prompt = _build_probe_prompt(
            intent="practice_setup",
            collected_data={},
            missing_fields=["scenario_type"],
        )

        assert "nothing yet" in prompt
        assert "scenario_type" in prompt

    def test_multiple_missing_fields(self):
        """Test prompt lists all missing fields."""
        from sage.orchestration.orchestrator import _build_probe_prompt

        prompt = _build_probe_prompt(
            intent="session_check_in",
            collected_data={},
            missing_fields=["timeAvailable", "energyLevel", "mindset"],
        )

        assert "timeAvailable" in prompt
        assert "energyLevel" in prompt
        assert "mindset" in prompt


@pytest.mark.asyncio
class TestMultiTurnVoiceFlow:
    """Integration tests for multi-turn voice data collection."""

    async def test_voice_multi_turn_collection(self, orchestrator, mock_llm_client):
        """Test complete multi-turn voice collection flow.

        Turn 1: User mentions practice but missing scenario type (required)
        Turn 2: User provides scenario type, data complete
        """
        # Mock LLM to:
        # 1. First call: Intent extraction returns incomplete data (missing scenario_type)
        # 2. Second call: Probe generation returns conversational question
        def mock_create(**kwargs):
            messages = kwargs.get("messages", [])
            if any("Generate a brief follow-up" in str(m) for m in messages):
                mock_resp = MagicMock()
                mock_resp.choices = [
                    MagicMock(message=MagicMock(content="Got it, hard mode. What kind of scenario—pricing, negotiation, or something else?"))
                ]
                return mock_resp
            # Intent extraction returns incomplete data (difficulty but no scenario_type)
            mock_resp = MagicMock()
            mock_resp.choices = [
                MagicMock(message=MagicMock(
                    content='{"intent": "practice_setup", "data": {"difficulty": "hard"}, "confidence": 0.9}'
                ))
            ]
            return mock_resp

        mock_llm_client.chat.completions.create.side_effect = mock_create

        response1 = await orchestrator.process_input(
            raw_input="I want to practice something hard",
            source_modality=InputModality.VOICE,
            session_id="multi-turn-session",
        )

        # Should request more data (scenario_type is required for practice_setup)
        assert response1.pending_data_request is not None
        assert "scenario" in response1.message.lower()

        # Verify pending request stored
        pending = orchestrator.get_pending_request("multi-turn-session")
        assert pending is not None
        assert pending.intent == "practice_setup"
        assert pending.collected_data.get("difficulty") == "hard"
        assert "scenario_type" in pending.missing_fields

    async def test_pending_cleared_after_complete(self, orchestrator, mock_llm_client):
        """Test pending request is cleared when data becomes complete."""
        # Set up pending request
        orchestrator._pending_requests["complete-session"] = PendingDataRequest(
            intent="session_check_in",
            collected_data={"timeAvailable": "focused"},
            missing_fields=["energyLevel"],
        )

        # Mock extraction to return complete data (merges with pending)
        mock_llm_client.chat.completions.create.return_value = make_mock_extraction_response(
            '{"intent": "session_check_in", "data": {"energyLevel": 80}, "confidence": 0.9}'
        )
        orchestrator.conversation_engine.resume_session = MagicMock()
        orchestrator.conversation_engine.process_turn_streaming = AsyncMock(
            return_value=SAGEResponse(
                message="Great, let's get started!",
                current_mode=DialogueMode.CHECK_IN,
            )
        )

        response = await orchestrator.process_input(
            raw_input="feeling energized",
            source_modality=InputModality.VOICE,
            session_id="complete-session",
        )

        # Data complete - should process, not request more
        assert response.pending_data_request is None
        assert response.message == "Great, let's get started!"

        # Pending should be cleared
        assert orchestrator.get_pending_request("complete-session") is None


@pytest.mark.asyncio
class TestUIGenerationIntegration:
    """Integration tests for UI generation in orchestrator."""

    async def test_ui_tree_generated_for_form_modality(self, orchestrator, mock_llm_client):
        """Test UI tree is generated for form modality with UI_TREE strategy."""
        import json
        # Mock conversation engine response
        mock_response = SAGEResponse(
            message="Let's check in.",
            current_mode=DialogueMode.CHECK_IN,
        )
        orchestrator.conversation_engine.resume_session = MagicMock()
        orchestrator.conversation_engine.process_turn_streaming = AsyncMock(
            return_value=mock_response
        )

        # Mock UI agent response
        ui_response = json.dumps({
            "tree": {"component": "Card", "props": {"title": "Check-in"}},
            "voice_fallback": "How are you showing up today?",
            "purpose": "Session check-in",
            "estimated_interaction_time": 30,
        })
        mock_llm_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=ui_response))]
        )

        response = await orchestrator.process_input(
            raw_input="",
            source_modality=InputModality.FORM,
            session_id="ui-test-session",
            form_id="session-check-in",
            form_data={"timeAvailable": "focused", "energyLevel": 80},
        )

        # UI tree should be present for form modality
        assert response.ui_tree is not None
        assert response.ui_tree.component == "Card"
        assert response.voice_hints is not None
        assert response.voice_hints.voice_fallback == "How are you showing up today?"

    async def test_no_ui_tree_for_voice_only(self, orchestrator, mock_llm_client):
        """Test no UI tree generated for voice-only modality with VOICE_DESCRIPTION."""
        import json
        # Mock extraction
        mock_llm_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(
                content='{"intent": "session_check_in", "data": {"timeAvailable": "focused", "energyLevel": 80}, "confidence": 0.9}'
            ))]
        )

        # Mock conversation engine
        mock_response = SAGEResponse(
            message="Great, you have about 45 minutes.",
            current_mode=DialogueMode.CHECK_IN,
        )
        orchestrator.conversation_engine.resume_session = MagicMock()
        orchestrator.conversation_engine.process_turn_streaming = AsyncMock(
            return_value=mock_response
        )

        response = await orchestrator.process_input(
            raw_input="I have 45 minutes and feeling good",
            source_modality=InputModality.VOICE,
            session_id="voice-test-session",
        )

        # Voice modality should NOT include UI tree (VOICE_DESCRIPTION strategy)
        assert response.ui_tree is None

    async def test_ui_generation_graceful_failure(self, orchestrator, mock_llm_client):
        """Test UI generation fails gracefully without crashing."""
        # Mock conversation engine response
        mock_response = SAGEResponse(
            message="Let's get started.",
            current_mode=DialogueMode.CHECK_IN,
        )
        orchestrator.conversation_engine.resume_session = MagicMock()
        orchestrator.conversation_engine.process_turn_streaming = AsyncMock(
            return_value=mock_response
        )

        # Mock UI agent to fail
        orchestrator.ui_agent.generate_async = AsyncMock(side_effect=Exception("LLM timeout"))

        response = await orchestrator.process_input(
            raw_input="",
            source_modality=InputModality.FORM,
            session_id="graceful-fail-session",
            form_id="session-check-in",
            form_data={"timeAvailable": "focused", "energyLevel": 80},
        )

        # Should still return a valid response, just without UI tree
        assert response.message == "Let's get started."
        assert response.ui_tree is None  # Graceful degradation

    async def test_hybrid_modality_generates_ui(self, orchestrator, mock_llm_client):
        """Test HYBRID modality generates both text and UI tree."""
        import json
        # Mock extraction for hybrid input
        extraction_response = '{"intent": "practice_setup", "data": {"scenario_type": "negotiation", "difficulty": "medium"}, "confidence": 0.9}'
        # Mock UI generation response
        ui_response = json.dumps({
            "tree": {"component": "Stack", "props": {}, "children": [
                {"component": "Text", "props": {"content": "Practice Mode"}}
            ]},
            "voice_fallback": "Starting practice mode for negotiation.",
            "purpose": "Practice setup confirmation",
            "estimated_interaction_time": 20,
        })

        def mock_create(**kwargs):
            messages = kwargs.get("messages", [])
            # Check if this is a UI generation call (has UI_AGENT_SYSTEM_PROMPT)
            system_msg = messages[0].get("content", "") if messages else ""
            if "UI generation agent" in system_msg or "You generate UI component trees" in system_msg:
                return MagicMock(
                    choices=[MagicMock(message=MagicMock(content=ui_response))]
                )
            # Otherwise it's extraction
            return MagicMock(
                choices=[MagicMock(message=MagicMock(content=extraction_response))]
            )

        mock_llm_client.chat.completions.create.side_effect = mock_create

        # Mock conversation engine
        mock_response = SAGEResponse(
            message="Practice mode ready.",
            current_mode=DialogueMode.PROBING,
        )
        orchestrator.conversation_engine.resume_session = MagicMock()
        orchestrator.conversation_engine.process_turn_streaming = AsyncMock(
            return_value=mock_response
        )

        response = await orchestrator.process_input(
            raw_input="Start a negotiation practice",
            source_modality=InputModality.HYBRID,
            session_id="hybrid-test-session",
            form_data={"scenario_type": "negotiation"},
        )

        # HYBRID should include UI tree
        assert response.ui_tree is not None
        assert response.voice_hints is not None


class TestUIAgentContext:
    """Test UI generation context building."""

    def test_build_ui_context_from_normalized_input(self, orchestrator):
        """Test _build_ui_generation_context extracts correct fields."""
        normalized = NormalizedInput(
            intent="session_check_in",
            data={"energy_level": "high", "time_available": "focused"},
            source_modality=InputModality.FORM,
        )
        decision = OrchestratorDecision(
            action="process",
            output_strategy=OutputStrategy.UI_TREE,
            context_for_llm={"intent": "session_check_in"},
        )

        orchestrator.conversation_engine.current_mode = DialogueMode.CHECK_IN
        context = orchestrator._build_ui_generation_context(normalized, decision)

        assert context["mode"] == "check_in"
        assert context["energy_level"] == "high"
        assert context["time_available"] == "focused"
        assert "session_check_in" in context.get("requirements", "")

    def test_build_ui_context_minimal(self, orchestrator):
        """Test context building with minimal input."""
        normalized = NormalizedInput(
            intent="general",
            data={},
            source_modality=InputModality.CHAT,
        )
        decision = OrchestratorDecision(
            action="process",
            output_strategy=OutputStrategy.TEXT_ONLY,
        )

        orchestrator.conversation_engine.current_mode = None
        context = orchestrator._build_ui_generation_context(normalized, decision)

        assert context["mode"] is None
        assert "energy_level" not in context
        assert "time_available" not in context
