"""Tests for practice mode API endpoints and models.

Note: Common fixtures (test_graph, client, test_learner, auth_headers) come from conftest.py.
"""

import pytest
from unittest.mock import MagicMock, patch

from sage.graph.models import (
    Message,
    PracticeFeedback,
    PracticeScenario,
    Session,
    SessionType,
)
from tests.conftest import create_test_token


# =============================================================================
# Practice-specific Fixtures
# =============================================================================


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI response."""
    mock_choice = MagicMock()
    mock_choice.message.content = "Hello, I'm here to discuss your proposal."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


@pytest.fixture
def mock_feedback_response():
    """Create a mock feedback response from OpenAI."""
    mock_choice = MagicMock()
    mock_choice.message.content = '''```json
{
    "positives": ["Clear communication", "Good questions"],
    "improvements": ["Be more assertive", "Ask about budget earlier"],
    "summary": "Good practice session with room for improvement.",
    "revealed_gaps": ["negotiation tactics"]
}
```'''
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


@pytest.fixture
def mock_hint_response():
    """Create a mock hint response."""
    mock_choice = MagicMock()
    mock_choice.message.content = "Try addressing their concern directly."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


@pytest.fixture
def practice_scenario():
    """Create a test practice scenario."""
    return PracticeScenario(
        scenario_id="test-scenario-1",
        title="Pricing Negotiation",
        description="Practice negotiating your freelance rates",
        sage_role="Skeptical Client",
        user_role="Freelancer",
        related_concepts=["pricing", "negotiation"],
    )


@pytest.fixture
def practice_session(test_graph, test_learner, practice_scenario):
    """Create a test practice session."""
    session = Session(
        learner_id=test_learner.id,
        session_type=SessionType.PRACTICE,
        practice_scenario=practice_scenario,
        messages=[
            Message(role="sage", content="Hi, I got your proposal. Can we talk pricing?", mode="practice")
        ],
    )
    return test_graph.create_session(session)


@pytest.fixture
def learning_session(test_graph, test_learner):
    """Create a regular learning session (not practice)."""
    session = Session(
        learner_id=test_learner.id,
        session_type=SessionType.LEARNING,
    )
    return test_graph.create_session(session)


# =============================================================================
# Model Tests
# =============================================================================


class TestPracticeScenarioModel:
    """Test PracticeScenario model."""

    def test_create_scenario(self):
        """Test creating a practice scenario."""
        scenario = PracticeScenario(
            scenario_id="test-1",
            title="Test Scenario",
            sage_role="Client",
            user_role="Consultant",
        )
        assert scenario.scenario_id == "test-1"
        assert scenario.title == "Test Scenario"
        assert scenario.sage_role == "Client"
        assert scenario.user_role == "Consultant"
        assert scenario.description is None
        assert scenario.related_concepts == []

    def test_scenario_with_all_fields(self):
        """Test scenario with all optional fields."""
        scenario = PracticeScenario(
            scenario_id="test-2",
            title="Full Scenario",
            description="A complete test scenario",
            sage_role="Manager",
            user_role="Team Lead",
            related_concepts=["leadership", "communication"],
        )
        assert scenario.description == "A complete test scenario"
        assert len(scenario.related_concepts) == 2

    def test_scenario_serialization(self):
        """Test scenario JSON round-trip."""
        scenario = PracticeScenario(
            scenario_id="test-3",
            title="Serialization Test",
            sage_role="Investor",
            user_role="Founder",
        )
        json_str = scenario.model_dump_json()
        restored = PracticeScenario.model_validate_json(json_str)
        assert restored.scenario_id == scenario.scenario_id
        assert restored.title == scenario.title


class TestPracticeFeedbackModel:
    """Test PracticeFeedback model."""

    def test_create_feedback(self):
        """Test creating practice feedback."""
        feedback = PracticeFeedback(
            positives=["Good opening", "Clear questions"],
            improvements=["Be more direct"],
            summary="Overall good performance.",
        )
        assert len(feedback.positives) == 2
        assert len(feedback.improvements) == 1
        assert feedback.summary == "Overall good performance."
        assert feedback.revealed_gaps == []

    def test_feedback_with_gaps(self):
        """Test feedback with revealed gaps."""
        feedback = PracticeFeedback(
            positives=["Engaged well"],
            improvements=["Work on objection handling"],
            summary="Practice revealed some knowledge gaps.",
            revealed_gaps=["objection handling", "closing techniques"],
        )
        assert len(feedback.revealed_gaps) == 2

    def test_feedback_defaults(self):
        """Test feedback with defaults."""
        feedback = PracticeFeedback()
        assert feedback.positives == []
        assert feedback.improvements == []
        assert feedback.summary == ""
        assert feedback.revealed_gaps == []


class TestSessionWithPractice:
    """Test Session model with practice fields."""

    def test_session_practice_type(self, test_graph, test_learner, practice_scenario):
        """Test creating a practice session."""
        session = Session(
            learner_id=test_learner.id,
            session_type=SessionType.PRACTICE,
            practice_scenario=practice_scenario,
        )
        created = test_graph.create_session(session)

        retrieved = test_graph.get_session(created.id)
        assert retrieved is not None
        assert retrieved.session_type == SessionType.PRACTICE
        assert retrieved.practice_scenario is not None
        assert retrieved.practice_scenario.title == practice_scenario.title

    def test_session_with_feedback(self, test_graph, test_learner, practice_scenario):
        """Test session with practice feedback."""
        feedback = PracticeFeedback(
            positives=["Good job"],
            improvements=["Try harder"],
            summary="Completed.",
        )
        session = Session(
            learner_id=test_learner.id,
            session_type=SessionType.PRACTICE,
            practice_scenario=practice_scenario,
            practice_feedback=feedback,
        )
        created = test_graph.create_session(session)

        retrieved = test_graph.get_session(created.id)
        assert retrieved.practice_feedback is not None
        assert retrieved.practice_feedback.summary == "Completed."

    def test_learning_session_type(self, test_graph, test_learner):
        """Test that regular sessions default to learning type."""
        session = Session(learner_id=test_learner.id)
        created = test_graph.create_session(session)

        retrieved = test_graph.get_session(created.id)
        assert retrieved.session_type == SessionType.LEARNING
        assert retrieved.practice_scenario is None


# =============================================================================
# API Tests
# =============================================================================


class TestPracticeStartEndpoint:
    """Test POST /api/practice/start endpoint."""

    @patch("sage.api.routes.practice._get_llm_client")
    def test_start_practice_success(
        self, mock_get_client, client, test_graph, test_learner, auth_headers, mock_openai_response
    ):
        """Test starting a practice session."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_get_client.return_value = mock_client

        response = client.post(
            "/api/practice/start",
            headers=auth_headers,
            json={
                "scenario_id": "pricing-101",
                "title": "Pricing Negotiation",
                "sage_role": "Skeptical Client",
                "user_role": "Freelancer",
                "description": "Practice your pricing conversation",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "initial_message" in data
        assert data["initial_message"] == "Hello, I'm here to discuss your proposal."

    @patch("sage.api.routes.practice._get_llm_client")
    def test_start_practice_with_learner_id(
        self, mock_get_client, client, test_graph, test_learner, auth_headers, mock_openai_response
    ):
        """Test starting practice with existing learner."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_get_client.return_value = mock_client

        response = client.post(
            "/api/practice/start",
            headers=auth_headers,
            json={
                "scenario_id": "test-scenario",
                "title": "Test Practice",
                "sage_role": "Test Role",
                "user_role": "Test User",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify session was created with correct learner (from auth token)
        session = test_graph.get_session(data["session_id"])
        assert session.learner_id == test_learner.id


class TestPracticeMessageEndpoint:
    """Test POST /api/practice/{session_id}/message endpoint."""

    @patch("sage.api.routes.practice._get_llm_client")
    def test_send_message_success(
        self, mock_get_client, client, test_graph, auth_headers, practice_session, mock_openai_response
    ):
        """Test sending a message in practice mode."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_get_client.return_value = mock_client

        response = client.post(
            f"/api/practice/{practice_session.id}/message",
            headers=auth_headers,
            json={"content": "I'd like to discuss my rate of $150/hour."},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

        # Verify messages were added to session
        updated_session = test_graph.get_session(practice_session.id)
        assert len(updated_session.messages) == 3  # initial + user + response

    def test_send_message_invalid_session(self, client, test_graph, auth_headers):
        """Test sending message to non-existent session."""
        response = client.post(
            "/api/practice/nonexistent-session/message",
            headers=auth_headers,
            json={"content": "Hello"},
        )

        assert response.status_code == 404

    def test_send_message_wrong_session_type(
        self, client, test_graph, auth_headers, learning_session
    ):
        """Test sending message to non-practice session."""
        response = client.post(
            f"/api/practice/{learning_session.id}/message",
            headers=auth_headers,
            json={"content": "Hello"},
        )

        assert response.status_code == 400
        assert "Not a practice session" in response.json()["detail"]


class TestPracticeHintEndpoint:
    """Test POST /api/practice/{session_id}/hint endpoint."""

    @patch("sage.api.routes.practice._get_llm_client")
    def test_get_hint_success(
        self, mock_get_client, client, test_graph, auth_headers, practice_session, mock_hint_response
    ):
        """Test getting a hint during practice."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_hint_response
        mock_get_client.return_value = mock_client

        response = client.post(f"/api/practice/{practice_session.id}/hint", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "hint" in data
        assert data["hint"] == "Try addressing their concern directly."

    def test_get_hint_invalid_session(self, client, test_graph, auth_headers):
        """Test getting hint for non-existent session."""
        response = client.post("/api/practice/nonexistent/hint", headers=auth_headers)

        assert response.status_code == 404


class TestPracticeEndEndpoint:
    """Test POST /api/practice/{session_id}/end endpoint."""

    @patch("sage.api.routes.practice._get_llm_client")
    def test_end_practice_success(
        self, mock_get_client, client, test_graph, auth_headers, practice_session, mock_feedback_response
    ):
        """Test ending a practice session."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_feedback_response
        mock_get_client.return_value = mock_client

        response = client.post(f"/api/practice/{practice_session.id}/end", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "positives" in data
        assert "improvements" in data
        assert "summary" in data
        assert "revealed_gaps" in data
        assert len(data["positives"]) == 2
        assert "Clear communication" in data["positives"]

    @patch("sage.api.routes.practice._get_llm_client")
    def test_end_practice_stores_feedback(
        self, mock_get_client, client, test_graph, auth_headers, practice_session, mock_feedback_response
    ):
        """Test that ending practice stores feedback in session."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_feedback_response
        mock_get_client.return_value = mock_client

        client.post(f"/api/practice/{practice_session.id}/end", headers=auth_headers)

        # Verify feedback was stored
        updated_session = test_graph.get_session(practice_session.id)
        assert updated_session.practice_feedback is not None
        assert updated_session.ended_at is not None

    @patch("sage.api.routes.practice._get_llm_client")
    def test_end_practice_fallback_on_parse_error(
        self, mock_get_client, client, test_graph, auth_headers, practice_session
    ):
        """Test fallback when LLM returns invalid JSON."""
        mock_client = MagicMock()

        # Return invalid JSON
        mock_choice = MagicMock()
        mock_choice.message.content = "This is not valid JSON at all"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        response = client.post(f"/api/practice/{practice_session.id}/end", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # Should get fallback feedback
        assert "You completed the practice session" in data["positives"]

    def test_end_practice_invalid_session(self, client, test_graph, auth_headers):
        """Test ending non-existent session."""
        response = client.post("/api/practice/nonexistent/end", headers=auth_headers)

        assert response.status_code == 404


# =============================================================================
# Integration Tests
# =============================================================================


class TestPracticeFlow:
    """Integration tests for complete practice flow."""

    @patch("sage.api.routes.practice._get_llm_client")
    def test_complete_practice_flow(
        self, mock_get_client, client, test_graph, test_learner, auth_headers, mock_openai_response, mock_feedback_response
    ):
        """Test a complete practice session from start to end."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # 1. Start practice
        mock_client.chat.completions.create.return_value = mock_openai_response
        start_response = client.post(
            "/api/practice/start",
            headers=auth_headers,
            json={
                "scenario_id": "flow-test",
                "title": "Complete Flow Test",
                "sage_role": "Test Character",
                "user_role": "Test Learner",
            },
        )
        assert start_response.status_code == 200
        session_id = start_response.json()["session_id"]

        # 2. Send a few messages
        for i in range(2):
            msg_response = client.post(
                f"/api/practice/{session_id}/message",
                headers=auth_headers,
                json={"content": f"Test message {i}"},
            )
            assert msg_response.status_code == 200

        # 3. Get a hint
        hint_choice = MagicMock()
        hint_choice.message.content = "Here's a tip."
        hint_response_mock = MagicMock()
        hint_response_mock.choices = [hint_choice]
        mock_client.chat.completions.create.return_value = hint_response_mock

        hint_response = client.post(f"/api/practice/{session_id}/hint", headers=auth_headers)
        assert hint_response.status_code == 200

        # 4. End practice
        mock_client.chat.completions.create.return_value = mock_feedback_response
        end_response = client.post(f"/api/practice/{session_id}/end", headers=auth_headers)
        assert end_response.status_code == 200

        feedback = end_response.json()
        assert len(feedback["positives"]) > 0
        assert "summary" in feedback

        # 5. Verify session state
        session = test_graph.get_session(session_id)
        assert session.session_type == SessionType.PRACTICE
        assert session.practice_feedback is not None
        assert session.ended_at is not None
        # Should have: initial + 2 user msgs + 2 responses + 1 hint = 6
        assert len(session.messages) >= 5
