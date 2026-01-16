"""Semantic Intent Extractor for Voice/UI Parity.

Uses LLM to extract structured data from natural language voice/chat input.
Supports schema-driven extraction with hints for mapping natural language
to enum values and numeric ranges.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class ExtractedIntent:
    """Result of semantic extraction from natural language."""

    intent: str
    """Detected intent (e.g., 'session_check_in', 'practice_setup')."""

    data: dict[str, Any] = field(default_factory=dict)
    """Extracted structured data."""

    data_complete: bool = False
    """Whether all required fields were extracted."""

    missing_fields: list[str] = field(default_factory=list)
    """Fields that could not be extracted."""

    confidence: float = 0.0
    """Confidence score (0.0-1.0) for the extraction."""


# =============================================================================
# Intent Schemas - Define extraction rules for each intent type
# =============================================================================

INTENT_SCHEMAS: dict[str, dict[str, Any]] = {
    "session_check_in": {
        "description": "Session check-in for gathering learner context",
        "required": [],  # All optional for flexibility
        "optional": ["timeAvailable", "energyLevel", "mindset"],
        "extraction_hints": {
            "timeAvailable": {
                "type": "enum",
                "values": ["quick", "focused", "deep"],
                "mappings": [
                    ("15 minutes, quick, short, little time", "quick"),
                    ("30 minutes, half hour, 30-45 minutes", "focused"),
                    ("hour, hour or more, plenty of time, no rush", "deep"),
                ],
            },
            "energyLevel": {
                "type": "number",
                "range": [0, 100],
                "mappings": [
                    ("exhausted, very tired, wiped out", "0-20"),
                    ("tired, low energy, dragging", "20-40"),
                    ("okay, fine, moderate", "40-60"),
                    ("good, solid, decent energy", "60-80"),
                    ("energized, excited, pumped, great", "80-100"),
                ],
            },
            "mindset": {
                "type": "string",
                "description": "Free-form description of current mental state",
            },
        },
    },
    "practice_setup": {
        "description": "Setup for practice/roleplay scenario",
        "required": ["scenario_type"],
        "optional": ["difficulty", "context", "focus_area"],
        "extraction_hints": {
            "scenario_type": {
                "type": "string",
                "description": "Type of scenario (e.g., 'pricing_call', 'negotiation')",
            },
            "difficulty": {
                "type": "enum",
                "values": ["easy", "medium", "hard"],
                "mappings": [
                    ("easy, simple, beginner, gentle", "easy"),
                    ("medium, moderate, normal", "medium"),
                    ("hard, difficult, challenging, advanced", "hard"),
                ],
            },
            "context": {
                "type": "string",
                "description": "Additional context for the scenario",
            },
            "focus_area": {
                "type": "string",
                "description": "Specific skill area to focus on",
            },
        },
    },
    "application_event": {
        "description": "Capture upcoming real-world application",
        "required": ["context"],
        "optional": ["planned_date", "stakes", "concept_ids"],
        "extraction_hints": {
            "context": {
                "type": "string",
                "description": "What they'll be applying (e.g., 'pricing call tomorrow')",
            },
            "planned_date": {
                "type": "date",
                "description": "When the application is planned (ISO format)",
            },
            "stakes": {
                "type": "enum",
                "values": ["low", "medium", "high"],
                "mappings": [
                    ("not important, casual, practice", "low"),
                    ("somewhat important, normal", "medium"),
                    ("very important, critical, high stakes, big deal", "high"),
                ],
            },
        },
    },
    "verification": {
        "description": "Response to a verification question",
        "required": ["answer"],
        "optional": ["confidence", "notes"],
        "extraction_hints": {
            "answer": {
                "type": "string",
                "description": "The learner's answer to the verification question",
            },
            "confidence": {
                "type": "number",
                "range": [0, 100],
                "mappings": [
                    ("not sure, guessing, uncertain", "0-30"),
                    ("somewhat confident, think so", "30-60"),
                    ("confident, pretty sure", "60-80"),
                    ("very confident, certain, definitely", "80-100"),
                ],
            },
        },
    },
    "outcome_discovery": {
        "description": "Discovering learner's goal/outcome",
        "required": [],
        "optional": ["goal", "context", "timeline", "motivation"],
        "extraction_hints": {
            "goal": {
                "type": "string",
                "description": "What they want to be able to DO",
            },
            "context": {
                "type": "string",
                "description": "Why they want to learn this",
            },
            "timeline": {
                "type": "string",
                "description": "When they need this skill",
            },
            "motivation": {
                "type": "string",
                "description": "What's driving them to learn",
            },
        },
    },
    "filter_graph": {
        "description": "Filter knowledge graph visualization",
        "required": [],
        "optional": [
            "show_proven_only",
            "show_concepts",
            "show_outcomes",
            "text_filter",
            "reset_filters",
        ],
        "extraction_hints": {
            "show_proven_only": {
                "type": "boolean",
                "mappings": [
                    ("proven, verified, demonstrated, mastered", True),
                    ("all, everything, unfiltered", False),
                ],
            },
            "show_concepts": {
                "type": "boolean",
                "mappings": [
                    ("concepts, topics, ideas, knowledge", True),
                    ("hide concepts, no concepts", False),
                ],
            },
            "show_outcomes": {
                "type": "boolean",
                "mappings": [
                    ("goals, outcomes, objectives", True),
                    ("hide goals, hide outcomes, no goals", False),
                ],
            },
            "text_filter": {
                "type": "string",
                "description": "Filter by text/topic (e.g., 'pricing', 'negotiation')",
            },
            "reset_filters": {
                "type": "boolean",
                "mappings": [
                    ("show everything, clear filters, reset, all", True),
                ],
            },
        },
    },
}


def _build_extraction_prompt(text: str, pending_context: dict[str, Any] | None) -> str:
    """Build the extraction prompt for the LLM."""
    schemas_desc = []
    for intent_name, schema in INTENT_SCHEMAS.items():
        fields = []
        for field_name in schema.get("required", []) + schema.get("optional", []):
            hints = schema.get("extraction_hints", {}).get(field_name, {})
            field_desc = f"  - {field_name}"
            if hints.get("type") == "enum":
                field_desc += f" (one of: {', '.join(hints['values'])})"
            elif hints.get("type") == "number":
                field_desc += f" (number {hints['range'][0]}-{hints['range'][1]})"
            if "mappings" in hints:
                mapping_examples = "; ".join(f'"{m[0]}" -> {m[1]}' for m in hints["mappings"][:2])
                field_desc += f"\n    Mappings: {mapping_examples}"
            fields.append(field_desc)
        schemas_desc.append(f"**{intent_name}**: {schema['description']}\n" + "\n".join(fields))

    pending_info = ""
    if pending_context:
        pending_info = f"\n\nPreviously collected data: {json.dumps(pending_context)}"

    return f"""Extract structured data from the following natural language input.

