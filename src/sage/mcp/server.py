"""SAGE MCP Server implementation using FastMCP.

Exposes SAGE functionality as MCP tools for ChatGPT Apps
and Claude Desktop integration.
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from sage.core.config import get_settings
from sage.graph.learning_graph import LearningGraph

from .auth import MCPAuthError, MCPUser, ensure_learner_exists, get_mcp_context
from .tools.session import sage_checkin, sage_message, sage_start_session
from .tools.progress import sage_graph, sage_progress
from .tools.practice import (
    sage_practice_feedback,
    sage_practice_scenario,
    sage_practice_start,
)

logger = logging.getLogger(__name__)

# Create the MCP server instance
mcp = FastMCP(
    "SAGE",
    instructions="AI tutor that teaches through conversation. Learn by doing, not by curriculum.",
)


def _get_graph() -> LearningGraph:
    """Get learning graph instance."""
    settings = get_settings()
    return LearningGraph(settings.db_path)


# =============================================================================
# Session Tools
# =============================================================================


@mcp.tool()
async def start_session(
    outcome_goal: str | None = None,
) -> dict[str, Any]:
    """Start a new SAGE learning session.

    Begin a conversation with SAGE to learn something new.
    SAGE adapts to your current state and goals.

    Args:
        outcome_goal: Optional learning goal to work towards

    Returns:
        Session ID and initial greeting
    """
    # Get authenticated user from context
    try:
        user = get_mcp_context(mcp.request_context.get("headers", {}))
    except MCPAuthError as e:
        return {"error": str(e), "authenticated": False}

    # Ensure learner exists
    graph = _get_graph()
    ensure_learner_exists(user, graph)

    # Find or create outcome if goal specified
    outcome_id = None
    if outcome_goal:
        # Check for existing outcome
        outcomes = graph.get_outcomes_by_learner(user.learner_id)
        for o in outcomes:
            if o.stated_goal.lower() == outcome_goal.lower():
                outcome_id = o.id
                break

    return await sage_start_session(user.learner_id, outcome_id)


@mcp.tool()
async def checkin(
    session_id: str,
    energy: str = "medium",
    time_available: str = "focused",
    mindset: str | None = None,
) -> dict[str, Any]:
    """Complete the session check-in.

    Tell SAGE how you're doing so it can adapt to you.

    Args:
        session_id: Your current session ID
        energy: Your energy level - "low", "medium", or "high"
        time_available: Time you have - "quick" (15min), "focused" (30min), or "deep" (1hr+)
        mindset: How you're feeling (optional)

    Returns:
        Acknowledgment and how SAGE will adapt
    """
    # Verify session ownership
    try:
        user = get_mcp_context(mcp.request_context.get("headers", {}))
    except MCPAuthError as e:
        return {"error": str(e)}

    graph = _get_graph()
    session = graph.get_session(session_id)
    if session and session.learner_id != user.learner_id:
        return {"error": "Session not found or access denied"}

    return await sage_checkin(session_id, energy, time_available, mindset)


@mcp.tool()
async def message(
    session_id: str,
    content: str,
) -> dict[str, Any]:
    """Send a message to SAGE.

    The main conversation tool for learning:
    - State what you want to learn
    - Answer SAGE's questions
    - Ask questions about topics
    - Demonstrate your understanding

    Args:
        session_id: Your current session ID
        content: Your message to SAGE

    Returns:
        SAGE's response with learning progress
    """
    # Verify session ownership
    try:
        user = get_mcp_context(mcp.request_context.get("headers", {}))
    except MCPAuthError as e:
        return {"error": str(e)}

    graph = _get_graph()
    session = graph.get_session(session_id)
    if session and session.learner_id != user.learner_id:
        return {"error": "Session not found or access denied"}

    return await sage_message(session_id, content)


# =============================================================================
# Progress Tools
# =============================================================================


@mcp.tool()
async def get_progress() -> dict[str, Any]:
    """Get your learning progress summary.

    See your:
    - Total sessions and proofs earned
    - Active learning goal
    - Recent concepts learned
    - Outcomes completed

    Returns:
        Progress statistics and recent activity
    """
    try:
        user = get_mcp_context(mcp.request_context.get("headers", {}))
    except MCPAuthError as e:
        return {"error": str(e)}

    return await sage_progress(user.learner_id)


@mcp.tool()
async def get_knowledge_graph(
    include_proofs: bool = True,
) -> dict[str, Any]:
    """Get your knowledge graph.

    Visualize what you've learned and how concepts connect.

    Args:
        include_proofs: Include proof nodes (default: True)

    Returns:
        Graph nodes and edges for visualization
    """
    try:
        user = get_mcp_context(mcp.request_context.get("headers", {}))
    except MCPAuthError as e:
        return {"error": str(e)}

    return await sage_graph(user.learner_id, include_proofs)


# =============================================================================
# Practice Tools
# =============================================================================


@mcp.tool()
async def start_practice(
    session_id: str,
    concept_id: str | None = None,
    difficulty: str = "realistic",
) -> dict[str, Any]:
    """Start a practice session.

    Practice applying what you've learned in realistic scenarios.

    Args:
        session_id: Your current session ID
        concept_id: Specific concept to practice (optional)
        difficulty: "gentle", "realistic", or "challenging"

    Returns:
        Practice scenario to respond to
    """
    try:
        user = get_mcp_context(mcp.request_context.get("headers", {}))
    except MCPAuthError as e:
        return {"error": str(e)}

    graph = _get_graph()
    session = graph.get_session(session_id)
    if session and session.learner_id != user.learner_id:
        return {"error": "Session not found or access denied"}

    return await sage_practice_start(session_id, concept_id, difficulty)


@mcp.tool()
async def practice_respond(
    session_id: str,
    practice_id: str,
    response: str,
) -> dict[str, Any]:
    """Respond to a practice scenario.

    Submit your response to get feedback.

    Args:
        session_id: Your current session ID
        practice_id: The practice session ID
        response: Your response to the scenario

    Returns:
        Feedback on your response
    """
    try:
        user = get_mcp_context(mcp.request_context.get("headers", {}))
    except MCPAuthError as e:
        return {"error": str(e)}

    graph = _get_graph()
    session = graph.get_session(session_id)
    if session and session.learner_id != user.learner_id:
        return {"error": "Session not found or access denied"}

    return await sage_practice_scenario(session_id, practice_id, response)


@mcp.tool()
async def end_practice(
    session_id: str,
    practice_id: str,
    self_reflection: str | None = None,
) -> dict[str, Any]:
    """Complete a practice session.

    End practice and get comprehensive feedback.

    Args:
        session_id: Your current session ID
        practice_id: The practice session ID
        self_reflection: Optional self-assessment

    Returns:
        Final feedback and next steps
    """
    try:
        user = get_mcp_context(mcp.request_context.get("headers", {}))
    except MCPAuthError as e:
        return {"error": str(e)}

    graph = _get_graph()
    session = graph.get_session(session_id)
    if session and session.learner_id != user.learner_id:
        return {"error": "Session not found or access denied"}

    return await sage_practice_feedback(session_id, practice_id, self_reflection)


# =============================================================================
# Server Creation
# =============================================================================


def create_mcp_server() -> FastMCP:
    """Create and return the MCP server instance.

    Used for mounting to Starlette/FastAPI apps.
    """
    return mcp


def run_stdio():
    """Run the MCP server in stdio mode.

    Used for Claude Desktop integration via local proxy.
    """
    mcp.run(transport="stdio")


def run_http(host: str = "0.0.0.0", port: int = 8001):
    """Run the MCP server in HTTP mode.

    Used for ChatGPT Apps and remote clients.
    """
    mcp.run(transport="streamable-http", host=host, port=port)


if __name__ == "__main__":
    # Default to stdio for local testing
    run_stdio()
