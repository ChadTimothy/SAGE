"""SAGE Orchestrator - Central routing and decision making.

The orchestrator is the main entry point for all user inputs. It:
1. Normalizes inputs from any modality (form, voice, chat)
2. Extracts semantic intent from unstructured inputs
3. Decides whether to request more data or process
4. Determines the appropriate output strategy
5. Routes to ConversationEngine for processing
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

from openai import OpenAI

from sage.dialogue.conversation import ConversationEngine
from sage.dialogue.structured_output import (
    ExtendedSAGEResponse,
    PendingDataRequest,
    VoiceHints,
)
from sage.graph.learning_graph import LearningGraph
from sage.graph.models import DialogueMode
from sage.orchestration.intent_extractor import SemanticIntentExtractor
from sage.orchestration.normalizer import (
    InputModality,
    InputNormalizer,
    NormalizedInput,
)
from sage.orchestration.ui_agent import UIGenerationAgent

logger = logging.getLogger(__name__)


class OutputStrategy(Enum):
    """How to format the response for the user."""

    TEXT_ONLY = "text_only"
    """Pure text response, suitable for voice or simple chat."""

    UI_TREE = "ui_tree"
    """Generate composable UI tree for rich interactions."""

    VOICE_DESCRIPTION = "voice_description"
    """Text optimized for voice with TTS hints."""

    HYBRID = "hybrid"
    """Both text and UI tree for multimodal experiences."""


@dataclass
class OrchestratorDecision:
    """The orchestrator's decision on how to handle an input."""

    action: str
    """Action to take: 'process', 'request_more', 'generate_ui'."""

    output_strategy: OutputStrategy
    """How to format the response."""

    context_for_llm: dict[str, Any] = field(default_factory=dict)
    """Additional context to pass to the LLM."""

    pending_data_request: PendingDataRequest | None = None
    """Tracks incomplete data collection state."""


# Output strategy mapping based on intent and modality
_OUTPUT_STRATEGY_MAP: dict[tuple[str, InputModality], OutputStrategy] = {
    # Session check-in: forms need UI tree, voice needs descriptions
    ("session_check_in", InputModality.FORM): OutputStrategy.UI_TREE,
    ("session_check_in", InputModality.VOICE): OutputStrategy.VOICE_DESCRIPTION,
    ("session_check_in", InputModality.CHAT): OutputStrategy.TEXT_ONLY,
    ("session_check_in", InputModality.HYBRID): OutputStrategy.HYBRID,
    # Practice setup: always UI tree for scenario selection
    ("practice_setup", InputModality.FORM): OutputStrategy.UI_TREE,
    ("practice_setup", InputModality.VOICE): OutputStrategy.HYBRID,
    ("practice_setup", InputModality.CHAT): OutputStrategy.HYBRID,
    ("practice_setup", InputModality.HYBRID): OutputStrategy.HYBRID,
    # Verification: text responses work well
    ("verification", InputModality.FORM): OutputStrategy.TEXT_ONLY,
    ("verification", InputModality.VOICE): OutputStrategy.TEXT_ONLY,
    ("verification", InputModality.CHAT): OutputStrategy.TEXT_ONLY,
}

_DEFAULT_OUTPUT_STRATEGY = OutputStrategy.TEXT_ONLY