## Available Intents and Fields

{chr(10).join(schemas_desc)}

## Input Text
"{text}"{pending_info}

## Instructions

1. Determine which intent best matches the input
2. Extract values for as many fields as you can confidently identify
3. Map natural language to the appropriate enum values or number ranges
4. Return a JSON object with:
   - "intent": the detected intent name
   - "data": object with extracted field values
   - "confidence": your confidence in the extraction (0.0-1.0)

If the input doesn't clearly match any intent, return intent="unknown".
If you can't extract a field with confidence, omit it from data.

Respond with ONLY valid JSON, no other text."""


def _parse_llm_response(response_text: str) -> dict[str, Any]:
    """Parse LLM response into structured data."""
    try:
        # Try to parse as JSON
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(response_text[start:end])
            except json.JSONDecodeError:
                pass
    return {"intent": "unknown", "data": {}, "confidence": 0.0}


_SYSTEM_MESSAGE = (
    "You are a semantic extraction assistant. "
    "Extract structured data from natural language and return only valid JSON."
)


def _build_extracted_intent(
    result: dict[str, Any],
    pending_context: dict[str, Any] | None,
) -> ExtractedIntent:
    """Build ExtractedIntent from LLM result and pending context."""
    intent = result.get("intent", "unknown")
    merged_data = {**(pending_context or {}), **result.get("data", {})}

    schema = INTENT_SCHEMAS.get(intent, {})
    required = schema.get("required", [])
    missing = [f for f in required if not merged_data.get(f)]

    return ExtractedIntent(
        intent=intent,
        data=merged_data,
        data_complete=not missing,
        missing_fields=missing,
        confidence=result.get("confidence", 0.5),
    )


class SemanticIntentExtractor:
    """Extracts structured data from natural language using LLM.

    This class is the second stage of the voice/UI parity pipeline:
    taking normalized unstructured input and extracting semantic intent
    and structured data.
    """

    def __init__(
        self,
        llm_client: OpenAI,
        model: str = "grok-3-mini",
        temperature: float = 0.3,
    ):
        """Initialize the intent extractor.

        Args:
            llm_client: OpenAI-compatible client for LLM calls
            model: Model to use for extraction
            temperature: Lower temperature for more deterministic extraction
        """
        self.client = llm_client
        self.model = model
        self.temperature = temperature

    def _call_llm(self, prompt: str) -> dict[str, Any]:
        """Call LLM and parse response.

        Returns parsed result dict or raises exception on failure.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_MESSAGE},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=500,
        )
        return _parse_llm_response(response.choices[0].message.content or "")

    def _extract_impl(
        self,
        text: str,
        pending_context: dict[str, Any] | None,
    ) -> ExtractedIntent:
        """Core extraction logic shared by sync and async methods."""
        prompt = _build_extraction_prompt(text, pending_context)

        try:
            result = self._call_llm(prompt)
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return ExtractedIntent(
                intent="unknown",
                data=dict(pending_context) if pending_context else {},
                confidence=0.0,
            )

        return _build_extracted_intent(result, pending_context)

    async def extract(
        self,
        text: str,
        pending_context: dict[str, Any] | None = None,
    ) -> ExtractedIntent:
        """Extract intent and data from natural language text.

        Args:
            text: The natural language input to extract from
            pending_context: Previously collected data (for multi-turn collection)

        Returns:
            ExtractedIntent with detected intent and extracted data
        """
        return self._extract_impl(text, pending_context)

    def extract_sync(
        self,
        text: str,
        pending_context: dict[str, Any] | None = None,
    ) -> ExtractedIntent:
        """Synchronous version of extract for non-async contexts.

        Args:
            text: The natural language input to extract from
            pending_context: Previously collected data

        Returns:
            ExtractedIntent with detected intent and extracted data
        """
        return self._extract_impl(text, pending_context)
