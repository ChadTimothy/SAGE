"""WebSocket chat handler for streaming responses."""

import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from sage.core.config import get_settings
from sage.dialogue.conversation import ConversationEngine
from sage.graph.learning_graph import LearningGraph

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


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


def _create_engine(
    graph: LearningGraph, session_id: str
) -> Optional[ConversationEngine]:
    """Create conversation engine for session."""
    session = graph.get_session(session_id)
    if not session:
        return None

    settings = get_settings()
    return ConversationEngine(
        graph=graph,
        learner_id=session.learner_id,
        session_id=session_id,
        outcome_id=session.outcome_id,
        llm_base_url=settings.llm_base_url,
        llm_api_key=settings.llm_api_key,
        llm_model=settings.llm_model,
    )


def _response_to_dict(response) -> dict:
    """Convert SAGEResponse to JSON-serializable dict."""
    gap = response.gap_identified
    proof = response.proof_earned

    return {
        "message": response.message,
        "mode": response.mode.value,
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
    }


@router.websocket("/api/chat/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
) -> None:
    """WebSocket endpoint for streaming chat."""
    settings = get_settings()
    graph = LearningGraph(settings.database_url)

    session = graph.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    await manager.connect(session_id, websocket)
    logger.info(f"WebSocket connected for session {session_id}")

    try:
        engine = _create_engine(graph, session_id)
        if not engine:
            await manager.send_error(session_id, "Failed to initialize engine")
            return

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")
            content = data.get("content", "")

            if msg_type == "voice" and data.get("audio") and not content:
                await manager.send_error(
                    session_id, "Voice transcription not yet implemented"
                )
                continue

            if not content:
                await manager.send_error(session_id, "Empty message")
                continue

            try:
                response = engine.process_turn(content)
                await manager.send_complete(session_id, _response_to_dict(response))
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await manager.send_error(session_id, str(e))

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.send_error(session_id, str(e))
    finally:
        manager.disconnect(session_id)
