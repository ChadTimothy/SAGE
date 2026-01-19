"""Tests for MCP server and REST endpoints.

Tests cover:
- MCP authentication (OAuth JWT tokens)
- MCP REST endpoints for session, progress, and practice
- User creation/linking on first access
- Session ownership verification
"""

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from sage.core.config import get_settings
from sage.graph.models import Concept, ConceptStatus, PracticeScenario, Session, SessionType
from sage.mcp.auth import (
    MCPAuthError,
    MCPUser,
    ensure_learner_exists,
    get_mcp_context,
    verify_mcp_token,
)

# Test secret (same as conftest.py)
TEST_SECRET = "test-secret-key-for-testing-only"


def create_oauth_token(
    user_id: str,
    learner_id: str | None = None,
    email: str | None = None,
    expires_in: int = 3600,
) -> str:
    """Create an OAuth 2.1 JWT token for testing."""
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "http://localhost:8000",
        "sub": user_id,
        "aud": "test-client",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        "source": "chatgpt",
    }
    if learner_id:
        payload["learner_id"] = learner_id
    if email:
        payload["email"] = email

    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


class TestMCPAuthentication:
    """Tests for MCP authentication layer."""

    def test_verify_valid_token(self, mock_settings):
        """Verify a valid OAuth token."""
        token = create_oauth_token("user123", "learner_abc")
        user = verify_mcp_token(token)

        assert user.user_id == "user123"
        assert user.learner_id == "learner_abc"
        assert user.source == "chatgpt"

    def test_verify_token_generates_learner_id_from_email(self, mock_settings):
        """Generate learner_id from email if not in token."""
        token = create_oauth_token("user123", email="test@example.com")
        user = verify_mcp_token(token)

        assert user.user_id == "user123"
        assert user.learner_id.startswith("learner_")
        assert user.email == "test@example.com"

    def test_verify_token_generates_learner_id_from_user_id(self, mock_settings):
        """Generate learner_id from user_id if no email."""
        token = create_oauth_token("user123")
        user = verify_mcp_token(token)

        assert user.user_id == "user123"
        assert user.learner_id.startswith("learner_")

    def test_verify_expired_token_fails(self, mock_settings):
        """Expired tokens should fail verification."""
        token = create_oauth_token("user123", expires_in=-100)

        with pytest.raises(MCPAuthError, match="Invalid token"):
            verify_mcp_token(token)

    def test_verify_invalid_token_fails(self, mock_settings):
        """Invalid tokens should fail verification."""
        with pytest.raises(MCPAuthError, match="Invalid token"):
            verify_mcp_token("invalid.token.here")

    def test_get_mcp_context_from_headers(self, mock_settings):
        """Extract user from Authorization header."""
        token = create_oauth_token("user123", "learner_abc")
        headers = {"Authorization": f"Bearer {token}"}

        user = get_mcp_context(headers)
        assert user.user_id == "user123"
        assert user.learner_id == "learner_abc"

    def test_get_mcp_context_lowercase_authorization(self, mock_settings):
        """Handle lowercase authorization header."""
        token = create_oauth_token("user123", "learner_abc")
        headers = {"authorization": f"Bearer {token}"}

        user = get_mcp_context(headers)
        assert user.user_id == "user123"

    def test_get_mcp_context_missing_header_fails(self, mock_settings):
        """Missing Authorization header should fail."""
        with pytest.raises(MCPAuthError, match="Missing or invalid Authorization"):
            get_mcp_context({})

    def test_get_mcp_context_invalid_format_fails(self, mock_settings):
        """Non-Bearer format should fail."""
        with pytest.raises(MCPAuthError, match="Missing or invalid Authorization"):
            get_mcp_context({"Authorization": "Basic abc123"})


