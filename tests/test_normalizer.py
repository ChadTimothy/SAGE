"""Tests for the Unified Input Normalizer."""

import pytest

from sage.orchestration.normalizer import (
    FORM_SCHEMAS,
    InputModality,
    InputNormalizer,
    NormalizedInput,
    _infer_intent_from_form_id,
)


@pytest.fixture
def normalizer() -> InputNormalizer:
    """Create normalizer instance for tests."""
    return InputNormalizer()


class TestInputModality:
    """Test InputModality enum."""

    def test_enum_values(self):
        """Test all modality values exist."""
        assert InputModality.FORM.value == "form"
        assert InputModality.VOICE.value == "voice"
        assert InputModality.CHAT.value == "chat"
        assert InputModality.HYBRID.value == "hybrid"


class TestNormalizedInput:
    """Test NormalizedInput dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        normalized = NormalizedInput(intent="test")
        assert normalized.intent == "test"
        assert normalized.data == {}
        assert normalized.data_complete is False
        assert normalized.missing_fields == []
        assert normalized.validation_errors == []
        assert normalized.source_modality == InputModality.CHAT
        assert normalized.raw_input == ""

    def test_custom_values(self):
        """Test custom values are preserved."""
        normalized = NormalizedInput(
            intent="session_check_in",
            data={"energyLevel": 75},
            data_complete=True,
            missing_fields=[],
            validation_errors=[],
            source_modality=InputModality.FORM,
            raw_input="form:check-in-123",
        )
        assert normalized.intent == "session_check_in"
        assert normalized.data["energyLevel"] == 75
        assert normalized.data_complete is True
        assert normalized.source_modality == InputModality.FORM


class TestInferIntentFromFormId:
    """Test form ID to intent inference."""

    @pytest.mark.parametrize(
        "form_id,expected",
        [
            # Check-in variations
            ("check-in-abc123", "session_check_in"),
            ("check_in_form", "session_check_in"),
            ("session_check_in", "session_check_in"),
            ("CHECK-IN", "session_check_in"),
            # Practice variations
            ("practice-setup-123", "practice_setup"),
            ("scenario_form", "practice_setup"),
            # Verification variations
            ("verification-quiz-abc", "verification"),
            ("quiz_form", "verification"),
            # Outcome variations
            ("outcome_discovery", "outcome_discovery"),
            ("goal-form", "outcome_discovery"),
            # Application variations
            ("application-event-123", "application_event"),
            ("event_form", "application_event"),
            # Generic fallback
            ("unknown-form", "generic_form"),
            ("random123", "generic_form"),
        ],
    )
    def test_intent_inference(self, form_id: str, expected: str) -> None:
        """Test form ID to intent mapping."""
        assert _infer_intent_from_form_id(form_id) == expected


class TestInputNormalizerForm:
    """Test InputNormalizer.normalize_form()."""

    def test_check_in_complete(self, normalizer):
        """Test normalizing complete check-in form."""
        result = normalizer.normalize_form(
            "check-in-123",
            {
                "timeAvailable": "focused",
                "energyLevel": 75,
                "mindset": "excited to learn",
            },
        )
        assert result.intent == "session_check_in"
        assert result.data_complete is True
        assert result.source_modality == InputModality.FORM
        assert len(result.missing_fields) == 0
        assert len(result.validation_errors) == 0

    def test_check_in_empty(self, normalizer):
        """Test normalizing empty check-in form (all optional)."""
        result = normalizer.normalize_form("check_in", {})
        assert result.intent == "session_check_in"
        assert result.data_complete is True  # No required fields
        assert len(result.missing_fields) == 0

    def test_check_in_invalid_time(self, normalizer):
        """Test validation error for invalid timeAvailable."""
        result = normalizer.normalize_form(
            "check-in",
            {"timeAvailable": "invalid_option"},
        )
        assert result.intent == "session_check_in"
        assert result.data_complete is False
        assert len(result.validation_errors) == 1
        assert "timeAvailable" in result.validation_errors[0]

    def test_check_in_invalid_energy(self, normalizer):
        """Test validation error for out-of-range energy level."""
        result = normalizer.normalize_form(
            "check-in",
            {"energyLevel": 150},  # Out of range
        )
        assert result.data_complete is False
        assert len(result.validation_errors) == 1
        assert "energyLevel" in result.validation_errors[0]

    def test_practice_missing_required(self, normalizer):
        """Test missing required field in practice setup."""
        result = normalizer.normalize_form(
            "practice-setup",
            {"difficulty": "medium"},
        )
        assert result.intent == "practice_setup"
        assert result.data_complete is False
        assert "scenario_type" in result.missing_fields

    def test_practice_complete(self, normalizer):
        """Test complete practice setup form."""
        result = normalizer.normalize_form(
            "practice-setup",
            {"scenario_type": "pricing_call", "difficulty": "hard"},
        )
        assert result.intent == "practice_setup"
        assert result.data_complete is True
        assert len(result.missing_fields) == 0

    def test_verification_form(self, normalizer):
        """Test verification form normalization."""
        result = normalizer.normalize_form(
            "verification-quiz-123",
            {"answer": "Start high with room to come down"},
        )
        assert result.intent == "verification"
        assert result.data_complete is True
        assert result.data["answer"] == "Start high with room to come down"

    def test_generic_form(self, normalizer):
        """Test unknown form type falls back to generic."""
        result = normalizer.normalize_form(
            "custom-form",
            {"field1": "value1", "field2": 42},
        )
        assert result.intent == "generic_form"
        assert result.data == {"field1": "value1", "field2": 42}
        assert result.data_complete is True  # No required fields for generic

    def test_raw_input_preserved(self, normalizer):
        """Test raw input is preserved."""
        result = normalizer.normalize_form("my-form", {"key": "value"})
        assert result.raw_input == "form:my-form"


class TestInputNormalizerVoice:
    """Test InputNormalizer.normalize_voice()."""

    def test_simple_transcript(self, normalizer):
        """Test normalizing simple voice transcript."""
        result = normalizer.normalize_voice(
            "I have about thirty minutes and feeling energized"
        )
        assert result.intent == "pending_extraction"
        assert result.source_modality == InputModality.VOICE
        assert result.raw_input == "I have about thirty minutes and feeling energized"
        assert result.data_complete is False

    def test_with_pending_data(self, normalizer):
        """Test merging with pending data."""
        result = normalizer.normalize_voice(
            "and I'm feeling pretty focused",
            pending={"timeAvailable": "focused"},
        )
        assert result.data["timeAvailable"] == "focused"
        assert result.source_modality == InputModality.VOICE

    def test_empty_pending(self, normalizer):
        """Test with empty pending data."""
        result = normalizer.normalize_voice("Hello", pending={})
        assert result.data == {}


class TestInputNormalizerChat:
    """Test InputNormalizer.normalize_chat()."""

    def test_simple_message(self, normalizer):
        """Test normalizing simple chat message."""
        result = normalizer.normalize_chat("I want to learn pricing strategies")
        assert result.intent == "pending_extraction"
        assert result.source_modality == InputModality.CHAT
        assert result.raw_input == "I want to learn pricing strategies"

    def test_with_pending_data(self, normalizer):
        """Test merging with pending data."""
        result = normalizer.normalize_chat(
            "My energy is high",
            pending={"timeAvailable": "deep"},
        )
        assert result.data["timeAvailable"] == "deep"
        assert result.source_modality == InputModality.CHAT


class TestInputNormalizerHybrid:
    """Test InputNormalizer.normalize_hybrid()."""

    def test_voice_with_form_prefill(self, normalizer):
        """Test voice input with form data prefill."""
        result = normalizer.normalize_hybrid(
            "I'm feeling pretty tired though",
            form_data={"timeAvailable": "quick"},
            modality=InputModality.VOICE,
        )
        assert result.intent == "pending_extraction"
        assert result.data["timeAvailable"] == "quick"
        assert result.source_modality == InputModality.VOICE
        assert result.raw_input == "I'm feeling pretty tired though"

    def test_chat_with_form_prefill(self, normalizer):
        """Test chat input with form data prefill."""
        result = normalizer.normalize_hybrid(
            "Actually let me change my answer",
            form_data={"answer": "old answer"},
            modality=InputModality.CHAT,
        )
        assert result.data["answer"] == "old answer"
        assert result.source_modality == InputModality.CHAT

    def test_no_form_data(self, normalizer):
        """Test hybrid without form data."""
        result = normalizer.normalize_hybrid("Just some text")
        assert result.data == {}
        assert result.source_modality == InputModality.HYBRID


class TestInputNormalizerMerge:
    """Test InputNormalizer.merge_with_pending()."""

    def test_merge_adds_new_fields(self, normalizer):
        """Test merging adds new fields to pending data."""
        new_input = NormalizedInput(
            intent="pending_extraction",
            data={"energyLevel": 80},
            source_modality=InputModality.VOICE,
            raw_input="I'm feeling energized",
        )

        result = normalizer.merge_with_pending(
            new_input,
            pending_data={"timeAvailable": "focused"},
            pending_intent="session_check_in",
        )

        assert result.data["timeAvailable"] == "focused"
        assert result.data["energyLevel"] == 80
        assert result.intent == "session_check_in"

    def test_merge_overwrites_existing(self, normalizer):
        """Test new input overwrites existing fields."""
        new_input = NormalizedInput(
            intent="pending_extraction",
            data={"energyLevel": 30},  # New value
            source_modality=InputModality.CHAT,
            raw_input="Actually I'm tired now",
        )

        result = normalizer.merge_with_pending(
            new_input,
            pending_data={"energyLevel": 80, "timeAvailable": "deep"},
            pending_intent="session_check_in",
        )

        assert result.data["energyLevel"] == 30  # Overwritten
        assert result.data["timeAvailable"] == "deep"  # Preserved

    def test_merge_validates_against_schema(self, normalizer):
        """Test merged data is validated against schema."""
        new_input = NormalizedInput(
            intent="pending_extraction",
            data={"energyLevel": 200},  # Invalid
            source_modality=InputModality.VOICE,
            raw_input="test",
        )

        result = normalizer.merge_with_pending(
            new_input,
            pending_data={},
            pending_intent="session_check_in",
        )

        assert result.data_complete is False
        assert len(result.validation_errors) == 1

    def test_merge_uses_new_intent_when_determined(self, normalizer):
        """Test uses new input's intent when not pending_extraction."""
        new_input = NormalizedInput(
            intent="verification",  # Determined intent
            data={"answer": "test answer"},
            source_modality=InputModality.FORM,
            raw_input="form:verification-123",
        )

        result = normalizer.merge_with_pending(
            new_input,
            pending_data={},
            pending_intent="session_check_in",
        )

        assert result.intent == "verification"  # Uses new, not pending

    def test_merge_checks_required_fields(self, normalizer):
        """Test merge identifies missing required fields."""
        new_input = NormalizedInput(
            intent="pending_extraction",
            data={"difficulty": "hard"},
            source_modality=InputModality.CHAT,
            raw_input="hard mode please",
        )

        result = normalizer.merge_with_pending(
            new_input,
            pending_data={},
            pending_intent="practice_setup",
        )

        assert result.data_complete is False
        assert "scenario_type" in result.missing_fields


class TestFormSchemas:
    """Test form schema definitions."""

    def test_session_check_in_schema_exists(self):
        """Test session check-in schema is defined."""
        assert "session_check_in" in FORM_SCHEMAS
        schema = FORM_SCHEMAS["session_check_in"]
        assert "required" in schema
        assert "optional" in schema
        assert "validators" in schema

    def test_practice_setup_schema_exists(self):
        """Test practice setup schema is defined."""
        assert "practice_setup" in FORM_SCHEMAS
        schema = FORM_SCHEMAS["practice_setup"]
        assert "scenario_type" in schema["required"]

    def test_verification_schema_exists(self):
        """Test verification schema is defined."""
        assert "verification" in FORM_SCHEMAS
        schema = FORM_SCHEMAS["verification"]
        assert "answer" in schema["required"]

    def test_validators_callable(self):
        """Test all validators are callable."""
        for intent, schema in FORM_SCHEMAS.items():
            for field, validator in schema.get("validators", {}).items():
                assert callable(validator), f"{intent}.{field} validator not callable"
