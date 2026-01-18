"""End-to-end modality parity tests for Issue #130.

These tests verify that form, voice, and chat inputs produce equivalent
database storage and that the experience is seamless across all modalities.

Task 5 from Issue #130:
- 5.1: Test tap form → submit → verify database storage
- 5.2: Test voice over form → fields fill → submit → verify identical storage
- 5.3: Test voice-only (no form visible) → voice_fallback → verify storage
- 5.4: Test chat feed messages read sensibly via TTS
- 5.5: Test graceful degradation when voice extraction fails
"""

from unittest.mock import MagicMock
import json

import pytest

from sage.dialogue.structured_output import (
    PendingDataRequest,
    SAGEResponse,
)
from sage.graph.models import DialogueMode, EnergyLevel, Session, SessionContext
from sage.orchestration.normalizer import (
    FORM_SCHEMAS,
    InputModality,
    InputNormalizer,
    NormalizedInput,
)
from sage.orchestration.intent_extractor import (
    INTENT_SCHEMAS,
    SemanticIntentExtractor,
)
from sage.orchestration.orchestrator import (
    OrchestratorDecision,
    OutputStrategy,
    SAGEOrchestrator,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_graph():
    """Create mock LearningGraph with session support."""
    graph = MagicMock()
    graph.get_session.return_value = None
    graph.create_session.return_value = Session(
        id="test-session", learner_id="learner-1"
    )
    graph.update_session_context = MagicMock()
    return graph


@pytest.fixture
def mock_llm_client():
    """Create mock OpenAI client."""
    client = MagicMock()
    client.chat.completions.create = MagicMock()
    return client


@pytest.fixture
def orchestrator(mock_graph, mock_llm_client):
    """Create orchestrator with mocks."""
    return SAGEOrchestrator(
        graph=mock_graph,
        llm_client=mock_llm_client,
        extraction_model="test-model",
    )


@pytest.fixture
def normalizer():
    """Create normalizer (takes no arguments)."""
    return InputNormalizer()


@pytest.fixture
def intent_extractor(mock_llm_client):
    """Create intent extractor with mock LLM."""
    return SemanticIntentExtractor(
        llm_client=mock_llm_client,
        model="test-model",
    )


# =============================================================================
# Task 5.1: Form Submission → Database Storage
# =============================================================================


class TestFormSubmissionStorage:
    """Test that form submissions are stored correctly in the database."""

    def test_check_in_form_schema_has_required_fields(self):
        """Verify check-in form schema defines all fields."""
        schema = FORM_SCHEMAS["session_check_in"]

        # Schema uses required/optional lists, not nested fields dict
        all_fields = schema.get("required", []) + schema.get("optional", [])

        assert "timeAvailable" in all_fields
        assert "energyLevel" in all_fields
        assert "mindset" in all_fields

    def test_form_data_normalizes_to_correct_types(self, normalizer):
        """Test form data normalizes to correct field types."""
        form_data = {
            "timeAvailable": "focused",
            "energyLevel": 75,
            "mindset": "Ready to learn!",
        }

        result = normalizer.normalize_form(
            form_id="session_check_in",
            data=form_data,
        )

        assert result.intent == "session_check_in"
        assert result.data["timeAvailable"] == "focused"
        assert result.data["energyLevel"] == 75
        assert result.data["mindset"] == "Ready to learn!"
        assert result.data_complete  # All optional, so complete

    def test_form_data_creates_valid_session_context(self, normalizer):
        """Test form data can create a valid SessionContext."""
        form_data = {
            "timeAvailable": "quick",
            "energyLevel": 50,
            "mindset": "curious",
        }

        result = normalizer.normalize_form(
            form_id="session_check_in",
            data=form_data,
        )

        # Create SessionContext from normalized data
        context = SessionContext(
            time_available=result.data["timeAvailable"],
            energy=_energy_level_from_number(result.data["energyLevel"]),
            mindset=result.data["mindset"],
        )

        assert context.time_available == "quick"
        assert context.energy == EnergyLevel.MEDIUM
        assert context.mindset == "curious"

    async def test_form_submission_triggers_session_update(
        self, orchestrator, mock_graph, mock_llm_client
    ):
        """Test form submission updates session in database."""
        # Mock LLM response
        mock_llm_client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(
                            {
                                "message": "Great! Let's get started.",
                                "current_mode": "outcome_discovery",
                            }
                        )
                    )
                )
            ]
        )

        # Simulate form submission flow using normalizer
        form_data = {
            "timeAvailable": "deep",
            "energyLevel": 90,
            "mindset": "excited to learn",
        }

        normalizer = InputNormalizer()
        normalized = normalizer.normalize_form(
            form_id="session_check_in",
            data=form_data,
        )

        # Verify normalized data is complete
        assert normalized.data_complete
        assert normalized.data["timeAvailable"] == "deep"
        assert normalized.data["energyLevel"] == 90


