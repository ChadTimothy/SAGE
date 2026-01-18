"""Session-related MCP tools for SAGE.

These tools handle session lifecycle and conversation.
"""

import logging
from typing import Any

from sage.core.config import get_settings
from sage.dialogue.structured_output import SAGEResponse
from sage.graph.learning_graph import LearningGraph
from sage.graph.models import EnergyLevel, Session, SessionContext
from sage.orchestration.normalizer import InputModality
from sage.orchestration.orchestrator import SAGEOrchestrator

logger = logging.getLogger(__name__)


def _get_default_graph() -> LearningGraph:
    """Get default learning graph instance."""
    settings = get_settings()
    return LearningGraph(settings.db_path)


def _get_orchestrator(graph: LearningGraph) -> SAGEOrchestrator:
    """Create SAGE orchestrator with settings."""
    settings = get_settings()
    from openai import OpenAI

    llm_client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    return SAGEOrchestrator(
        graph=graph,
        llm_client=llm_client,
        extraction_model=settings.llm_model,
        ui_generation_model="grok-2",
    )


def _response_to_dict(response: SAGEResponse) -> dict[str, Any]:
    """Convert SAGEResponse to serializable dict."""
    gap = response.gap_identified
    proof = response.proof_earned

    return {
        "message": response.message,
        "mode": response.current_mode.value,
        "transition_to": response.transition_to.value if response.transition_to else None,
        "gap_identified": {
            "name": gap.name,
            "display_name": gap.display_name,
            "description": gap.description,
        } if gap else None,
        "proof_earned": {
            "concept_id": proof.concept_id,
            "demonstration_type": proof.demonstration_type,
            "evidence": proof.evidence,
        } if proof else None,
        "outcome_achieved": response.outcome_achieved,
    }


async def sage_start_session(
    learner_id: str,
    outcome_id: str | None = None,
    graph: LearningGraph | None = None,
) -> dict[str, Any]:
    """Start a new SAGE learning session.

    Creates a new session for the learner and returns the session ID
    along with an initial greeting.

    Args:
        learner_id: The learner's ID
        outcome_id: Optional outcome ID to continue working on
        graph: Optional LearningGraph instance (uses default if not provided)

    Returns:
        dict with:
            - session_id: The new session's ID
            - message: Initial greeting from SAGE
            - learner_name: The learner's name for personalization
    """
    if graph is None:
        graph = _get_default_graph()

    # Verify learner exists
    learner = graph.get_learner(learner_id)
    if not learner:
        return {
            "error": "Learner not found",
            "session_id": None,
        }

    # Create session
    session = Session(learner_id=learner_id, outcome_id=outcome_id)
    session = graph.create_session(session)

    # Update learner session count
    learner.total_sessions += 1
    graph.update_learner(learner)

    logger.info(f"Started MCP session {session.id} for learner {learner_id}")

    # Get learner name for personalization
    learner_name = learner.profile.name or "there"

    return {
        "session_id": session.id,
        "message": f"Hey {learner_name}! Ready to learn something today?",
        "learner_name": learner_name,
        "has_active_outcome": outcome_id is not None or learner.active_outcome_id is not None,
    }


async def sage_checkin(
    session_id: str,
    energy_level: str = "medium",
    time_available: str = "focused",
    mindset: str | None = None,
    setting: str | None = None,
    graph: LearningGraph | None = None,
) -> dict[str, Any]:
    """Complete the session check-in to personalize the learning experience.

    SAGE adapts its approach based on your current state.

    Args:
        session_id: Current session ID
        energy_level: Your energy level - "low", "medium", or "high"
        time_available: How much time you have - "quick" (15 min), "focused" (30 min), or "deep" (1+ hour)
        mindset: How you're feeling (optional, e.g., "stressed about deadline", "curious and relaxed")
        setting: Your environment (optional, e.g., "quiet office", "commuting")
        graph: Optional LearningGraph instance (uses default if not provided)

    Returns:
        dict with:
            - message: SAGE's response acknowledging your state
            - adaptations: How SAGE will adapt to your current context
    """
    if graph is None:
        graph = _get_default_graph()
    session = graph.get_session(session_id)

    if not session:
        return {"error": "Session not found"}

    # Build check-in context
    context_parts = []

    if energy_level:
        context_parts.append(f"energy level is {energy_level}")

    time_map = {
        "quick": "about 15 minutes",
        "focused": "about 30 minutes",
        "deep": "an hour or more",
    }
    if time_available:
        time_text = time_map.get(time_available, time_available)
        context_parts.append(f"I have {time_text}")

    if mindset:
        context_parts.append(f"feeling {mindset}")

    if setting:
        context_parts.append(f"I'm in {setting}")

    # Store context in session using proper SessionContext model
    energy_enum = None
    if energy_level:
        energy_map = {"low": EnergyLevel.LOW, "medium": EnergyLevel.MEDIUM, "high": EnergyLevel.HIGH}
        energy_enum = energy_map.get(energy_level.lower())

    session.context = SessionContext(
        energy=energy_enum,
        time_available=time_available,
        mindset=mindset,
        environment=setting,
    )
    graph.update_session(session)

    # Generate adaptive response
    adaptations = []
    if energy_level == "low":
        adaptations.append("Keeping things concise and practical")
    elif energy_level == "high":
        adaptations.append("Ready for deeper exploration")

    if time_available == "quick":
        adaptations.append("Focusing on quick wins")
    elif time_available == "deep":
        adaptations.append("We can dig into the details")

    if mindset and "stress" in mindset.lower():
        adaptations.append("Taking a gentler pace")

    context_summary = ", ".join(context_parts) if context_parts else "Ready to go"

    return {
        "message": f"Got it - {context_summary}. What would you like to work on?",
        "adaptations": adaptations,
        "session_context": session.context.model_dump() if session.context else None,
    }


async def sage_message(
    session_id: str,
    message: str,
    graph: LearningGraph | None = None,
) -> dict[str, Any]:
    """Send a message to SAGE and get a response.

    This is the main conversation tool - use it for:
    - Stating learning goals ("I want to learn X")
    - Answering SAGE's questions
    - Asking questions about a topic
    - Demonstrating understanding

    Args:
        session_id: Current session ID
        message: Your message to SAGE
        graph: Optional LearningGraph instance (uses default if not provided)

    Returns:
        dict with:
            - message: SAGE's response
            - mode: Current conversation mode (check_in, outcome_discovery, probing, teaching, verification)
            - gap_identified: Any learning gap discovered (name, description)
            - proof_earned: Any proof of understanding earned
            - outcome_achieved: Whether the learning goal has been achieved
    """
    if graph is None:
        graph = _get_default_graph()
    session = graph.get_session(session_id)

    if not session:
        return {"error": "Session not found"}

    orchestrator = _get_orchestrator(graph)

    try:
        # Process message through orchestrator (no streaming for MCP)
        response = await orchestrator.process_input(
            raw_input=message,
            source_modality=InputModality.CHAT,
            session_id=session_id,
        )

        return _response_to_dict(response)

    except Exception as e:
        logger.error(f"Error processing MCP message: {e}")
        return {
            "error": str(e),
            "message": "Sorry, I encountered an error. Could you try again?",
        }