class SAGEOrchestrator:
    """Central orchestrator for all SAGE inputs.

    The orchestrator manages the full input processing pipeline:
    1. Normalize input (form → structured, voice/chat → pending extraction)
    2. Extract intent (for unstructured inputs)
    3. Make decision (process vs request more data)
    4. Execute action (route to conversation engine or generate UI)
    5. Return extended response with appropriate format
    """

    def __init__(
        self,
        graph: LearningGraph,
        llm_client: OpenAI,
        *,
        extraction_model: str = "grok-3-mini",
        ui_generation_model: str = "grok-2",
    ):
        """Initialize the orchestrator.

        Args:
            graph: The learning graph for data access
            llm_client: OpenAI-compatible client for LLM calls
            extraction_model: Model to use for intent extraction
            ui_generation_model: Model to use for UI generation (default: grok-2)
        """
        self.graph = graph
        self.llm_client = llm_client

        # Initialize components
        self.normalizer = InputNormalizer()
        self.intent_extractor = SemanticIntentExtractor(
            llm_client,
            model=extraction_model,
        )
        self.conversation_engine = ConversationEngine(graph, llm_client)
        self.ui_agent = UIGenerationAgent(
            llm_client,
            model=ui_generation_model,
        )

        # Track pending data requests per session
        self._pending_requests: dict[str, PendingDataRequest] = {}

    async def process_input(
        self,
        raw_input: str,
        source_modality: InputModality,
        session_id: str,
        *,
        form_id: str | None = None,
        form_data: dict[str, Any] | None = None,
        on_chunk: Callable[[str], Awaitable[None]] | None = None,
    ) -> ExtendedSAGEResponse:
        """Main entry point for all inputs.

        Args:
            raw_input: The raw text input (transcript, message, or empty for forms)
            source_modality: Where the input came from
            session_id: Current session identifier
            form_id: Form identifier (for form modality)
            form_data: Form field values (for form modality)
            on_chunk: Optional streaming callback

        Returns:
            ExtendedSAGEResponse with appropriate format for the modality
        """
        # Step 1: Normalize the input
        normalized = self._normalize_input(
            raw_input,
            source_modality,
            form_id,
            form_data,
        )

        # Step 2: Extract intent if needed (unstructured inputs)
        if normalized.intent == "pending_extraction":
            pending = self._get_pending_context(session_id)
            extracted = await self.intent_extractor.extract(
                normalized.raw_input,
                pending_context=pending,
            )
            normalized = NormalizedInput(
                intent=extracted.intent,
                data=extracted.data,
                data_complete=extracted.data_complete,
                missing_fields=extracted.missing_fields,
                source_modality=normalized.source_modality,
                raw_input=normalized.raw_input,
            )

        # Step 3: Make decision
        decision = self._make_decision(normalized, session_id)

        # Step 4: Execute action
        if decision.action == "request_more":
            return await self._create_data_request_response(decision, normalized)

        # Step 5: Process through conversation engine
        return await self._process_with_engine(
            normalized,
            decision,
            session_id,
            on_chunk,
        )

    def _normalize_input(
        self,
        raw_input: str,
        source_modality: InputModality,
        form_id: str | None,
        form_data: dict[str, Any] | None,
    ) -> NormalizedInput:
        """Normalize input based on modality."""
        if source_modality == InputModality.FORM and form_id and form_data is not None:
            return self.normalizer.normalize_form(form_id, form_data)
        elif source_modality == InputModality.VOICE:
            return self.normalizer.normalize_voice(raw_input)
        elif source_modality == InputModality.HYBRID:
            return self.normalizer.normalize_hybrid(
                raw_input,
                form_data=form_data,
                modality=InputModality.HYBRID,
            )
        else:
            return self.normalizer.normalize_chat(raw_input)

    def _get_pending_context(self, session_id: str) -> dict[str, Any] | None:
        """Get pending data context for a session."""
        pending = self._pending_requests.get(session_id)
        if pending:
            return pending.collected_data
        return None

    def _make_decision(
        self,
        normalized: NormalizedInput,
        session_id: str,
    ) -> OrchestratorDecision:
        """Decide what action to take based on normalized input."""
        output_strategy = self._determine_output_strategy(
            normalized.intent,
            normalized.source_modality,
        )

        # If data is incomplete, request more
        if not normalized.data_complete and normalized.missing_fields:
            pending_request = PendingDataRequest(
                intent=normalized.intent,
                collected_data=normalized.data,
                missing_fields=normalized.missing_fields,
                validation_errors=normalized.validation_errors,
            )
            self._pending_requests[session_id] = pending_request

            return OrchestratorDecision(
                action="request_more",
                output_strategy=output_strategy,
                context_for_llm={"missing_fields": normalized.missing_fields},
                pending_data_request=pending_request,
            )

        # Data is complete, clear any pending request and process
        if session_id in self._pending_requests:
            del self._pending_requests[session_id]

        return OrchestratorDecision(
            action="process",
            output_strategy=output_strategy,
            context_for_llm={
                "intent": normalized.intent,
                "data": normalized.data,
            },
        )

    def _determine_output_strategy(
        self,
        intent: str,
        source_modality: InputModality,
    ) -> OutputStrategy:
        """Choose the appropriate output format."""
        key = (intent, source_modality)
        return _OUTPUT_STRATEGY_MAP.get(key, _DEFAULT_OUTPUT_STRATEGY)

    async def _create_data_request_response(
        self,
        decision: OrchestratorDecision,
        normalized: NormalizedInput,
    ) -> ExtendedSAGEResponse:
        """Create a response requesting more data from the user.

        For form modality: Returns structured validation messages
        For voice/chat: Generates conversational follow-up using LLM

        When voice input extracts form field values, includes form_field_updates
        so the frontend can update the form visually (voice/UI parity).
        """
        is_check_in = normalized.intent == "session_check_in"
        current_mode = DialogueMode.CHECK_IN if is_check_in else DialogueMode.PROBING

        # Determine if we should include form_field_updates for voice-to-form mapping
        form_field_updates = None
        if normalized.source_modality in (InputModality.VOICE, InputModality.HYBRID):
            # Voice input extracted values - include for form field visual updates
            if normalized.data:
                form_field_updates = normalized.data.copy()

        # Form modality: use template-based validation messages
        if normalized.source_modality == InputModality.FORM:
            message = _build_missing_fields_message(normalized.missing_fields)
            if normalized.validation_errors:
                errors = "; ".join(normalized.validation_errors)
                message = f"{errors}. {message}"
        else:
            # Voice/chat/hybrid: generate conversational probe using LLM
            message = await self._generate_conversational_probe(
                intent=normalized.intent,
                collected_data=normalized.data,
                missing_fields=normalized.missing_fields,
            )

        return ExtendedSAGEResponse(
            message=message,
            current_mode=current_mode,
            pending_data_request=decision.pending_data_request,
            form_field_updates=form_field_updates,
        )

    async def _generate_conversational_probe(
        self,
        intent: str,
        collected_data: dict[str, Any],
        missing_fields: list[str],
    ) -> str:
        """Generate a natural conversational follow-up question using LLM.

        Creates contextual, SAGE-personality-aligned questions to gather
        missing data during multi-turn collection.
        """
        prompt = _build_probe_prompt(intent, collected_data, missing_fields)

        try:
            response = self.llm_client.chat.completions.create(
                model=self.intent_extractor.model,
                messages=[
                    {"role": "system", "content": _PROBE_SYSTEM_MESSAGE},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=150,
            )
            return response.choices[0].message.content or _build_missing_fields_message(missing_fields)
        except Exception as e:
            logger.warning(f"LLM probe generation failed: {e}, falling back to template")
            return _build_missing_fields_message(missing_fields)

    async def _process_with_engine(
        self,
        normalized: NormalizedInput,
        decision: OrchestratorDecision,
        session_id: str,
        on_chunk: Callable[[str], Awaitable[None]] | None,
    ) -> ExtendedSAGEResponse:
        """Process through the conversation engine."""
        # Resume the session to load context before processing
        self.conversation_engine.resume_session(session_id)

        user_message = _build_user_message(normalized)
        chunk_handler = on_chunk or _null_chunk_handler

        base_response = await self.conversation_engine.process_turn_streaming(
            user_message,
            chunk_handler,
        )

        should_include_ui = decision.output_strategy in (
            OutputStrategy.UI_TREE,
            OutputStrategy.HYBRID,
        )

        # Generate UI tree if needed
        ui_tree = None
        ui_purpose = None
        voice_hints = None
        estimated_interaction_time = None

        if should_include_ui:
            ui_purpose = f"Response for {normalized.intent}"
            ui_context = self._build_ui_generation_context(normalized, decision)

            try:
                ui_spec = await self.ui_agent.generate_async(
                    purpose=ui_purpose,
                    context=ui_context,
                )
                ui_tree = ui_spec.tree
                ui_purpose = ui_spec.purpose
                estimated_interaction_time = ui_spec.estimated_interaction_time
                voice_hints = VoiceHints(
                    voice_fallback=ui_spec.voice_fallback,
                )
                logger.info(f"Generated UI tree for intent: {normalized.intent}")
            except Exception as e:
                logger.warning(f"UI generation failed, continuing without UI: {e}")
                # Continue without UI tree - graceful degradation

        # Include form_field_updates for voice-to-form mapping when voice input
        # extracted data (enables visual form filling for modality parity)
        form_field_updates = None
        if normalized.source_modality in (InputModality.VOICE, InputModality.HYBRID):
            if normalized.data:
                form_field_updates = normalized.data.copy()

        return ExtendedSAGEResponse(
            message=base_response.message,
            current_mode=base_response.current_mode,
            transition_to=base_response.transition_to,
            transition_reason=base_response.transition_reason,
            gap_identified=base_response.gap_identified,
            proof_earned=base_response.proof_earned,
            connection_discovered=base_response.connection_discovered,
            application_detected=base_response.application_detected,
            followup_response=base_response.followup_response,
            state_change_detected=base_response.state_change_detected,
            context_update=base_response.context_update,
            outcome_achieved=base_response.outcome_achieved,
            outcome_reasoning=base_response.outcome_reasoning,
            teaching_approach_used=base_response.teaching_approach_used,
            reasoning=base_response.reasoning,
            ui_tree=ui_tree,
            voice_hints=voice_hints,
            ui_purpose=ui_purpose,
            estimated_interaction_time=estimated_interaction_time,
            form_field_updates=form_field_updates,
        )

    def _build_ui_generation_context(
        self,
        normalized: NormalizedInput,
        decision: OrchestratorDecision,
    ) -> dict[str, Any]:
        """Build context for UI generation based on normalized input and decision."""
        context: dict[str, Any] = {
            "mode": str(self.conversation_engine.current_mode.value)
            if self.conversation_engine.current_mode
            else None,
        }

        # Extract session context from data if available
        if normalized.data:
            if "energy_level" in normalized.data:
                context["energy_level"] = normalized.data["energy_level"]
            if "time_available" in normalized.data:
                context["time_available"] = normalized.data["time_available"]

        # Add requirements from decision context
        if decision.context_for_llm:
            if "intent" in decision.context_for_llm:
                context["requirements"] = f"For {decision.context_for_llm['intent']} interaction"

        return context

    def get_pending_request(self, session_id: str) -> PendingDataRequest | None:
        """Get the pending data request for a session."""
        return self._pending_requests.get(session_id)

    def clear_pending_request(self, session_id: str) -> None:
        """Clear a pending data request."""
        if session_id in self._pending_requests:
            del self._pending_requests[session_id]


async def _null_chunk_handler(chunk: str) -> None:
    """No-op chunk handler for non-streaming calls."""


def _build_missing_fields_message(missing: list[str]) -> str:
    """Build a user-friendly message asking for missing data fields."""
    if len(missing) == 0:
        return "Please provide some more details."
    if len(missing) == 1:
        return f"I need one more piece of information: {missing[0]}. Could you tell me more?"
    if len(missing) == 2:
        return f"I'm missing some information: {missing[0]} and {missing[1]}. Could you fill in those details?"

    fields = ", ".join(missing[:-1]) + f", and {missing[-1]}"
    return f"I'm missing some information: {fields}. Could you fill in those details?"


def _build_user_message(normalized: NormalizedInput) -> str:
    """Build user message with context from normalized input."""
    if not normalized.data:
        return normalized.raw_input

    data_summary = ", ".join(
        f"{k}: {v}" for k, v in normalized.data.items() if v is not None
    )
    if not data_summary:
        return normalized.raw_input

    if normalized.source_modality == InputModality.FORM:
        return f"[Form data: {data_summary}]"

    return f"{normalized.raw_input} [Context: {data_summary}]"


_PROBE_SYSTEM_MESSAGE = """You are SAGE, an AI tutor. Generate a brief, natural follow-up question.

Personality:
- Direct, gets to the point
- Respects intelligence, doesn't talk down
- Slightly dry, efficient
- Think JARVIS, not professor

Rules:
- One short question only (1-2 sentences max)
- Acknowledge what they already told you
- Ask naturally about missing info
- Sound conversational, not like a form"""


def _build_probe_prompt(
    intent: str,
    collected_data: dict[str, Any],
    missing_fields: list[str],
) -> str:
    """Build prompt for generating conversational follow-up questions."""
    collected_summary = (
        ", ".join(f"{k}={v}" for k, v in collected_data.items() if v is not None)
        if collected_data
        else "nothing yet"
    )

    intent_context = {
        "session_check_in": "gathering how the learner is showing up today (energy, time, mindset)",
        "practice_setup": "setting up a practice/roleplay scenario",
        "verification": "checking understanding of a concept",
        "outcome_discovery": "discovering what the learner wants to achieve",
        "application_event": "capturing an upcoming real-world application",
    }.get(intent, "gathering information")

    return f"""Generate a brief follow-up question.

Context: {intent_context}
Already collected: {collected_summary}
Still need: {", ".join(missing_fields)}

Write ONE short, natural question to gather the missing info."""