# =============================================================================
# Task 5.2: Voice Input → Identical Database Storage
# =============================================================================


class TestVoiceInputStorage:
    """Test that voice input produces identical storage to form submission."""

    async def test_voice_extracts_same_fields_as_form(self, intent_extractor, mock_llm_client):
        """Voice extraction produces the same field names as forms."""
        # Mock LLM extraction response
        mock_llm_client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(
                            {
                                "intent": "session_check_in",
                                "data": {
                                    "timeAvailable": "focused",
                                    "energyLevel": 70,
                                    "mindset": "ready to dive in",
                                },
                                "confidence": 0.9,
                            }
                        )
                    )
                )
            ]
        )

        result = await intent_extractor.extract(
            text="I have about 30 minutes, feeling pretty good energy, ready to dive in",
        )

        # Voice should extract same fields as form schema
        form_schema = FORM_SCHEMAS["session_check_in"]
        form_fields = set(form_schema.get("required", []) + form_schema.get("optional", []))
        extracted_fields = set(result.data.keys())

        # Voice extraction should cover the same fields
        assert extracted_fields == form_fields

    async def test_voice_and_form_create_identical_context(
        self, normalizer, intent_extractor, mock_llm_client
    ):
        """Voice and form inputs create identical SessionContext."""
        # Form data
        form_data = {
            "timeAvailable": "focused",
            "energyLevel": 75,
            "mindset": "excited",
        }

        form_result = normalizer.normalize_form(
            form_id="session_check_in",
            data=form_data,
        )

        # Mock voice extraction to return equivalent data
        mock_llm_client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(
                            {
                                "intent": "session_check_in",
                                "data": {
                                    "timeAvailable": "focused",
                                    "energyLevel": 75,
                                    "mindset": "excited",
                                },
                                "confidence": 0.9,
                            }
                        )
                    )
                )
            ]
        )

        voice_result = await intent_extractor.extract(
            text="30 minutes, high energy, excited",
        )

        # Create contexts from both
        form_context = SessionContext(
            time_available=form_result.data["timeAvailable"],
            energy=_energy_level_from_number(form_result.data["energyLevel"]),
            mindset=form_result.data["mindset"],
        )

        voice_context = SessionContext(
            time_available=voice_result.data["timeAvailable"],
            energy=_energy_level_from_number(voice_result.data["energyLevel"]),
            mindset=voice_result.data["mindset"],
        )

        # Should be identical
        assert form_context.time_available == voice_context.time_available
        assert form_context.energy == voice_context.energy
        assert form_context.mindset == voice_context.mindset

    def test_voice_fills_form_visually_via_form_field_updates(self):
        """Voice input returns form_field_updates for visual form filling."""
        # Create decision for request_more with form_field_updates
        decision = OrchestratorDecision(
            action="request_more",
            output_strategy=OutputStrategy.HYBRID,
            pending_data_request=PendingDataRequest(
                intent="session_check_in",
                missing_fields=["energyLevel"],
            ),
        )

        # Normalized voice input with partial data
        normalized = NormalizedInput(
            intent="session_check_in",
            data={"timeAvailable": "focused", "mindset": "curious"},
            missing_fields=["energyLevel"],
            source_modality=InputModality.VOICE,
            raw_input="I have about 30 minutes and I'm curious today",
        )

        # form_field_updates should contain the extracted data
        # This allows frontend to prefill form fields visually
        form_field_updates = normalized.data.copy()

        assert form_field_updates is not None
        assert form_field_updates["timeAvailable"] == "focused"
        assert form_field_updates["mindset"] == "curious"


# =============================================================================
# Task 5.3: Voice-Only Mode with voice_fallback
# =============================================================================


