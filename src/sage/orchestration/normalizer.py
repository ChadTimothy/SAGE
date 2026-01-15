"""Unified Input Normalizer for Voice/UI Parity.

Converts any input type (form, voice, chat) to a normalized semantic
intent structure for consistent processing by the SAGE orchestrator.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class InputModality(Enum):
    """Source modality for user input."""

    FORM = "form"
    VOICE = "voice"
    CHAT = "chat"
    HYBRID = "hybrid"  # Mixed modality (e.g., voice + form prefill)


@dataclass
class NormalizedInput:
    """Unified input regardless of source modality.

    This structure is the common format used by the SAGE orchestrator,
    regardless of whether input came from a form, voice, or chat.
    """

    intent: str
    """Semantic intent identifier (e.g., 'session_check_in', 'practice_setup')."""

    data: dict[str, Any] = field(default_factory=dict)
    """Extracted structured data from the input."""

    data_complete: bool = False
    """Whether all required fields for this intent are present."""

    missing_fields: list[str] = field(default_factory=list)
    """Fields still needed to complete the intent."""

    validation_errors: list[str] = field(default_factory=list)
    """Validation failures encountered during normalization."""

    source_modality: InputModality = InputModality.CHAT
    """Where the input came from."""

    raw_input: str = ""
    """Original input for context and debugging."""


FORM_SCHEMAS: dict[str, dict[str, Any]] = {
    "session_check_in": {
        "required": [],  # All fields optional for flexibility
        "optional": ["timeAvailable", "energyLevel", "mindset"],
        "validators": {
            "timeAvailable": lambda v: v in ("quick", "focused", "deep"),
            "energyLevel": lambda v: isinstance(v, (int, float)) and 0 <= v <= 100,
        },
    },
    "practice_setup": {
        "required": ["scenario_type"],
        "optional": ["difficulty", "context", "focus_area"],
        "validators": {
            "difficulty": lambda v: v in ("easy", "medium", "hard"),
        },
    },
    "verification": {
        "required": ["answer"],
        "optional": ["confidence", "notes"],
        "validators": {
            "confidence": lambda v: isinstance(v, (int, float)) and 0 <= v <= 100,
        },
    },
    "outcome_discovery": {
        "required": [],
        "optional": ["goal", "context", "timeline"],
        "validators": {},
    },
    "application_event": {
        "required": [],
        "optional": ["context", "planned_date", "stakes"],
        "validators": {
            "stakes": lambda v: v in ("low", "medium", "high"),
        },
    },
}


_DEFAULT_SCHEMA: dict[str, Any] = {"required": [], "optional": [], "validators": {}}

_FORM_ID_TO_INTENT: list[tuple[tuple[str, ...], str]] = [
    (("check_in", "check-in"), "session_check_in"),
    (("practice", "scenario"), "practice_setup"),
    (("verification", "quiz"), "verification"),
    (("outcome", "goal"), "outcome_discovery"),
    (("application", "event"), "application_event"),
]


def _infer_intent_from_form_id(form_id: str) -> str:
    """Infer semantic intent from form ID.

    Maps form IDs (like 'check-in-abc123') to semantic intents
    (like 'session_check_in').
    """
    form_id_lower = form_id.lower()
    for keywords, intent in _FORM_ID_TO_INTENT:
        if any(keyword in form_id_lower for keyword in keywords):
            return intent
    return "generic_form"


def _validate_against_schema(
    intent: str,
    data: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Validate data against the schema for an intent.

    Returns:
        Tuple of (missing_fields, validation_errors)
    """
    schema = FORM_SCHEMAS.get(intent, _DEFAULT_SCHEMA)
    missing_fields = []
    validation_errors = []

    for field_name in schema.get("required", []):
        if field_name not in data or data[field_name] is None:
            missing_fields.append(field_name)

    validators = schema.get("validators", {})
    for field_name, value in data.items():
        if field_name in validators and value is not None:
            try:
                if not validators[field_name](value):
                    validation_errors.append(f"Invalid value for {field_name}: {value}")
            except Exception as e:
                validation_errors.append(f"Validation error for {field_name}: {e}")

    return missing_fields, validation_errors


class InputNormalizer:
    """Converts any input to NormalizedInput.

    This class handles the first stage of the voice/UI parity pipeline:
    taking raw input from any modality and converting it to a standard
    format for downstream processing.
    """

    def normalize_form(
        self,
        form_id: str,
        data: dict[str, Any],
    ) -> NormalizedInput:
        """Normalize form submission.

        Form data is already structured, so we just need to:
        1. Infer the intent from the form ID
        2. Validate against the schema
        3. Identify any missing required fields
        """
        intent = _infer_intent_from_form_id(form_id)
        missing_fields, validation_errors = _validate_against_schema(intent, data)

        return NormalizedInput(
            intent=intent,
            data=data,
            data_complete=not missing_fields and not validation_errors,
            missing_fields=missing_fields,
            validation_errors=validation_errors,
            source_modality=InputModality.FORM,
            raw_input=f"form:{form_id}",
        )

    def _normalize_unstructured(
        self,
        raw_input: str,
        modality: InputModality,
        pending_data: dict[str, Any] | None = None,
    ) -> NormalizedInput:
        """Normalize unstructured input (voice, chat, or hybrid).

        Unstructured input requires semantic extraction by the Intent Extractor.
        Intent is marked as 'pending_extraction' until extracted downstream.
        """
        return NormalizedInput(
            intent="pending_extraction",
            data=dict(pending_data) if pending_data else {},
            data_complete=False,
            source_modality=modality,
            raw_input=raw_input,
        )

    def normalize_voice(
        self,
        transcript: str,
        pending: dict[str, Any] | None = None,
    ) -> NormalizedInput:
        """Normalize voice transcription."""
        return self._normalize_unstructured(transcript, InputModality.VOICE, pending)

    def normalize_chat(
        self,
        message: str,
        pending: dict[str, Any] | None = None,
    ) -> NormalizedInput:
        """Normalize chat message."""
        return self._normalize_unstructured(message, InputModality.CHAT, pending)

    def normalize_hybrid(
        self,
        message: str,
        form_data: dict[str, Any] | None = None,
        modality: InputModality = InputModality.HYBRID,
    ) -> NormalizedInput:
        """Normalize hybrid input (voice/chat with form prefill)."""
        return self._normalize_unstructured(message, modality, form_data)

    def merge_with_pending(
        self,
        new_input: NormalizedInput,
        pending_data: dict[str, Any],
        pending_intent: str,
    ) -> NormalizedInput:
        """Merge new input with pending incomplete data.

        This is used when collecting data across multiple turns.
        The new input's data is merged into the pending data.

        Args:
            new_input: The newly normalized input
            pending_data: Data collected in previous turns
            pending_intent: The intent we're collecting data for
        """
        merged = {**pending_data, **new_input.data}
        intent = pending_intent if new_input.intent == "pending_extraction" else new_input.intent
        missing_fields, validation_errors = _validate_against_schema(intent, merged)

        return NormalizedInput(
            intent=intent,
            data=merged,
            data_complete=not missing_fields and not validation_errors,
            missing_fields=missing_fields,
            validation_errors=validation_errors,
            source_modality=new_input.source_modality,
            raw_input=new_input.raw_input,
        )
