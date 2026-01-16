"""Tests for Session State API Endpoints.

Part of #81 - Cross-Modality State Synchronization.

Note: Common fixtures (test_graph, client, test_learner, test_session, auth_headers)
are provided by conftest.py
"""

import pytest

from sage.orchestration.session_state import session_state_manager
from sage.orchestration.normalizer import InputModality
from sage.dialogue.structured_output import PendingDataRequest


@pytest.fixture(autouse=True)
def clear_state():
    """Clear session state before and after each test."""
    session_state_manager.clear_all()
    yield
    session_state_manager.clear_all()


class TestGetSessionState:
    """Tests for GET /api/sessions/{session_id}/state endpoint."""

    def test_get_session_state(self, client, test_session, auth_headers):
        """Getting state for a session returns state."""
        response = client.get(
            f"/api/sessions/{test_session.id}/state",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == test_session.id
        assert data["modality_preference"] == "chat"
        assert data["check_in_complete"] is False
        assert data["voice_enabled"] is False
        assert data["messages"] == []

    def test_get_existing_session_state(self, client, test_session, auth_headers):
        """Getting state for existing session returns current state."""
        # Create and modify state
        state = session_state_manager.get_or_create(test_session.id)
        state.modality_preference = InputModality.VOICE
        state.voice_enabled = True
        session_state_manager.update(test_session.id, state)

        response = client.get(
            f"/api/sessions/{test_session.id}/state",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["modality_preference"] == "voice"
        assert data["voice_enabled"] is True


class TestSetModalityPreference:
    """Tests for POST /api/sessions/{session_id}/modality endpoint."""

    def test_set_modality_to_voice(self, client, test_session, auth_headers):
        """Can set modality preference to voice."""
        response = client.post(
            f"/api/sessions/{test_session.id}/modality",
            headers=auth_headers,
            json={"modality": "voice"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["modality"] == "voice"

        # Verify state was updated
        state = session_state_manager.get(test_session.id)
        assert state is not None
        assert state.modality_preference == InputModality.VOICE

    def test_set_modality_to_chat(self, client, test_session, auth_headers):
        """Can set modality preference to chat."""
        # First set to voice
        state = session_state_manager.get_or_create(test_session.id)
        state.modality_preference = InputModality.VOICE
        session_state_manager.update(test_session.id, state)

        response = client.post(
            f"/api/sessions/{test_session.id}/modality",
            headers=auth_headers,
            json={"modality": "chat"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["modality"] == "chat"

    def test_set_invalid_modality(self, client, test_session, auth_headers):
        """Invalid modality returns validation error."""
        response = client.post(
            f"/api/sessions/{test_session.id}/modality",
            headers=auth_headers,
            json={"modality": "invalid"},
        )

        assert response.status_code == 422


class TestMergeCollectedData:
    """Tests for POST /api/sessions/{session_id}/merge-data endpoint."""

    def test_merge_check_in_data(self, client, test_session, auth_headers):
        """Can merge check-in data."""
        response = client.post(
            f"/api/sessions/{test_session.id}/merge-data",
            headers=auth_headers,
            json={
                "data": {
                    "energy_level": 75,
                    "time_available": "focused",
                }
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["check_in_data"]["energy_level"] == 75
        assert data["check_in_data"]["time_available"] == "focused"

    def test_merge_camel_case_data(self, client, test_session, auth_headers):
        """Can merge camelCase data from frontend."""
        response = client.post(
            f"/api/sessions/{test_session.id}/merge-data",
            headers=auth_headers,
            json={
                "data": {
                    "energyLevel": 80,
                    "timeAvailable": "quick",
                }
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["check_in_data"]["energy_level"] == 80
        assert data["check_in_data"]["time_available"] == "quick"

    def test_merge_into_pending_request(self, client, test_session, auth_headers):
        """Merges data into existing pending request."""
        # Set up pending request
        state = session_state_manager.get_or_create(test_session.id)
        state.pending_data_request = PendingDataRequest(
            intent="practice_setup",
            required_fields=["scenario", "difficulty"],
            collected_data={"scenario": "negotiation"},
            voice_prompt="test",
        )
        session_state_manager.update(test_session.id, state)

        response = client.post(
            f"/api/sessions/{test_session.id}/merge-data",
            headers=auth_headers,
            json={"data": {"difficulty": "medium"}},
        )

        assert response.status_code == 200
        data = response.json()
        collected = data["pending_data_request"]["collected_data"]
        assert collected["scenario"] == "negotiation"
        assert collected["difficulty"] == "medium"


class TestGetPrefillData:
    """Tests for GET /api/sessions/{session_id}/prefill/{intent} endpoint."""

    def test_get_check_in_prefill(self, client, test_session, auth_headers):
        """Gets prefill data for check-in intent."""
        # Set up state with check-in data
        state = session_state_manager.get_or_create(test_session.id)
        state.check_in_data.energy_level = 70
        state.check_in_data.time_available = "deep"
        session_state_manager.update(test_session.id, state)

        response = client.get(
            f"/api/sessions/{test_session.id}/prefill/session_check_in",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["energyLevel"] == 70
        assert data["timeAvailable"] == "deep"

    def test_get_prefill_no_data(self, client, test_session, auth_headers):
        """Returns empty dict when no data collected."""
        response = client.get(
            f"/api/sessions/{test_session.id}/prefill/session_check_in",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json() == {}

    def test_get_prefill_from_pending_request(self, client, test_session, auth_headers):
        """Gets prefill from pending request for matching intent."""
        # Set up pending request
        state = session_state_manager.get_or_create(test_session.id)
        state.pending_data_request = PendingDataRequest(
            intent="practice_setup",
            required_fields=["scenario"],
            collected_data={"scenario": "conflict resolution"},
            voice_prompt="test",
        )
        session_state_manager.update(test_session.id, state)

        response = client.get(
            f"/api/sessions/{test_session.id}/prefill/practice_setup",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["scenario"] == "conflict resolution"

    def test_get_prefill_nonexistent_session(self, client, auth_headers):
        """Non-existent session returns 404."""
        response = client.get(
            "/api/sessions/nonexistent/prefill/any_intent",
            headers=auth_headers,
        )

        # Ownership verification returns 404 for non-existent session
        assert response.status_code == 404


class TestClearSessionState:
    """Tests for DELETE /api/sessions/{session_id}/state endpoint."""

    def test_clear_existing_state(self, client, test_session, auth_headers):
        """Can clear existing session state."""
        # Create state
        state = session_state_manager.get_or_create(test_session.id)
        state.voice_enabled = True
        session_state_manager.update(test_session.id, state)

        response = client.delete(
            f"/api/sessions/{test_session.id}/state",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # Verify state was deleted
        assert session_state_manager.get(test_session.id) is None

    def test_clear_nonexistent_state(self, client, test_session, auth_headers):
        """Clearing nonexistent state succeeds silently."""
        response = client.delete(
            f"/api/sessions/{test_session.id}/state",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCrossModalityAPIWorkflow:
    """Integration tests for cross-modality workflows via API."""

    def test_voice_collects_ui_prefills_workflow(self, client, test_session, auth_headers):
        """Voice collects data, UI gets prefill through API."""
        session_id = test_session.id

        # Voice mode: collect partial check-in
        client.post(
            f"/api/sessions/{session_id}/modality",
            headers=auth_headers,
            json={"modality": "voice"},
        )

        client.post(
            f"/api/sessions/{session_id}/merge-data",
            headers=auth_headers,
            json={"data": {"energy_level": 60}},
        )

        # Switch to UI
        client.post(
            f"/api/sessions/{session_id}/modality",
            headers=auth_headers,
            json={"modality": "chat"},
        )

        # UI gets prefill data
        response = client.get(
            f"/api/sessions/{session_id}/prefill/session_check_in",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["energyLevel"] == 60

    def test_full_state_sync_workflow(self, client, test_session, auth_headers):
        """Full workflow: create, modify, sync, clear."""
        session_id = test_session.id

        # Initial state
        response = client.get(
            f"/api/sessions/{session_id}/state",
            headers=auth_headers,
        )
        assert response.json()["modality_preference"] == "chat"

        # Set voice mode
        client.post(
            f"/api/sessions/{session_id}/modality",
            headers=auth_headers,
            json={"modality": "voice"},
        )

        # Collect data
        client.post(
            f"/api/sessions/{session_id}/merge-data",
            headers=auth_headers,
            json={"data": {"energyLevel": 85, "mindset": "focused"}},
        )

        # Verify state
        response = client.get(
            f"/api/sessions/{session_id}/state",
            headers=auth_headers,
        )
        data = response.json()
        assert data["modality_preference"] == "voice"
        assert data["check_in_data"]["energy_level"] == 85
        assert data["check_in_data"]["mindset"] == "focused"

        # Clear state
        client.delete(
            f"/api/sessions/{session_id}/state",
            headers=auth_headers,
        )

        # Verify state was cleared
        assert session_state_manager.get(session_id) is None
