"""Session API routes."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sage.graph.models import Session
from sage.orchestration.normalizer import InputModality
from sage.orchestration.session_state import (
    UnifiedSessionState,
    session_state_manager,
)

from ..deps import Graph, User, Verifier
from ..schemas import SessionCreate, SessionEndRequest, SessionResponse


class ModalityPreferenceRequest(BaseModel):
    """Request to update modality preference."""

    modality: InputModality


class MergeDataRequest(BaseModel):
    """Request to merge collected data into session state."""

    data: dict[str, Any]

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
    user: User,
    graph: Graph,
    verifier: Verifier,
) -> SessionResponse:
    """Start a new session."""
    # Verify user owns the learner
    verifier.verify_learner(user, data.learner_id)

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
    user: User,
    graph: Graph,
    verifier: Verifier,
) -> SessionResponse:
    """Get a session by ID."""
    verifier.verify_session(user, session_id)
    session = graph.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_to_response(session)


@router.post("/{session_id}/end", response_model=SessionResponse)
def end_session(
    session_id: str,
    data: SessionEndRequest,
    user: User,
    graph: Graph,
    verifier: Verifier,
) -> SessionResponse:
    """End a session."""
    verifier.verify_session(user, session_id)
    session = graph.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.ended_at:
        raise HTTPException(status_code=400, detail="Session already ended")

    session.ended_at = datetime.utcnow()
    graph.update_session(session)

    return _session_to_response(session)


# ============================================================================
# Cross-Modality State Synchronization Endpoints
# Part of #81 - Cross-Modality State Synchronization
# ============================================================================


@router.get("/{session_id}/state", response_model=UnifiedSessionState)
def get_session_state(
    session_id: str,
    user: User,
    verifier: Verifier,
) -> UnifiedSessionState:
    """Get current unified session state for frontend sync.

    Returns the complete state including:
    - Modality preference
    - Pending data collection state
    - Check-in progress
    - Message history with modality tags

    This enables the frontend to restore state after page refresh
    or when switching between modalities.
    """
    verifier.verify_session(user, session_id)
    return session_state_manager.get_or_create(session_id)


@router.post("/{session_id}/modality")
def set_modality_preference(
    session_id: str,
    request: ModalityPreferenceRequest,
    user: User,
    verifier: Verifier,
) -> dict[str, str]:
    """Update user's modality preference.

    Called when user explicitly switches between voice and UI modes.
    """
    verifier.verify_session(user, session_id)
    state = session_state_manager.get_or_create(session_id)
    state.set_modality_preference(request.modality)
    session_state_manager.update(session_id, state)

    return {"status": "ok", "modality": request.modality.value}


@router.post("/{session_id}/merge-data")
def merge_collected_data(
    session_id: str,
    request: MergeDataRequest,
    user: User,
    verifier: Verifier,
) -> UnifiedSessionState:
    """Merge collected data from one modality into the unified state.

    Called when partial data is collected via voice or UI to ensure
    it's available when switching to the other modality.
    """
    verifier.verify_session(user, session_id)
    state = session_state_manager.get_or_create(session_id)
    state.merge_collected_data(request.data)
    session_state_manager.update(session_id, state)

    return state


@router.get("/{session_id}/prefill/{intent}")
def get_prefill_data(
    session_id: str,
    intent: str,
    user: User,
    verifier: Verifier,
) -> dict[str, Any]:
    """Get data to prefill UI forms based on intent.

    When a user switches from voice to UI, this provides the
    already-collected data to prefill the form.
    """
    verifier.verify_session(user, session_id)
    state = session_state_manager.get(session_id)
    if not state:
        return {}

    return state.get_prefill_data_for_intent(intent)


@router.delete("/{session_id}/state")
def clear_session_state(
    session_id: str,
    user: User,
    verifier: Verifier,
) -> dict[str, str]:
    """Clear session state (for logout or session end)."""
    verifier.verify_session(user, session_id)
    session_state_manager.delete(session_id)
    return {"status": "ok"}
