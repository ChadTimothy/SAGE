"""WebSocket chat handler for streaming responses."""

import logging
from typing import Any, Optional, Union

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from sage.core.config import get_settings
from sage.dialogue.structured_output import ExtendedSAGEResponse, SAGEResponse
from sage.graph.learning_graph import LearningGraph
from sage.orchestration.normalizer import InputModality
from sage.orchestration.orchestrator import SAGEOrchestrator

from ..auth import get_current_user_ws

logger = logging.getLogger(__name__)


# =============================================================================
# WebSocket Message Models
# =============================================================================


router = APIRouter(tags=["chat"])


class WSIncomingMessage(BaseModel):
    """WebSocket message from client."""

    type: str = "text"
    content: Optional[str] = None
    form_id: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    is_voice: bool = False


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept and store connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        """Remove connection."""
        self.active_connections.pop(session_id, None)

    async def send_chunk(self, session_id: str, content: str):
        """Send a streaming chunk."""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(
                {"type": "chunk", "content": content}
            )

    async def send_complete(self, session_id: str, response: dict):
        """Send complete response."""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(
                {"type": "complete", "response": response}
            )

    async def send_error(self, session_id: str, message: str):
        """Send error message."""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(
                {"type": "error", "message": message}
            )


manager = ConnectionManager()


def _create_orchestrator(graph: LearningGraph) -> SAGEOrchestrator:
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


def _response_to_dict(response: Union[SAGEResponse, ExtendedSAGEResponse]) -> dict:
    """Convert SAGEResponse or ExtendedSAGEResponse to JSON-serializable dict."""
    gap = response.gap_identified
    proof = response.proof_earned

    result = {
        "message": response.message,
        "mode": response.current_mode.value,
        "transition_to": response.transition_to.value if response.transition_to else None,
        "transition_reason": response.transition_reason,
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
        "ui_tree": None,
        "voice_hints": None,
        "pending_data_request": None,
        "ui_purpose": None,
        "estimated_interaction_time": None,
        "graph_filter_update": None,
    }

    # Add extended fields if present (ExtendedSAGEResponse)
    for field in ("ui_tree", "voice_hints", "pending_data_request"):
        value = getattr(response, field, None)
        if value:
            result[field] = value.model_dump()

    for field in ("ui_purpose", "estimated_interaction_time"):
        if hasattr(response, field):
            result[field] = getattr(response, field)

    return result


@router.websocket("/api/chat/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
) -> None:
    """WebSocket endpoint for streaming chat.

    Authentication via query parameter: ?token=xxx
    """
    settings = get_settings()
    graph = LearningGraph(settings.db_path)

    # Authenticate user from query param token
    try:
        user = await get_current_user_ws(websocket)
    except Exception:
        return  # Connection already closed by get_current_user_ws

    # Verify session ownership
    session = graph.get_session(session_id)

    if session:
        # Verify user owns this session
        if session.learner_id != user.learner_id:
            await websocket.close(code=4003, reason="Access denied: not your session")
            return
    else:
        # Auto-create session for the authenticated user's learner
        from sage.graph.models import Session

        session = Session(id=session_id, learner_id=user.learner_id)
        session = graph.create_session(session)
        logger.info(f"Auto-created session {session_id} for learner {user.learner_id}")

    await manager.connect(session_id, websocket)
    logger.info(f"WebSocket connected for session {session_id}")

    orchestrator = _create_orchestrator(graph)

    try:
        await _handle_messages(session_id, orchestrator)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.send_error(session_id, str(e))
    finally:
        manager.disconnect(session_id)


def _parse_incoming_message(data: dict) -> WSIncomingMessage:
    """Parse incoming WebSocket data into a message object."""
    try:
        return WSIncomingMessage.model_validate(data)
    except Exception:
        # Fallback for legacy message format
        return WSIncomingMessage(
            type=data.get("type", "text"),
            content=data.get("content", ""),
            is_voice=data.get("is_voice", False),
        )


