"""Main conversation loop for SAGE.

This module implements the core conversation engine that:
1. Loads context at session start
2. Builds prompts for each turn
3. Calls the LLM and parses responses
4. Persists state changes
5. Manages mode transitions
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Optional

from openai import OpenAI

from sage.context.full_context import FullContext, FullContextLoader
from sage.context.persistence import (
    ApplicationDetected,
    ConnectionDiscovered,
    FollowupResponse,
    GapIdentified,
    ProofEarned,
    StateChange,
    TurnChanges,
    TurnPersistence,
)
from sage.context.turn_context import TurnContext, TurnContextBuilder
from sage.dialogue.modes import ModeManager
from sage.dialogue.prompt_builder import PromptBuilder, build_messages_for_llm
from sage.dialogue.state_detection import (
    get_prompt_instructions_for_detection,
)
from sage.dialogue.structured_output import (
    SAGEResponse,
    create_fallback_response,
    get_output_instructions,
    parse_sage_response,
    validate_response_consistency,
)
from sage.graph.learning_graph import LearningGraph
from sage.graph.models import (
    Concept,
    DialogueMode,
    Message,
    Session,
    SessionContext,
    SessionEndingState,
)


logger = logging.getLogger(__name__)


@dataclass
class ConversationConfig:
    """Configuration for the conversation engine."""

    # LLM settings
    model: str = "grok-2"  # Default model
    temperature: float = 0.7
    max_tokens: int = 2000

    # Conversation settings
    max_recent_messages: int = 15
    validate_responses: bool = True

    # Timeouts and retries
    max_retries: int = 2
    timeout_seconds: int = 60


class ConversationEngine:
    """The main SAGE conversation engine.

    Orchestrates the conversation loop, managing:
    - Context loading and building
    - Prompt construction
    - LLM calls
    - Response parsing and validation
    - State persistence
    """

    def __init__(
        self,
        graph: LearningGraph,
        llm_client: OpenAI,
        config: Optional[ConversationConfig] = None,
    ):
        """Initialize the conversation engine.

        Args:
            graph: The LearningGraph for data access
            llm_client: OpenAI-compatible client for LLM calls
            config: Optional configuration
        """
        self.graph = graph
        self.client = llm_client
        self.config = config or ConversationConfig()

        # Initialize components
        self.context_loader = FullContextLoader(graph)
        self.prompt_builder = PromptBuilder()
        self.mode_manager = ModeManager()
        self.persistence = TurnPersistence(graph)

        # Initialize gap finder and proof handler (lazy imports to avoid circular deps)
        from sage.gaps import create_gap_finder
        from sage.assessment import create_proof_handler
        self.gap_finder = create_gap_finder(graph)
        self.proof_handler = create_proof_handler(graph)

        # State
        self.full_context: Optional[FullContext] = None
        self.current_session: Optional[Session] = None
        self.current_mode: Optional[DialogueMode] = None
        self.current_concept: Optional[Concept] = None

    def start_session(
        self,
        learner_id: str,
        outcome_id: Optional[str] = None,
    ) -> tuple[Session, DialogueMode]:
        """Start a new conversation session.

        Loads context, creates session, and determines initial mode.

        Args:
            learner_id: The learner's ID
            outcome_id: Optional specific outcome to work on

        Returns:
            Tuple of (Session, initial DialogueMode)
        """
        # Load full context
        self.full_context = self.context_loader.load(learner_id)

        # Determine initial mode
        self.current_mode = self.mode_manager.determine_initial_mode(self.full_context)

        # Create session
        session = Session(
            learner_id=learner_id,
            outcome_id=outcome_id or (
                self.full_context.active_outcome.id
                if self.full_context.active_outcome else None
            ),
            started_at=datetime.utcnow(),
        )
        session = self.graph.create_session(session)
        self.current_session = session

        logger.info(
            f"Started session {session.id} for learner {learner_id} "
            f"in mode {self.current_mode}"
        )

        return session, self.current_mode

    def resume_session(self, session_id: str) -> tuple[Session, DialogueMode]:
        """Resume an existing conversation session.

        Loads context and session state for continuing a conversation.

        Args:
            session_id: The session ID to resume

        Returns:
            Tuple of (Session, current DialogueMode)

        Raises:
            ValueError: If session not found
        """
        session = self.graph.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        self.full_context = self.context_loader.load(session.learner_id)
        self.current_mode = self._get_mode_from_session(session)
        self.current_session = session

        logger.info(
            f"Resumed session {session.id} for learner {session.learner_id} "
            f"in mode {self.current_mode}"
        )

        return session, self.current_mode

    def _get_mode_from_session(self, session: Session) -> DialogueMode:
        """Extract the current mode from session history, or determine initial mode."""
        for msg in reversed(session.messages or []):
            if msg.role == "sage" and msg.mode:
                return DialogueMode(msg.mode)

        return self.mode_manager.determine_initial_mode(self.full_context)

    def _build_llm_messages(
        self,
        session_context: Optional[SessionContext] = None,
    ) -> tuple[TurnContext, list[dict[str, str]]]:
        """Build turn context and LLM messages for a conversation turn.

        Returns:
            Tuple of (TurnContext, messages for LLM)

        Raises:
            RuntimeError: If no session is active
        """
        if not self.current_session:
            raise RuntimeError("No active session. Call start_session first.")

        turn_context = self._build_turn_context(session_context)

        system_prompt = self.prompt_builder.build_system_prompt(turn_context)
        turn_prompt = self.prompt_builder.build_turn_prompt(turn_context)
        turn_prompt += f"\n\n---\n\n{get_output_instructions()}"
        turn_prompt += f"\n\n---\n\n{get_prompt_instructions_for_detection()}"

        return turn_context, build_messages_for_llm(system_prompt, turn_prompt, "")

    def _finalize_turn(
        self,
        user_message: str,
        response: SAGEResponse,
        session_context: Optional[SessionContext] = None,
    ) -> None:
        """Validate response, persist changes, and handle mode transitions."""
        if self.config.validate_responses:
            warnings = validate_response_consistency(response, self.current_mode)
            for warning in warnings:
                logger.warning(f"Response validation: {warning}")

        self._persist_turn(user_message, response, session_context)

        if response.transition_to:
            logger.info(
                f"Mode transition: {self.current_mode} -> {response.transition_to} "
                f"({response.transition_reason})"
            )
            if response.transition_to == DialogueMode.TEACHING and self.current_concept:
                self.gap_finder.start_teaching_gap(self.current_concept.id)
                logger.info(f"Started teaching gap: {self.current_concept.display_name}")

            self.current_mode = response.transition_to

    def process_turn(
        self,
        user_message: str,
        session_context: Optional[SessionContext] = None,
    ) -> SAGEResponse:
        """Process a single conversation turn.

        Args:
            user_message: The user's message
            session_context: Optional session context (Set/Setting/Intention)

        Returns:
            The SAGE response

        Raises:
            RuntimeError: If no session is active
        """
        _, messages = self._build_llm_messages(session_context)
        messages[-1]["content"] = user_message

        response = self._call_llm(messages)
        self._finalize_turn(user_message, response, session_context)

        return response

    async def process_turn_streaming(
        self,
        user_message: str,
        on_chunk: Callable[[str], Awaitable[None]],
        session_context: Optional[SessionContext] = None,
    ) -> SAGEResponse:
        """Process a conversation turn with streaming output.

        Args:
            user_message: The user's message
            on_chunk: Async callback to receive text chunks during streaming
            session_context: Optional session context (Set/Setting/Intention)

        Returns:
            The SAGE response after streaming completes

        Raises:
            RuntimeError: If no session is active
        """
        _, messages = self._build_llm_messages(session_context)
        messages[-1]["content"] = user_message

        response = await self._call_llm_streaming(messages, on_chunk)
        self._finalize_turn(user_message, response, session_context)

        return response

    def _build_turn_context(
        self,
        session_context: Optional[SessionContext] = None,
    ) -> TurnContext:
        """Build the context for this turn.

        Adds mode-specific hints for PROBE and TEACH modes.
        """
        builder = TurnContextBuilder(
            full_context=self.full_context,
            session=self.current_session,
            mode=self.current_mode,
        )

        if session_context:
            builder.with_session_context(session_context)

        if self.current_concept:
            builder.with_current_concept(self.current_concept)

        extra_hints = self._get_mode_specific_hints()
        if extra_hints:
            builder.with_extra_hints(extra_hints)

        return builder.build()

    def _get_mode_specific_hints(self) -> list[str]:
        """Get hints specific to the current dialogue mode."""
        if self.current_mode == DialogueMode.PROBING:
            probing_context = self.gap_finder.build_probing_context(self.full_context)
            hints = self.gap_finder.get_probing_prompt_hints(probing_context)
            return [hints] if hints else []

        if self.current_mode == DialogueMode.TEACHING and self.current_concept:
            connections = self.gap_finder.find_teaching_connections(
                concept_id=self.current_concept.id,
                learner_id=self.current_session.learner_id,
            )
            if connections:
                hints = self.gap_finder.get_connection_prompt_hints(connections)
                return [hints] if hints else []

        return []

    def _call_llm(
        self,
        messages: list[dict[str, str]],
    ) -> SAGEResponse:
        """Call the LLM and parse the response.

        Args:
            messages: The messages to send

        Returns:
            Parsed SAGEResponse
        """
        for attempt in range(self.config.max_retries + 1):
            try:
                # Make the API call
                completion = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    response_format={"type": "json_object"},
                )

                # Parse the response
                content = completion.choices[0].message.content
                if not content:
                    raise ValueError("Empty response from LLM")

                response_data = json.loads(content)
                return parse_sage_response(response_data)

            except Exception as e:
                logger.error(f"LLM call failed (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries:
                    # Return fallback response
                    return create_fallback_response(self.current_mode, e)

        # Should never reach here, but just in case
        return create_fallback_response(self.current_mode)

    async def _call_llm_streaming(
        self,
        messages: list[dict[str, str]],
        on_chunk: Callable[[str], Awaitable[None]],
    ) -> SAGEResponse:
        """Call the LLM with streaming, sending chunks via callback.

        Args:
            messages: The messages to send
            on_chunk: Async callback to receive text chunks

        Returns:
            Parsed SAGEResponse after stream completes
        """
        accumulated = ""

        for attempt in range(self.config.max_retries + 1):
            try:
                # Make streaming API call
                stream = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    response_format={"type": "json_object"},
                    stream=True,
                )

                # Stream chunks and accumulate
                accumulated = ""
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        accumulated += content
                        # Send raw chunk for UI feedback
                        await on_chunk(content)

                if not accumulated:
                    raise ValueError("Empty response from LLM")

                # Parse complete JSON
                response_data = json.loads(accumulated)
                return parse_sage_response(response_data)

            except Exception as e:
                logger.error(f"Streaming LLM call failed (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries:
                    return create_fallback_response(self.current_mode, e)

        return create_fallback_response(self.current_mode)

    def _persist_turn(
        self,
        user_message: str,
        response: SAGEResponse,
        session_context: Optional[SessionContext] = None,
    ) -> None:
        """Persist all changes from this turn.

        Args:
            user_message: The user's message
            response: The SAGE response
            session_context: Optional session context
        """
        # Build TurnChanges from SAGEResponse
        changes = TurnChanges(
            user_message=user_message,
            sage_message=response.message,
            sage_mode=response.current_mode,
            transition_to=response.transition_to,
            transition_reason=response.transition_reason,
            outcome_achieved=response.outcome_achieved,
            outcome_reasoning=response.outcome_reasoning,
            teaching_approach_used=response.teaching_approach_used,
        )

        # Map structured output models to persistence models
        if response.gap_identified:
            changes.gap_identified = GapIdentified(
                name=response.gap_identified.name,
                display_name=response.gap_identified.display_name,
                description=response.gap_identified.description,
                blocking_outcome_id=response.gap_identified.blocking_outcome_id,
            )

        if response.proof_earned:
            changes.proof_earned = ProofEarned(
                concept_id=response.proof_earned.concept_id,
                demonstration_type=response.proof_earned.demonstration_type,
                evidence=response.proof_earned.evidence,
                confidence=response.proof_earned.confidence,
                prompt=response.proof_earned.exchange.prompt,
                response=response.proof_earned.exchange.response,
                analysis=response.proof_earned.exchange.analysis,
            )

        if response.connection_discovered:
            changes.connection_discovered = ConnectionDiscovered(
                from_concept_id=response.connection_discovered.from_concept_id,
                to_concept_id=response.connection_discovered.to_concept_id,
                relationship=response.connection_discovered.relationship,
                strength=response.connection_discovered.strength,
                used_in_teaching=response.connection_discovered.used_in_teaching,
            )

        if response.application_detected:
            changes.application_detected = ApplicationDetected(
                context=response.application_detected.context,
                concept_ids=response.application_detected.concept_ids,
                planned_date=(
                    datetime.combine(response.application_detected.planned_date, datetime.min.time())
                    if response.application_detected.planned_date else None
                ),
                stakes=response.application_detected.stakes,
            )

        if response.followup_response:
            changes.followup_response = FollowupResponse(
                event_id=response.followup_response.event_id,
                outcome_result=response.followup_response.outcome_result,
                what_worked=response.followup_response.what_worked,
                what_struggled=response.followup_response.what_struggled,
                gaps_revealed=response.followup_response.gaps_revealed,
                insights=response.followup_response.insights,
            )

        if response.state_change_detected:
            changes.state_change_detected = StateChange(
                what_changed=response.state_change_detected.what_changed,
                detected_from=response.state_change_detected.detected_from,
                recommended_adaptation=response.state_change_detected.recommended_adaptation,
            )
            changes.context_update = response.context_update or session_context

        # Process gaps and connections via GapFinder
        if response.gap_identified or response.connection_discovered:
            gap_result = self.gap_finder.process_response(
                response=response,
                learner_id=self.current_session.learner_id,
                outcome_id=self.current_session.outcome_id,
                session_id=self.current_session.id,
            )
            # Track the newly created concept as current
            if gap_result.gap_created:
                self.current_concept = gap_result.gap_created
                logger.info(f"Set current concept to: {self.current_concept.display_name}")

        # Process proof via ProofHandler
        if response.proof_earned:
            proof = self.proof_handler.process_proof_earned(
                proof_earned=response.proof_earned,
                learner_id=self.current_session.learner_id,
                session_id=self.current_session.id,
            )
            if proof:
                logger.info(f"Proof created for concept: {response.proof_earned.concept_id}")
                # Mark gap as understood if it was the current concept
                if self.current_concept and self.current_concept.id == response.proof_earned.concept_id:
                    self.gap_finder.mark_gap_understood(self.current_concept.id)
                    self.current_concept = None  # Clear after proof earned

        # Persist turn changes (messages, state updates)
        self.current_session = self.persistence.persist(
            self.current_session,
            changes,
        )

    def _determine_next_step(self) -> Optional[str]:
        """Determine what the next step would be for session continuity."""
        if not self.current_mode:
            return None

        concept_name = self.current_concept.name if self.current_concept else None

        # Templates for each mode. Use {concept} placeholder for concept-specific messages.
        mode_templates = {
            DialogueMode.TEACHING: "Continue teaching {concept}" if concept_name else None,
            DialogueMode.PROBING: "Continue probing for gaps",
            DialogueMode.VERIFICATION: f"Complete verification of {concept_name}" if concept_name else None,
            DialogueMode.OUTCOME_DISCOVERY: "Continue exploring learning goals",
            DialogueMode.FRAMING: "Continue framing the territory",
            DialogueMode.OUTCOME_CHECK: "Check if outcome is achieved",
        }

        template = mode_templates.get(self.current_mode)
        if template and "{concept}" in template:
            return template.format(concept=concept_name)
        return template

    def end_session(self) -> Session:
        """End the current session.

        Returns:
            The completed session
        """
        if not self.current_session:
            raise RuntimeError("No active session to end.")

        # Capture ending state for cross-session continuity
        self.current_session.ending_state = SessionEndingState(
            mode=self.current_mode.value if self.current_mode else "unknown",
            current_focus=self.current_concept.name if self.current_concept else None,
            next_step=self._determine_next_step(),
        )

        # Update session end time
        self.current_session.ended_at = datetime.utcnow()
        self.graph.update_session(self.current_session)

        # Update learner stats
        learner = self.graph.get_learner(self.current_session.learner_id)
        if learner:
            learner.total_sessions += 1
            learner.last_session_at = datetime.utcnow()
            self.graph.update_learner(learner)

        logger.info(f"Ended session {self.current_session.id}")

        session = self.current_session
        self.current_session = None
        self.full_context = None
        self.current_mode = None
        self.current_concept = None

        return session


def create_conversation_engine(
    graph: LearningGraph,
    api_key: str,
    base_url: str = "https://api.x.ai/v1",
    model: str = "grok-2",
) -> ConversationEngine:
    """Create a conversation engine with default configuration.

    Args:
        graph: The LearningGraph for data access
        api_key: API key for the LLM provider
        base_url: Base URL for the LLM API
        model: Model to use

    Returns:
        Configured ConversationEngine
    """
    client = OpenAI(api_key=api_key, base_url=base_url)
    config = ConversationConfig(model=model)
    return ConversationEngine(graph, client, config)


# =============================================================================
# Simple Conversation Functions
# =============================================================================


async def run_conversation(
    engine: ConversationEngine,
    learner_id: str,
    message_handler: Callable[[str], str],
    on_response: Optional[Callable[[SAGEResponse], None]] = None,
) -> Session:
    """Run a conversation loop until completion.

    This is a simple helper for running a conversation programmatically.

    Args:
        engine: The conversation engine
        learner_id: The learner's ID
        message_handler: Function that takes SAGE's message and returns user's response
        on_response: Optional callback for each response

    Returns:
        The completed session
    """
    session, mode = engine.start_session(learner_id)

    try:
        while True:
            # Get user message
            user_message = message_handler(
                "Session started. How are you showing up today?"
                if not engine.current_session.messages
                else engine.current_session.messages[-1].content
            )

            if not user_message or user_message.lower() in ["quit", "exit", "bye"]:
                break

            # Process turn
            response = engine.process_turn(user_message)

            if on_response:
                on_response(response)

            # Check if outcome achieved
            if response.outcome_achieved:
                logger.info("Outcome achieved! Session can end.")
                break

    finally:
        session = engine.end_session()

    return session
