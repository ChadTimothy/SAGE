"""Tests for SAGE API endpoints.

Note: Fixtures for test_graph, client, test_learner, test_session, and auth_headers
are provided by conftest.py
"""

import pytest

from tests.conftest import create_test_token


class TestRootEndpoints:
    """Test root and health endpoints."""

    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "SAGE API"
        assert "version" in data

    def test_health(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestLearnerEndpoints:
    """Test learner API endpoints."""

    def test_create_learner(self, client, test_learner, auth_headers):
        """Test creating a learner (deprecated endpoint returns user's learner)."""
        response = client.post(
            "/api/learners",
            headers=auth_headers,
            json={
                "name": "New Learner",
                "age_group": "adult",
                "skill_level": "beginner",
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Deprecated endpoint returns user's existing learner, not a new one
        assert data["id"] == test_learner.id
        assert "name" in data

    def test_get_learner_not_found(self, client, auth_headers):
        """Test getting non-existent learner returns 403 (not owner)."""
        response = client.get("/api/learners/nonexistent-id", headers=auth_headers)
        # Returns 403 because user is not owner of that learner
        assert response.status_code == 403

    def test_get_learner(self, client, test_learner, auth_headers):
        """Test getting an existing learner."""
        response = client.get(f"/api/learners/{test_learner.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_learner.id
        assert data["name"] == "Test Learner"

    def test_get_learner_state(self, client, test_learner, auth_headers):
        """Test getting learner state."""
        response = client.get(f"/api/learners/{test_learner.id}/state", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "learner" in data
        assert data["learner"]["id"] == test_learner.id
        assert "recent_concepts" in data
        assert "recent_proofs" in data

    def test_get_learner_outcomes(self, client, test_learner, auth_headers):
        """Test getting learner outcomes."""
        response = client.get(f"/api/learners/{test_learner.id}/outcomes", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_get_learner_graph(self, client, test_learner, auth_headers):
        """Test getting learner knowledge graph."""
        response = client.get(f"/api/learners/{test_learner.id}/graph", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        # Should have at least the learner node
        assert len(data["nodes"]) >= 1


class TestSessionEndpoints:
    """Test session API endpoints."""

    def test_create_session(self, client, test_learner, auth_headers):
        """Test creating a session."""
        response = client.post(
            "/api/sessions",
            headers=auth_headers,
            json={"learner_id": test_learner.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["learner_id"] == test_learner.id
        assert "id" in data
        assert "started_at" in data

    def test_create_session_invalid_learner(self, client, auth_headers):
        """Test creating session with invalid learner returns 403."""
        response = client.post(
            "/api/sessions",
            headers=auth_headers,
            json={"learner_id": "nonexistent"},
        )
        # 403 because the user doesn't own 'nonexistent' learner
        assert response.status_code == 403

    def test_get_session(self, client, test_session, auth_headers):
        """Test getting a session."""
        response = client.get(f"/api/sessions/{test_session.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == test_session.id

    def test_end_session(self, client, test_session, auth_headers):
        """Test ending a session."""
        response = client.post(
            f"/api/sessions/{test_session.id}/end",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ended_at"] is not None

    def test_end_session_already_ended(self, client, test_graph, test_learner, auth_headers):
        """Test ending already ended session."""
        from sage.graph.models import Session

        session = test_graph.create_session(Session(learner_id=test_learner.id))

        # End session twice
        client.post(f"/api/sessions/{session.id}/end", headers=auth_headers, json={})
        response = client.post(f"/api/sessions/{session.id}/end", headers=auth_headers, json={})
        assert response.status_code == 400


class TestWebSocketChat:
    """Test WebSocket chat endpoint."""

    def test_websocket_invalid_session(self, client, auth_token):
        """Test WebSocket with invalid session."""
        with pytest.raises(Exception):
            # Should fail to connect - invalid session but valid auth
            with client.websocket_connect(f"/api/chat/invalid-session?token={auth_token}"):
                pass

    def test_websocket_no_auth(self, client):
        """Test WebSocket without auth token."""
        with pytest.raises(Exception):
            # Should fail without token
            with client.websocket_connect("/api/chat/some-session"):
                pass


class TestWebSocketProtocolExtension:
    """Test WebSocket protocol extension for voice/UI parity (#84)."""

    def test_ws_incoming_message_text(self):
        """Test WSIncomingMessage with text type."""
        from sage.api.routes.chat import WSIncomingMessage

        msg = WSIncomingMessage(type="text", content="Hello", is_voice=False)
        assert msg.type == "text"
        assert msg.content == "Hello"
        assert msg.is_voice is False
        assert msg.form_id is None
        assert msg.data is None

    def test_ws_incoming_message_form_submission(self):
        """Test WSIncomingMessage with form_submission type."""
        from sage.api.routes.chat import WSIncomingMessage

        msg = WSIncomingMessage(
            type="form_submission",
            form_id="check-in-123",
            data={"energyLevel": 50, "mindset": "focused"},
        )
        assert msg.type == "form_submission"
        assert msg.form_id == "check-in-123"
        assert msg.data == {"energyLevel": 50, "mindset": "focused"}
        assert msg.content is None

    def test_ws_incoming_message_defaults(self):
        """Test WSIncomingMessage default values."""
        from sage.api.routes.chat import WSIncomingMessage

        msg = WSIncomingMessage()
        assert msg.type == "text"
        assert msg.is_voice is False

    def test_form_data_to_message_check_in(self):
        """Test _form_data_to_message with check-in form."""
        from sage.api.routes.chat import _form_data_to_message

        # Full check-in data
        result = _form_data_to_message("check-in-abc123", {
            "timeAvailable": "focused",
            "energyLevel": 75,
            "mindset": "excited about the topic",
        })
        assert "about 30 minutes" in result
        assert "high" in result
        assert "excited about the topic" in result

    def test_form_data_to_message_check_in_low_energy(self):
        """Test _form_data_to_message with low energy."""
        from sage.api.routes.chat import _form_data_to_message

        result = _form_data_to_message("session_check_in", {
            "energyLevel": 20,
        })
        assert "low" in result

    def test_form_data_to_message_check_in_medium_energy(self):
        """Test _form_data_to_message with medium energy."""
        from sage.api.routes.chat import _form_data_to_message

        result = _form_data_to_message("check_in_form", {
            "energyLevel": 50,
        })
        assert "medium" in result

    def test_form_data_to_message_verification(self):
        """Test _form_data_to_message with verification form."""
        from sage.api.routes.chat import _form_data_to_message

        result = _form_data_to_message("verification-quiz-123", {
            "answer": "Start high with room to come down",
        })
        assert "My answer is:" in result
        assert "Start high with room to come down" in result

    def test_form_data_to_message_generic(self):
        """Test _form_data_to_message with generic form."""
        from sage.api.routes.chat import _form_data_to_message

        result = _form_data_to_message("custom-form", {
            "name": "John",
            "topic": "pricing",
        })
        assert "name: John" in result
        assert "topic: pricing" in result

    def test_form_data_to_message_empty(self):
        """Test _form_data_to_message with empty data."""
        from sage.api.routes.chat import _form_data_to_message

        result = _form_data_to_message("check-in", {})
        assert result == "Starting session"

        result = _form_data_to_message("generic", {})
        assert result == "Form submitted"

    def test_response_to_dict_includes_ui_fields(self):
        """Test _response_to_dict includes voice/UI parity fields."""
        from sage.api.routes.chat import _response_to_dict
        from sage.dialogue.structured_output import SAGEResponse
        from sage.graph.models import DialogueMode

        response = SAGEResponse(
            message="Hello!",
            current_mode=DialogueMode.CHECK_IN,
        )

        result = _response_to_dict(response)

        # Should have all the standard fields
        assert result["message"] == "Hello!"
        assert result["mode"] == "check_in"

        # Should have voice/UI parity fields (null for base SAGEResponse)
        assert "ui_tree" in result
        assert "voice_hints" in result
        assert "pending_data_request" in result
        assert "ui_purpose" in result
        assert "estimated_interaction_time" in result

    def test_response_to_dict_with_extended_response(self):
        """Test _response_to_dict with ExtendedSAGEResponse."""
        from sage.api.routes.chat import _response_to_dict
        from sage.dialogue.structured_output import (
            ExtendedSAGEResponse,
            UITreeNode,
            VoiceHints,
            PendingDataRequest,
        )
        from sage.graph.models import DialogueMode

        ui_tree = UITreeNode(
            component="Stack",
            props={"gap": 4},
            children=[
                UITreeNode(component="Text", props={"content": "Hello"}),
            ],
        )
        voice_hints = VoiceHints(
            voice_fallback="Hello, how are you?",
            emphasis=["Hello"],
            tone="friendly",
        )
        pending = PendingDataRequest(
            intent="check_in",
            collected_data={"energyLevel": 50},
            missing_fields=["mindset"],
        )

        response = ExtendedSAGEResponse(
            message="Hello!",
            current_mode=DialogueMode.CHECK_IN,
            ui_tree=ui_tree,
            voice_hints=voice_hints,
            pending_data_request=pending,
            ui_purpose="Gather session context",
            estimated_interaction_time=30,
        )

        result = _response_to_dict(response)

        # Check extended fields are serialized
        assert result["ui_tree"] is not None
        assert result["ui_tree"]["component"] == "Stack"
        assert len(result["ui_tree"]["children"]) == 1

        assert result["voice_hints"] is not None
        assert result["voice_hints"]["voice_fallback"] == "Hello, how are you?"
        assert result["voice_hints"]["tone"] == "friendly"

        assert result["pending_data_request"] is not None
        assert result["pending_data_request"]["intent"] == "check_in"
        assert result["pending_data_request"]["missing_fields"] == ["mindset"]

        assert result["ui_purpose"] == "Gather session context"
        assert result["estimated_interaction_time"] == 30