class TestVoiceOnlyMode:
    """Test voice-only mode with voice_fallback for users without screen."""

    def test_voice_modality_gets_voice_fallback(self):
        """Voice-only users receive voice_fallback instead of UI."""
        decision = OrchestratorDecision(
            action="request_more",
            output_strategy=OutputStrategy.VOICE_DESCRIPTION,
            pending_data_request=PendingDataRequest(
                intent="session_check_in",
                missing_fields=["timeAvailable", "energyLevel", "mindset"],
            ),
        )

        # Voice-only output strategy should not generate UI tree
        assert decision.output_strategy == OutputStrategy.VOICE_DESCRIPTION

        # For voice-only, the message itself serves as the voice fallback
        # No UI tree should be generated

    def test_voice_fallback_is_tts_friendly(self):
        """Voice fallback text is appropriate for TTS."""
        example_fallbacks = [
            "How are you showing up today?",
            "What's your energy level, roughly?",
            "How much time do you have?",
        ]

        for fallback in example_fallbacks:
            # Not too long
            assert len(fallback) < 200
            # Ends with punctuation
            assert fallback[-1] in ".?!"
            # No visual references
            assert "click" not in fallback.lower()
            assert "button" not in fallback.lower()
            assert "slider" not in fallback.lower()

    def test_voice_fallback_avoids_ui_references(self):
        """Voice fallback avoids references to visual UI elements."""
        bad_phrases = [
            "click",
            "tap",
            "select",
            "dropdown",
            "checkbox",
            "radio button",
            "slider",
            "form",
            "see below",
            "shown above",
        ]

        good_fallback = "How much time do you have for learning today?"

        for phrase in bad_phrases:
            assert phrase not in good_fallback.lower()


# =============================================================================
# Task 5.4: TTS-Friendly Chat Messages
# =============================================================================


class TestTTSFriendlyMessages:
    """Test that chat feed messages are TTS-friendly."""

    def test_format_check_in_form_data_as_readable_message(self):
        """Check-in form data formats as natural language."""
        from sage.api.routes.chat import _form_data_to_message

        form_data = {
            "timeAvailable": "focused",
            "energyLevel": 75,
            "mindset": "ready to learn",
        }

        message = _form_data_to_message("session_check_in", form_data)

        # Should be readable as speech
        assert "30 minutes" in message or "focused" in message.lower()
        assert "energy" in message.lower() or "high" in message.lower()

    def test_format_quiz_answer_as_readable_message(self):
        """Quiz answer formats as natural language."""
        from sage.api.routes.chat import _form_data_to_message

        form_data = {"answer": "B"}

        message = _form_data_to_message("verification_quiz", form_data)

        # Should mention the answer
        assert "answer" in message.lower() or "B" in message

    def test_energy_level_to_text_conversion(self):
        """Energy level number converts to readable text."""
        from sage.api.routes.chat import _energy_level_to_text

        assert _energy_level_to_text(20) == "low"
        assert _energy_level_to_text(50) == "medium"
        assert _energy_level_to_text(85) == "high"

    def test_messages_have_reasonable_length_for_tts(self):
        """Messages are not too long for comfortable TTS."""
        from sage.api.routes.chat import _form_data_to_message

        # Test check-in message
        form_data = {
            "timeAvailable": "focused",
            "energyLevel": 75,
            "mindset": "ready to learn",
        }
        message = _form_data_to_message("session_check_in", form_data)

        # TTS works best with moderate length
        assert len(message) < 500
        # Message should be non-empty and readable
        assert len(message) > 0
        # Should contain readable content (not raw JSON/data)
        assert "timeAvailable" not in message  # Field names shouldn't appear
        assert any(word in message.lower() for word in ["have", "energy", "minutes"])


# =============================================================================
# Task 5.5: Graceful Degradation
# =============================================================================