class TestMCPUserCreation:
    """Tests for user creation/linking on first MCP access."""

    def test_ensure_learner_exists_returns_existing(self, test_graph, test_learner, mock_settings):
        """Return existing learner without creating new one."""
        user = MCPUser(
            user_id="test-user",
            learner_id=test_learner.id,
            email="test@example.com",
            name="Test User",
        )

        result = ensure_learner_exists(user, test_graph)

        assert result.id == test_learner.id
        # Verify it's the same learner (name matches original)
        assert result.profile.name == test_learner.profile.name

    def test_ensure_learner_creates_new_for_new_user(self, test_graph, mock_settings):
        """Create new learner for first-time MCP user."""
        user = MCPUser(
            user_id="new-chatgpt-user",
            learner_id="learner_abc123",
            email="newuser@example.com",
            name="New User",
        )

        result = ensure_learner_exists(user, test_graph)

        assert result.id == "learner_abc123"
        assert result.profile.name == "New User"
        # Verify learner was actually created
        learner = test_graph.get_learner("learner_abc123")
        assert learner is not None
        assert learner.profile.name == "New User"

    def test_ensure_learner_sets_name(self, test_graph, mock_settings):
        """Set name from MCP user info."""
        user = MCPUser(
            user_id="new-user",
            learner_id="learner_xyz",
            name="John Smith",
        )

        result = ensure_learner_exists(user, test_graph)

        assert result.profile.name == "John Smith"


