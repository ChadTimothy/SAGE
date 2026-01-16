"""Common test fixtures for SAGE tests."""

import jwt
import pytest
from fastapi.testclient import TestClient

from sage.api.deps import get_graph
from sage.api.main import app
from sage.core.config import get_settings
from sage.graph.learning_graph import LearningGraph
from sage.graph.models import (
    AgeGroup,
    Learner,
    LearnerProfile,
    Session,
    SkillLevel,
)


# Test secret for JWT tokens
TEST_SECRET = "test-secret-key-for-testing-only"


def create_test_token(user_id: str, learner_id: str) -> str:
    """Create a JWT token for testing."""
    payload = {
        "sub": user_id,
        "learner_id": learner_id,
        "email": "test@example.com",
        "name": "Test User",
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


@pytest.fixture
def test_graph(tmp_path):
    """Create test graph with temp database."""
    db_path = tmp_path / "test.db"
    return LearningGraph(str(db_path))


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    monkeypatch.setenv("NEXTAUTH_SECRET", TEST_SECRET)
    # Clear cached settings to pick up new env var
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(test_graph, mock_settings):
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


@pytest.fixture
def auth_headers(test_learner):
    """Create auth headers with valid JWT token."""
    token = create_test_token(test_learner.id, test_learner.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_token(test_learner):
    """Create a JWT token for testing."""
    return create_test_token(test_learner.id, test_learner.id)
