"""Session API routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from sage.graph.learning_graph import LearningGraph
from sage.graph.models import Session

from ..deps import get_graph
from ..schemas import SessionCreate, SessionEndRequest, SessionResponse

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _session_to_response(session: Session) -> SessionResponse:
    """Convert Session model to response schema."""
    return SessionResponse(
        id=session.id,
        learner_id=session.learner_id,
        outcome_id=session.outcome_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        message_count=len(session.messages),
    )


@router.post("", response_model=SessionResponse)
def create_session(
    data: SessionCreate,
    graph: LearningGraph = Depends(get_graph),
) -> SessionResponse:
    """Start a new session."""
    learner = graph.get_learner(data.learner_id)
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    session = Session(learner_id=data.learner_id, outcome_id=data.outcome_id)
    created = graph.create_session(session)

    learner.total_sessions += 1
    graph.update_learner(learner)

    return _session_to_response(created)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    graph: LearningGraph = Depends(get_graph),
) -> SessionResponse:
    """Get a session by ID."""
    session = graph.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_to_response(session)


@router.post("/{session_id}/end", response_model=SessionResponse)
def end_session(
    session_id: str,
    data: SessionEndRequest,
    graph: LearningGraph = Depends(get_graph),
) -> SessionResponse:
    """End a session."""
    session = graph.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.ended_at:
        raise HTTPException(status_code=400, detail="Session already ended")

    session.ended_at = datetime.utcnow()
    graph.update_session(session)

    return _session_to_response(session)