class TestMCPRestEndpoints:
    """Tests for MCP REST API endpoints."""

    def test_start_session_creates_session(self, client, test_graph, mock_settings):
        """Start session creates new session and returns greeting."""
        # Create OAuth token for a new user
        token = create_oauth_token("mcp-user-1", "learner_mcp1", "mcp@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/mcp/session/start",
            json={},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "message" in data
        assert data["session_id"] is not None

        # Verify session was created
        session = test_graph.get_session(data["session_id"])
        assert session is not None
        assert session.learner_id == "learner_mcp1"

    def test_start_session_with_goal(self, client, test_graph, mock_settings):
        """Start session with a learning goal."""
        token = create_oauth_token("mcp-user-2", "learner_mcp2")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/mcp/session/start",
            json={"outcome_goal": "Learn Python basics"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data

    def test_checkin_updates_session_context(self, client, test_graph, test_learner, mock_settings):
        """Check-in updates session context."""
        # Create session for test learner
        session = Session(learner_id=test_learner.id)
        session = test_graph.create_session(session)

        # Create token for the test learner
        token = create_oauth_token(test_learner.id, test_learner.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/mcp/session/checkin",
            json={
                "session_id": session.id,
                "energy": "high",
                "time_available": "deep",
                "mindset": "excited to learn",
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "adaptations" in data
        assert "session_context" in data
        assert data["session_context"]["energy"] == "high"

    def test_checkin_rejects_wrong_session(self, client, test_graph, test_learner, other_learner, mock_settings):
        """Check-in rejects access to other user's session."""
        # Create session for other learner
        session = Session(learner_id=other_learner.id)
        session = test_graph.create_session(session)

        # Try to check in with test_learner's token
        token = create_oauth_token(test_learner.id, test_learner.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/mcp/session/checkin",
            json={"session_id": session.id},
            headers=headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_message_sends_to_sage(self, client, test_graph, test_learner, mock_settings, monkeypatch):
        """Send message to SAGE and get response."""
        # Create session
        session = Session(learner_id=test_learner.id)
        session = test_graph.create_session(session)

        token = create_oauth_token(test_learner.id, test_learner.id)
        headers = {"Authorization": f"Bearer {token}"}

        # Mock the orchestrator to avoid LLM calls
        async def mock_process_input(*args, **kwargs):
            from sage.dialogue.modes import DialogueMode
            from sage.dialogue.structured_output import SAGEResponse

            return SAGEResponse(
                message="I'm here to help you learn!",
                current_mode=DialogueMode.OUTCOME_DISCOVERY,
            )

        monkeypatch.setattr(
            "sage.orchestration.orchestrator.SAGEOrchestrator.process_input",
            mock_process_input,
        )

        response = client.post(
            "/api/mcp/message",
            json={
                "session_id": session.id,
                "content": "I want to learn Python",
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "mode" in data

    def test_get_progress(self, client, test_graph, test_learner, mock_settings):
        """Get learner progress summary."""
        token = create_oauth_token(test_learner.id, test_learner.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/mcp/progress", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_sessions" in data
        assert "total_proofs" in data
        assert "recent_concepts" in data

    def test_get_knowledge_graph(self, client, test_graph, test_learner, mock_settings):
        """Get knowledge graph for visualization."""
        token = create_oauth_token(test_learner.id, test_learner.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/mcp/graph", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert data["node_count"] >= 1  # At least learner node

    def test_start_practice(self, client, test_graph, test_learner, mock_settings):
        """Start a practice session."""
        # Create session and concept
        session = Session(learner_id=test_learner.id)
        session = test_graph.create_session(session)

        concept = Concept(
            learner_id=test_learner.id,
            name="python_basics",
            display_name="Python Basics",
            status=ConceptStatus.IDENTIFIED,
        )
        concept = test_graph.create_concept_obj(concept)

        token = create_oauth_token(test_learner.id, test_learner.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/mcp/practice/start",
            json={"session_id": session.id, "concept_id": concept.id},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "practice_id" in data
        assert "scenario" in data
        assert "concept" in data

    def test_practice_respond(self, client, test_graph, test_learner, mock_settings):
        """Respond to practice scenario."""
        # Create session with practice state
        session = Session(learner_id=test_learner.id)
        session = test_graph.create_session(session)

        concept = Concept(
            learner_id=test_learner.id,
            name="python_basics",
            display_name="Python Basics",
            status=ConceptStatus.IDENTIFIED,
        )
        concept = test_graph.create_concept_obj(concept)

        # Store practice state in session using proper model
        session.session_type = SessionType.PRACTICE
        session.practice_scenario = PracticeScenario(
            scenario_id="practice_test123",
            title=f"Practice: {concept.display_name}",
            description="Test practice scenario",
            sage_role="Coach",
            user_role="Learner",
            related_concepts=[concept.id],
        )
        test_graph.update_session(session)

        token = create_oauth_token(test_learner.id, test_learner.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/mcp/practice/respond",
            json={
                "session_id": session.id,
                "practice_id": "practice_test123",
                "response": "I would use a for loop to iterate over the list",
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "feedback" in data
        assert "score" in data
        assert "areas_good" in data

    def test_end_practice(self, client, test_graph, test_learner, mock_settings):
        """Complete a practice session."""
        session = Session(learner_id=test_learner.id)
        session = test_graph.create_session(session)

        concept = Concept(
            learner_id=test_learner.id,
            name="python_basics",
            display_name="Python Basics",
            status=ConceptStatus.IDENTIFIED,
        )
        concept = test_graph.create_concept_obj(concept)

        session.session_type = SessionType.PRACTICE
        session.practice_scenario = PracticeScenario(
            scenario_id="practice_end123",
            title=f"Practice: {concept.display_name}",
            description="Test practice scenario",
            sage_role="Coach",
            user_role="Learner",
            related_concepts=[concept.id],
        )
        test_graph.update_session(session)

        token = create_oauth_token(test_learner.id, test_learner.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/mcp/practice/end",
            json={
                "session_id": session.id,
                "practice_id": "practice_end123",
                "self_reflection": "I learned a lot!",
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["practice_complete"] is True
        assert "summary" in data
        assert "key_learnings" in data


class TestMCPAuthorization:
    """Tests for MCP authorization checks."""

    def test_unauthorized_request_returns_401(self, client, mock_settings):
        """Requests without token return 401."""
        response = client.post(
            "/api/mcp/session/start",
            json={},
        )
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client, mock_settings):
        """Invalid tokens return 401."""
        response = client.post(
            "/api/mcp/session/start",
            json={},
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_session_access_denied_for_wrong_user(self, client, test_graph, test_learner, mock_settings):
        """Users cannot access other users' sessions."""
        # Create session for test_learner
        session = Session(learner_id=test_learner.id)
        session = test_graph.create_session(session)

        # Try to access with a different user's token
        other_token = create_oauth_token("other-user", "other_learner_id")
        headers = {"Authorization": f"Bearer {other_token}"}

        response = client.post(
            "/api/mcp/message",
            json={"session_id": session.id, "content": "test"},
            headers=headers,
        )

        assert response.status_code == 404