async def _handle_messages(session_id: str, orchestrator: SAGEOrchestrator) -> None:
    """Process incoming messages in the WebSocket loop."""
    websocket = manager.active_connections.get(session_id)
    if not websocket:
        return

    while True:
        data = await websocket.receive_json()
        msg = _parse_incoming_message(data)

        if msg.type == "form_submission":
            await _process_form_submission(session_id, orchestrator, msg)
        elif msg.content:
            # Determine modality from message flags
            modality = InputModality.VOICE if msg.is_voice else InputModality.CHAT
            await _process_message(session_id, orchestrator, msg.content, modality)
        else:
            await manager.send_error(session_id, "Empty message")


async def _stream_response(
    session_id: str,
    orchestrator: SAGEOrchestrator,
    content: str,
    modality: InputModality,
    *,
    form_id: str | None = None,
    form_data: dict[str, Any] | None = None,
) -> None:
    """Process content through the orchestrator and stream the response."""
    async def on_chunk(chunk: str) -> None:
        await manager.send_chunk(session_id, chunk)

    response = await orchestrator.process_input(
        raw_input=content,
        source_modality=modality,
        session_id=session_id,
        form_id=form_id,
        form_data=form_data,
        on_chunk=on_chunk,
    )
    await manager.send_complete(session_id, _response_to_dict(response))


async def _process_message(
    session_id: str,
    orchestrator: SAGEOrchestrator,
    content: str,
    modality: InputModality,
) -> None:
    """Process a text or voice message and send response via streaming."""
    try:
        await _stream_response(session_id, orchestrator, content, modality)
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await manager.send_error(session_id, str(e))


async def _process_form_submission(
    session_id: str,
    orchestrator: SAGEOrchestrator,
    msg: WSIncomingMessage,
) -> None:
    """Process a form submission through the orchestrator."""
    if not msg.form_id or not msg.data:
        await manager.send_error(session_id, "Invalid form submission: missing form_id or data")
        return

    try:
        # Route through orchestrator with FORM modality
        # The orchestrator handles form normalization and validation
        await _stream_response(
            session_id,
            orchestrator,
            content="",  # Empty for form submissions
            modality=InputModality.FORM,
            form_id=msg.form_id,
            form_data=msg.data,
        )
    except Exception as e:
        logger.error(f"Error processing form submission: {e}")
        await manager.send_error(session_id, str(e))


def _energy_level_to_text(level: Any) -> str:
    """Convert energy level value to descriptive text."""
    if not isinstance(level, (int, float)):
        return str(level)
    if level < 40:
        return "low"
    if level < 70:
        return "medium"
    return "high"


def _form_data_to_message(form_id: str, data: dict[str, Any]) -> str:
    """Convert form data to a natural language message."""
    form_id_lower = form_id.lower()

    # Session check-in form
    if "check_in" in form_id_lower or "check-in" in form_id_lower:
        time_map = {
            "quick": "about 15 minutes",
            "focused": "about 30 minutes",
            "deep": "an hour or more",
        }
        parts = []
        if "timeAvailable" in data:
            time_text = time_map.get(data["timeAvailable"], data["timeAvailable"])
            parts.append(f"I have {time_text}")
        if "energyLevel" in data:
            parts.append(f"my energy is {_energy_level_to_text(data['energyLevel'])}")
        if data.get("mindset"):
            parts.append(f"and {data['mindset']}")
        return ". ".join(parts) if parts else "Starting session"

    # Verification/quiz form
    if "verification" in form_id_lower or "quiz" in form_id_lower:
        if "answer" in data:
            return f"My answer is: {data['answer']}"
        return str(data)

    # Generic form - convert to key-value description
    parts = [f"{key}: {value}" for key, value in data.items() if value]
    return "; ".join(parts) if parts else "Form submitted"
