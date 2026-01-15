"""Tests for SAGE API endpoints."""

import pytest
from fastapi.testclient import TestClient

from sage.api.deps import get_graph
from sage.api.main import app
from sage.graph.learning_graph import LearningGraph
from sage.graph.models import (
    AgeGroup,
    Learner,
    LearnerProfile,
    Session,
    SkillLevel,
)


@pytest.fixture
def test_graph(tmp_path):
    """Create test graph with temp database."""
    db_path = tmp_path / "test.db"
    return LearningGraph(str(db_path))


@pytest.fixture
def client(test_graph):
    """Create test client with overridden dependencies."""
    def override_get_graph():
        yield test_graph

    app.dependency_overrides[get_graph] = override_get_graph
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_learner(test_graph):
    """Create test learner."""
    profile = LearnerProfile(
        name="Test Learner",
        age_group=AgeGroup.ADULT,
        skill_level=SkillLevel.BEGINNER,
    )
    learner = Learner(profile=profile)
    return test_graph.create_learner(learner)


@pytest.fixture
def test_session(test_graph, test_learner):
    """Create test session."""
    session = Session(learner_id=test_learner.id)
    return test_graph.create_session(session)


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

    def test_create_learner(self, client):
        """Test creating a learner."""
        response = client.post(
            "/api/learners",
            json={
                "name": "New Learner",
                "age_group": "adult",
                "skill_level": "beginner",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Learner"
        assert data["age_group"] == "adult"
        assert data["skill_level"] == "beginner"
        assert "id" in data

    def test_get_learner_not_found(self, client):
        """Test getting non-existent learner."""
        response = client.get("/api/learners/nonexistent-id")
        assert response.status_code == 404

    def test_get_learner(self, client):
        """Test getting an existing learner."""
        # First create a learner
        create_response = client.post(
            "/api/learners",
            json={"name": "Test Learner", "age_group": "teen", "skill_level": "intermediate"},
        )
        learner_id = create_response.json()["id"]

        # Then get it
        response = client.get(f"/api/learners/{learner_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == learner_id
        assert data["name"] == "Test Learner"

    def test_get_learner_state(self, client):
        """Test getting learner state."""
        # Create a learner
        create_response = client.post(
            "/api/learners",
            json={"name": "State Test", "age_group": "adult", "skill_level": "beginner"},
        )
        learner_id = create_response.json()["id"]

        # Get state
        response = client.get(f"/api/learners/{learner_id}/state")
        assert response.status_code == 200
        data = response.json()
        assert "learner" in data
        assert data["learner"]["id"] == learner_id
        assert "recent_concepts" in data
        assert "recent_proofs" in data

    def test_get_learner_outcomes(self, client):
        """Test getting learner outcomes."""
        # Create a learner
        create_response = client.post(
            "/api/learners",
            json={"name": "Outcomes Test", "age_group": "adult", "skill_level": "beginner"},
        )
        learner_id = create_response.json()["id"]

        # Get outcomes (should be empty initially)
        response = client.get(f"/api/learners/{learner_id}/outcomes")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_learner_graph(self, client):
        """Test getting learner knowledge graph."""
        # Create a learner
        create_response = client.post(
            "/api/learners",
            json={"name": "Graph Test", "age_group": "adult", "skill_level": "beginner"},
        )
        learner_id = create_response.json()["id"]

        # Get graph
        response = client.get(f"/api/learners/{learner_id}/graph")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        # Should have at least the learner node
        assert len(data["nodes"]) >= 1


class TestSessionEndpoints:
    """Test session API endpoints."""

    def test_create_session(self, client):
        """Test creating a session."""
        # First create a learner
        learner_response = client.post(
            "/api/learners",
            json={"name": "Session Test", "age_group": "adult", "skill_level": "beginner"},
        )
        learner_id = learner_response.json()["id"]

        # Create session
        response = client.post(
            "/api/sessions",
            json={"learner_id": learner_id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["learner_id"] == learner_id
        assert "id" in data
        assert "started_at" in data

    def test_create_session_invalid_learner(self, client):
        """Test creating session with invalid learner."""
        response = client.post(
            "/api/sessions",
            json={"learner_id": "nonexistent"},
        )
        assert response.status_code == 404

    def test_get_session(self, client):
        """Test getting a session."""
        # Create learner and session
        learner_response = client.post(
            "/api/learners",
            json={"name": "Get Session Test", "age_group": "adult", "skill_level": "beginner"},
        )
        learner_id = learner_response.json()["id"]

        session_response = client.post(
            "/api/sessions",
            json={"learner_id": learner_id},
        )
        session_id = session_response.json()["id"]

        # Get session
        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        assert response.json()["id"] == session_id

    def test_end_session(self, client):
        """Test ending a session."""
        # Create learner and session
        learner_response = client.post(
            "/api/learners",
            json={"name": "End Session Test", "age_group": "adult", "skill_level": "beginner"},
        )
        learner_id = learner_response.json()["id"]

        session_response = client.post(
            "/api/sessions",
            json={"learner_id": learner_id},
        )
        session_id = session_response.json()["id"]

        # End session
        response = client.post(f"/api/sessions/{session_id}/end", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["ended_at"] is not None

    def test_end_session_already_ended(self, client):
        """Test ending already ended session."""
        # Create learner and session
        learner_response = client.post(
            "/api/learners",
            json={"name": "Double End Test", "age_group": "adult", "skill_level": "beginner"},
        )
        learner_id = learner_response.json()["id"]

        session_response = client.post(
            "/api/sessions",
            json={"learner_id": learner_id},
        )
        session_id = session_response.json()["id"]

        # End session twice
        client.post(f"/api/sessions/{session_id}/end", json={})
        response = client.post(f"/api/sessions/{session_id}/end", json={})
        assert response.status_code == 400


class TestWebSocketChat:
    """Test WebSocket chat endpoint."""

    def test_websocket_invalid_session(self, client):
        """Test WebSocket with invalid session."""
        with pytest.raises(Exception):
            # Should fail to connect
            with client.websocket_connect("/api/chat/invalid-session"):
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
