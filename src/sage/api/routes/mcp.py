"""MCP-related REST endpoints for SAGE.

Provides REST endpoints for MCP tool operations.
These complement the full MCP server for simpler integrations.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from sage.mcp.auth import MCPAuthError, ensure_learner_exists, get_mcp_context
from sage.mcp.tools.session import sage_checkin, sage_message, sage_start_session
from sage.mcp.tools.progress import sage_graph, sage_progress
from sage.mcp.tools.practice import (
    sage_practice_feedback,
    sage_practice_scenario,
    sage_practice_start,
)
from ..deps import Graph, get_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


def _get_user_from_request(request: Request):
    """Extract and validate user from request headers."""
    try:
        headers = dict(request.headers)
        return get_mcp_context(headers)
    except MCPAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


# =============================================================================
# Request/Response Models
# =============================================================================


class StartSessionRequest(BaseModel):
    """Request to start a new session."""

    outcome_goal: str | None = None


class CheckinRequest(BaseModel):
    """Request for session check-in."""

    session_id: str
    energy: str = "medium"
    time_available: str = "focused"
    mindset: str | None = None


class MessageRequest(BaseModel):
    """Request to send a message."""

    session_id: str
    content: str


class PracticeStartRequest(BaseModel):
    """Request to start practice."""

    session_id: str
    concept_id: str | None = None
    difficulty: str = "realistic"


class PracticeRespondRequest(BaseModel):
    """Request to respond to practice scenario."""

    session_id: str
    practice_id: str
    response: str


class PracticeEndRequest(BaseModel):
    """Request to end practice."""

    session_id: str
    practice_id: str
    self_reflection: str | None = None


# =============================================================================
# Session Endpoints
# =============================================================================


@router.post("/session/start")
async def start_session(
    request: Request,
    data: StartSessionRequest,
    graph: Graph,
) -> dict[str, Any]:
    """Start a new SAGE learning session.

    Requires OAuth Bearer token in Authorization header.
    """
    user = _get_user_from_request(request)

    # Ensure learner exists (handles first-time users)
    ensure_learner_exists(user, graph)

    # Find outcome if goal specified
    outcome_id = None
    if data.outcome_goal:
        outcomes = graph.get_outcomes_by_learner(user.learner_id)
        for o in outcomes:
            if o.stated_goal.lower() == data.outcome_goal.lower():
                outcome_id = o.id
                break

    return await sage_start_session(user.learner_id, outcome_id, graph=graph)


@router.post("/session/checkin")
async def checkin(
    request: Request,
    data: CheckinRequest,
    graph: Graph,
) -> dict[str, Any]:
    """Complete the session check-in."""
    user = _get_user_from_request(request)

    # Verify session ownership
    session = graph.get_session(data.session_id)
    if not session or session.learner_id != user.learner_id:
        raise HTTPException(status_code=404, detail="Session not found")

    return await sage_checkin(
        data.session_id,
        data.energy,
        data.time_available,
        data.mindset,
        graph=graph,
    )


@router.post("/message")
async def send_message(
    request: Request,
    data: MessageRequest,
    graph: Graph,
) -> dict[str, Any]:
    """Send a message to SAGE.

    This is the main conversation endpoint for MCP integrations.
    Unlike the WebSocket chat endpoint, this returns the complete
    response without streaming.
    """
    user = _get_user_from_request(request)

    # Verify session ownership
    session = graph.get_session(data.session_id)
    if not session or session.learner_id != user.learner_id:
        raise HTTPException(status_code=404, detail="Session not found")

    return await sage_message(data.session_id, data.content, graph=graph)


# =============================================================================
# Progress Endpoints
# =============================================================================


@router.get("/progress")
async def get_progress(request: Request, graph: Graph) -> dict[str, Any]:
    """Get learning progress summary."""
    user = _get_user_from_request(request)
    return await sage_progress(user.learner_id, graph=graph)


@router.get("/graph")
async def get_knowledge_graph(
    request: Request,
    graph: Graph,
    include_proofs: bool = True,
) -> dict[str, Any]:
    """Get knowledge graph for visualization."""
    user = _get_user_from_request(request)
    return await sage_graph(user.learner_id, include_proofs, graph=graph)


# =============================================================================
# Practice Endpoints
# =============================================================================


@router.post("/practice/start")
async def start_practice(
    request: Request,
    data: PracticeStartRequest,
    graph: Graph,
) -> dict[str, Any]:
    """Start a practice session."""
    user = _get_user_from_request(request)

    # Verify session ownership
    session = graph.get_session(data.session_id)
    if not session or session.learner_id != user.learner_id:
        raise HTTPException(status_code=404, detail="Session not found")

    return await sage_practice_start(
        data.session_id,
        data.concept_id,
        data.difficulty,
        graph=graph,
    )


@router.post("/practice/respond")
async def practice_respond(
    request: Request,
    data: PracticeRespondRequest,
    graph: Graph,
) -> dict[str, Any]:
    """Respond to a practice scenario."""
    user = _get_user_from_request(request)

    # Verify session ownership
    session = graph.get_session(data.session_id)
    if not session or session.learner_id != user.learner_id:
        raise HTTPException(status_code=404, detail="Session not found")

    return await sage_practice_scenario(
        data.session_id,
        data.practice_id,
        data.response,
        graph=graph,
    )


@router.post("/practice/end")
async def end_practice(
    request: Request,
    data: PracticeEndRequest,
    graph: Graph,
) -> dict[str, Any]:
    """Complete a practice session."""
    user = _get_user_from_request(request)

    # Verify session ownership
    session = graph.get_session(data.session_id)
    if not session or session.learner_id != user.learner_id:
        raise HTTPException(status_code=404, detail="Session not found")

    return await sage_practice_feedback(
        data.session_id,
        data.practice_id,
        data.self_reflection,
        graph=graph,
    )
