"""MCP authentication for SAGE.

Validates OAuth tokens from ChatGPT/Claude and handles
user creation/linking.
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

from jose import JWTError, jwt

from sage.core.config import get_settings
from sage.graph.learning_graph import LearningGraph
from sage.graph.models import Learner, LearnerProfile

logger = logging.getLogger(__name__)


@dataclass
class MCPUser:
    """Authenticated MCP user context."""

    user_id: str
    learner_id: str
    email: str | None = None
    name: str | None = None
    source: str = "mcp"


class MCPAuthError(Exception):
    """Authentication error for MCP requests."""

    pass


def _hash_email(email: str) -> str:
    """Create a deterministic hash from email for learner_id."""
    return hashlib.sha256(email.encode()).hexdigest()[:12]


def verify_mcp_token(token: str) -> MCPUser:
    """Verify an MCP OAuth token and extract user context.

    Args:
        token: Bearer token from Authorization header

    Returns:
        MCPUser with validated user information

    Raises:
        MCPAuthError: If token is invalid or missing required claims
    """
    settings = get_settings()
    signing_key = settings.oauth_signing_key or settings.nextauth_secret

    if not signing_key:
        raise MCPAuthError("OAuth signing key not configured")

    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError as e:
        logger.error(f"MCP token validation failed: {e}")
        raise MCPAuthError(f"Invalid token: {e}")

    if "sub" not in payload:
        raise MCPAuthError("Token missing user ID (sub)")

    # Get learner_id from token or generate from email
    learner_id = payload.get("learner_id")
    if not learner_id:
        # Generate from email if available
        email = payload.get("email")
        if email:
            learner_id = f"learner_{_hash_email(email)}"
        else:
            # Use user_id hash as fallback
            learner_id = f"learner_{_hash_email(payload['sub'])}"

    return MCPUser(
        user_id=payload["sub"],
        learner_id=learner_id,
        email=payload.get("email"),
        name=payload.get("name"),
        source=payload.get("source", "chatgpt"),
    )


def ensure_learner_exists(user: MCPUser, graph: LearningGraph) -> Learner:
    """Ensure a learner exists for the MCP user, creating if needed.

    This handles the account linking gap - OAuth generates a hash-based
    learner_id that may not exist in the database. We create a new
    learner on first access.

    Args:
        user: Authenticated MCP user
        graph: Learning graph for database access

    Returns:
        Learner instance (existing or newly created)
    """
    learner = graph.get_learner(user.learner_id)

    if learner:
        return learner

    # Create new learner for first-time MCP user
    logger.info(f"Creating new learner for MCP user: {user.user_id}")

    profile = LearnerProfile(
        name=user.name,
        # Note: LearnerProfile doesn't have preferred_name field
        # The name field stores the display name
    )

    learner = Learner(
        id=user.learner_id,
        profile=profile,
    )

    return graph.create_learner(learner)


def get_mcp_context(headers: dict[str, Any]) -> MCPUser:
    """Extract MCP user context from request headers.

    ChatGPT attaches OAuth token via Authorization: Bearer header.

    Args:
        headers: Request headers dict

    Returns:
        MCPUser with validated user info

    Raises:
        MCPAuthError: If no valid token found
    """
    auth_header = headers.get("authorization", headers.get("Authorization", ""))

    if not auth_header.startswith("Bearer "):
        raise MCPAuthError("Missing or invalid Authorization header")

    token = auth_header[7:]  # Strip "Bearer " prefix
    return verify_mcp_token(token)
