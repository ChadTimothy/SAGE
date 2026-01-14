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
