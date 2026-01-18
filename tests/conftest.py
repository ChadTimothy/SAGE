"""Common test fixtures for SAGE tests."""

import json
import pytest
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from jose.jwe import encrypt as jwe_encrypt
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


# Test secret for JWT tokens (must be at least 32 bytes for JWE)
TEST_SECRET = "test-secret-key-for-testing-only"


def _derive_test_key(secret: str) -> bytes:
    """Derive encryption key using HKDF (matches NextAuth v4)."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes for A256GCM
        salt=b"",  # Empty salt for NextAuth v4
        info=b"NextAuth.js Generated Encryption Key",
    )
    return hkdf.derive(secret.encode("utf-8"))


def create_test_token(user_id: str, learner_id: str) -> str:
    """Create a JWE encrypted token for testing (matches NextAuth format)."""
    payload = {
        "sub": user_id,
        "learner_id": learner_id,
        "email": "test@example.com",
        "name": "Test User",
    }
    # Derive key using HKDF (same as NextAuth v4 and our backend)
    derived_key = _derive_test_key(TEST_SECRET)
    # Encrypt as JWE (same format NextAuth uses)
    return jwe_encrypt(
        json.dumps(payload).encode("utf-8"),
        derived_key,
    ).decode("utf-8")


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


def create_learner_in_graph(
    graph: LearningGraph,
    name: str = "Test Learner",
    age_group: AgeGroup = AgeGroup.ADULT,
    skill_level: SkillLevel = SkillLevel.BEGINNER,
) -> Learner:
    """Create a learner in the graph with the given attributes."""
    profile = LearnerProfile(
        name=name,
        age_group=age_group,
        skill_level=skill_level,
    )
    learner = Learner(profile=profile)
    return graph.create_learner(learner)


@pytest.fixture
def test_learner(test_graph):
    """Create test learner."""
    return create_learner_in_graph(test_graph)


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


@pytest.fixture
def other_learner(test_graph):
    """Create a second learner for ownership tests."""
    return create_learner_in_graph(test_graph, name="Other Learner")


@pytest.fixture
def other_auth_headers(other_learner):
    """Create auth headers for a different user (for ownership tests)."""
    token = create_test_token(other_learner.id, other_learner.id)
    return {"Authorization": f"Bearer {token}"}