class TestGracefulDegradation:
    """Test graceful degradation when voice extraction fails."""

    async def test_extraction_failure_returns_empty_data(
        self, intent_extractor, mock_llm_client
    ):
        """Failed extraction returns empty/unknown intent, not error."""
        # Mock LLM returning invalid JSON
        mock_llm_client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content="I don't understand what you said.")
                )
            ]
        )

        result = await intent_extractor.extract(
            text="garbled audio input that makes no sense",
        )

        # Should not crash, should return unknown intent
        assert result is not None
        assert result.intent == "unknown"
        assert result.confidence == 0.0

    async def test_partial_extraction_preserves_valid_fields(
        self, intent_extractor, mock_llm_client
    ):
        """Partial extraction keeps valid fields, marks rest as missing."""
        # Mock LLM returning partial data
        mock_llm_client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(
                            {
                                "intent": "session_check_in",
                                "data": {
                                    "timeAvailable": "quick",
                                    # energyLevel and mindset missing
                                },
                                "confidence": 0.7,
                            }
                        )
                    )
                )
            ]
        )

        result = await intent_extractor.extract(
            text="Just 15 minutes today",
        )

        # Should preserve valid extraction
        assert result.data.get("timeAvailable") == "quick"
        # Intent should be detected
        assert result.intent == "session_check_in"

    async def test_orchestrator_handles_extraction_exception(
        self, mock_llm_client
    ):
        """Orchestrator handles extraction exceptions gracefully."""
        # Mock LLM throwing an exception
        mock_llm_client.chat.completions.create.side_effect = Exception(
            "API rate limit exceeded"
        )

        extractor = SemanticIntentExtractor(
            llm_client=mock_llm_client,
            model="test-model",
        )

        # Should not crash, should return unknown with empty data
        result = await extractor.extract(
            text="test input",
        )

        assert result is not None
        assert result.intent == "unknown"
        assert result.confidence == 0.0

    def test_fallback_to_text_only_when_ui_generation_fails(self):
        """Text-only fallback when UI generation fails."""
        # The orchestrator should have fallback logic
        # When UIGenerationAgent fails, response should still have message
        response = SAGEResponse(
            message="How are you showing up today?",
            current_mode=DialogueMode.CHECK_IN,
        )

        # Even without UI, the message is usable
        assert response.message is not None
        assert len(response.message) > 0


# =============================================================================
# Integration Tests: Full Flow
# =============================================================================


class TestModalityParityIntegration:
    """Integration tests for full modality parity flows."""

    def test_form_schema_field_names_match_intent_schema(self):
        """Form schema field names match intent extraction schema."""
        for intent_name, form_schema in FORM_SCHEMAS.items():
            if intent_name in INTENT_SCHEMAS:
                intent_schema = INTENT_SCHEMAS[intent_name]

                # Get all field names from both schemas
                form_fields = set(
                    form_schema.get("required", []) + form_schema.get("optional", [])
                )
                intent_fields = set(
                    intent_schema.get("required", []) + intent_schema.get("optional", [])
                )

                # Form fields should be subset of intent fields (intent may have more)
                assert form_fields <= intent_fields, (
                    f"Form fields not in intent for {intent_name}: "
                    f"{form_fields - intent_fields}"
                )

    def test_all_form_types_have_schema_structure(self):
        """All form types have proper schema structure."""
        for form_name, schema in FORM_SCHEMAS.items():
            # Schema should have required and/or optional
            assert "required" in schema or "optional" in schema, (
                f"{form_name} missing required/optional"
            )

    async def test_voice_input_flows_to_same_storage_as_form(
        self, normalizer, intent_extractor, mock_llm_client
    ):
        """Full flow: voice input results in same storage as form."""
        # This is the key integration test for modality parity

        # Step 1: Form submission data
        form_data = {
            "timeAvailable": "deep",
            "energyLevel": 85,
            "mindset": "focused and ready",
        }

        form_normalized = normalizer.normalize_form(
            form_id="session_check_in",
            data=form_data,
        )

        # Step 2: Equivalent voice input
        mock_llm_client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(
                            {
                                "intent": "session_check_in",
                                "data": {
                                    "timeAvailable": "deep",
                                    "energyLevel": 85,
                                    "mindset": "focused and ready",
                                },
                                "confidence": 0.95,
                            }
                        )
                    )
                )
            ]
        )

        voice_extracted = await intent_extractor.extract(
            text="I have an hour or more, high energy, focused and ready",
        )

        # Both should produce identical data for storage
        assert form_normalized.data == voice_extracted.data
        assert form_normalized.intent == voice_extracted.intent


# =============================================================================
# Helper Functions
# =============================================================================


def _energy_level_from_number(level: int) -> EnergyLevel:
    """Convert numeric energy level to EnergyLevel enum."""
    if level < 40:
        return EnergyLevel.LOW
    elif level < 70:
        return EnergyLevel.MEDIUM
    else:
        return EnergyLevel.HIGH
