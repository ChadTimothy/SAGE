"""Tests for Cross-Modality Session State Synchronization.

Part of #81 - Cross-Modality State Synchronization.
"""

import pytest
from datetime import datetime

from sage.orchestration.session_state import (
    PartialSessionContext,
    TaggedMessage,
    UnifiedSessionState,
    SessionStateManager,
    session_state_manager,
)
from sage.orchestration.normalizer import InputModality
from sage.dialogue.structured_output import PendingDataRequest


class TestPartialSessionContext:
    """Tests for PartialSessionContext model."""

    def test_empty_context(self):
        """Empty context has all None values."""
        ctx = PartialSessionContext()
        assert ctx.energy_level is None
        assert ctx.time_available is None
        assert ctx.mindset is None
        assert ctx.physical_environment is None

    def test_partial_context(self):
        """Can create with partial values."""
        ctx = PartialSessionContext(
            energy_level=75,
            time_available="focused",
        )
        assert ctx.energy_level == 75
        assert ctx.time_available == "focused"
        assert ctx.mindset is None
        assert ctx.physical_environment is None

    def test_energy_level_validation(self):
        """Energy level must be 0-100."""
        ctx = PartialSessionContext(energy_level=50)
        assert ctx.energy_level == 50

        with pytest.raises(ValueError):
            PartialSessionContext(energy_level=-1)

        with pytest.raises(ValueError):
            PartialSessionContext(energy_level=101)


class TestTaggedMessage:
    """Tests for TaggedMessage model."""

    def test_tagged_message_creation(self):
        """Can create tagged message with modality."""
        msg = TaggedMessage(
            role="user",
            content="Hello!",
            source_modality=InputModality.VOICE,
        )
        assert msg.role == "user"
        assert msg.content == "Hello!"
        assert msg.source_modality == InputModality.VOICE
        assert isinstance(msg.timestamp, datetime)

    def test_message_serialization(self):
        """Message can be serialized to JSON."""
        msg = TaggedMessage(
            role="assistant",
            content="Hi there!",
            source_modality=InputModality.CHAT,
        )
        data = msg.model_dump(mode="json")
        assert data["role"] == "assistant"
        assert data["content"] == "Hi there!"
        assert data["source_modality"] == "chat"
        assert "timestamp" in data


class TestUnifiedSessionState:
    """Tests for UnifiedSessionState model."""

    def test_default_state(self):
        """Default state has sensible defaults."""
        state = UnifiedSessionState(session_id="test-123")
        assert state.session_id == "test-123"
        assert state.modality_preference == InputModality.CHAT
        assert state.pending_data_request is None
        assert state.check_in_complete is False
        assert state.messages == []
        assert state.voice_enabled is False

    def test_add_message(self):
        """Can add messages with modality tagging."""
        state = UnifiedSessionState(session_id="test-123")
        state.add_message("user", "Hello", InputModality.VOICE)
        state.add_message("assistant", "Hi!", InputModality.CHAT)

        assert len(state.messages) == 2
        assert state.messages[0].role == "user"
        assert state.messages[0].source_modality == InputModality.VOICE
        assert state.messages[1].role == "assistant"
        assert state.messages[1].source_modality == InputModality.CHAT

    def test_set_modality_preference(self):
        """Can update modality preference."""
        state = UnifiedSessionState(session_id="test-123")
        assert state.modality_preference == InputModality.CHAT

        state.set_modality_preference(InputModality.VOICE)
        assert state.modality_preference == InputModality.VOICE

    def test_merge_check_in_data_snake_case(self):
        """Merges check-in data with snake_case keys."""
        state = UnifiedSessionState(session_id="test-123")
        state.merge_collected_data({
            "energy_level": 80,
            "time_available": "quick",
            "mindset": "focused",
        })

        assert state.check_in_data.energy_level == 80
        assert state.check_in_data.time_available == "quick"
        assert state.check_in_data.mindset == "focused"

    def test_merge_check_in_data_camel_case(self):
        """Merges check-in data with camelCase keys from frontend."""
        state = UnifiedSessionState(session_id="test-123")
        state.merge_collected_data({
            "energyLevel": 65,
            "timeAvailable": "deep",
        })

        assert state.check_in_data.energy_level == 65
        assert state.check_in_data.time_available == "deep"

    def test_merge_into_pending_request(self):
        """Merges data into pending data request."""
        state = UnifiedSessionState(session_id="test-123")
        state.pending_data_request = PendingDataRequest(
            intent="session_check_in",
            required_fields=["energy_level", "time_available"],
            collected_data={"energy_level": 50},
            voice_prompt="What's your energy level?",
        )

        state.merge_collected_data({"time_available": "focused"})

        assert state.pending_data_request.collected_data["energy_level"] == 50
        assert state.pending_data_request.collected_data["time_available"] == "focused"

    def test_get_prefill_data_for_check_in(self):
        """Gets prefill data for check-in intent."""
        state = UnifiedSessionState(session_id="test-123")
        state.check_in_data = PartialSessionContext(
            energy_level=75,
            time_available="quick",
        )

        prefill = state.get_prefill_data_for_intent("session_check_in")

        assert prefill["energyLevel"] == 75
        assert prefill["timeAvailable"] == "quick"
        assert "mindset" not in prefill  # None values excluded

    def test_get_prefill_data_for_other_intent(self):
        """Gets prefill data from pending request for other intents."""
        state = UnifiedSessionState(session_id="test-123")
        state.pending_data_request = PendingDataRequest(
            intent="practice_setup",
            required_fields=["scenario", "difficulty"],
            collected_data={"scenario": "negotiation"},
            voice_prompt="Pick a scenario",
        )

        prefill = state.get_prefill_data_for_intent("practice_setup")
        assert prefill == {"scenario": "negotiation"}

    def test_get_prefill_data_no_match(self):
        """Returns empty dict when intent doesn't match."""
        state = UnifiedSessionState(session_id="test-123")
        state.pending_data_request = PendingDataRequest(
            intent="practice_setup",
            required_fields=["scenario"],
            collected_data={"scenario": "test"},
            voice_prompt="test",
        )

        prefill = state.get_prefill_data_for_intent("different_intent")
        assert prefill == {}

    def test_clear_pending_request(self):
        """Can clear pending data request."""
        state = UnifiedSessionState(session_id="test-123")
        state.pending_data_request = PendingDataRequest(
            intent="test",
            required_fields=[],
            collected_data={},
            voice_prompt="test",
        )

        state.clear_pending_request()
        assert state.pending_data_request is None

    def test_storage_serialization(self):
        """State can be serialized for storage."""
        state = UnifiedSessionState(session_id="test-123")
        state.modality_preference = InputModality.VOICE
        state.add_message("user", "Hello", InputModality.VOICE)

        storage_dict = state.to_storage_dict()

        assert storage_dict["session_id"] == "test-123"
        assert storage_dict["modality_preference"] == "voice"
        assert len(storage_dict["messages"]) == 1

    def test_storage_deserialization(self):
        """State can be reconstructed from storage."""
        storage_dict = {
            "session_id": "test-456",
            "modality_preference": "voice",
            "pending_data_request": None,
            "check_in_data": {"energy_level": 80},
            "check_in_complete": False,
            "messages": [],
            "voice_enabled": True,
            "last_activity": "2024-01-15T10:30:00",
        }

        state = UnifiedSessionState.from_storage_dict(storage_dict)

        assert state.session_id == "test-456"
        assert state.modality_preference == InputModality.VOICE
        assert state.check_in_data.energy_level == 80
        assert state.voice_enabled is True


class TestSessionStateManager:
    """Tests for SessionStateManager."""

    def setup_method(self):
        """Clear state manager before each test."""
        session_state_manager.clear_all()

    def test_get_or_create_new(self):
        """Creates new state if none exists."""
        state = session_state_manager.get_or_create("new-session")

        assert state.session_id == "new-session"
        assert state.modality_preference == InputModality.CHAT

    def test_get_or_create_existing(self):
        """Returns existing state if present."""
        # Create state
        state1 = session_state_manager.get_or_create("existing-session")
        state1.modality_preference = InputModality.VOICE
        session_state_manager.update("existing-session", state1)

        # Get same state
        state2 = session_state_manager.get_or_create("existing-session")

        assert state2.modality_preference == InputModality.VOICE

    def test_get_nonexistent(self):
        """Returns None for nonexistent session."""
        state = session_state_manager.get("nonexistent")
        assert state is None

    def test_update(self):
        """Can update existing state."""
        state = session_state_manager.get_or_create("update-test")
        state.voice_enabled = True
        session_state_manager.update("update-test", state)

        retrieved = session_state_manager.get("update-test")
        assert retrieved is not None
        assert retrieved.voice_enabled is True

    def test_delete(self):
        """Can delete session state."""
        session_state_manager.get_or_create("delete-test")
        session_state_manager.delete("delete-test")

        assert session_state_manager.get("delete-test") is None

    def test_delete_nonexistent_no_error(self):
        """Deleting nonexistent session doesn't raise error."""
        session_state_manager.delete("never-existed")

    def test_clear_all(self):
        """Clear all removes all states."""
        session_state_manager.get_or_create("session-1")
        session_state_manager.get_or_create("session-2")
        session_state_manager.clear_all()

        assert session_state_manager.get("session-1") is None
        assert session_state_manager.get("session-2") is None


class TestCrossModalityWorkflow:
    """Integration tests for cross-modality workflows."""

    def setup_method(self):
        """Clear state manager before each test."""
        session_state_manager.clear_all()

    def test_voice_to_ui_prefill_workflow(self):
        """Voice collects data, UI prefills form with it."""
        session_id = "voice-to-ui-test"
        state = session_state_manager.get_or_create(session_id)

        # Voice collects partial check-in data
        state.set_modality_preference(InputModality.VOICE)
        state.merge_collected_data({"energy_level": 70})
        session_state_manager.update(session_id, state)

        # User switches to UI
        state = session_state_manager.get(session_id)
        assert state is not None
        state.set_modality_preference(InputModality.CHAT)
        session_state_manager.update(session_id, state)

        # UI requests prefill data
        prefill = state.get_prefill_data_for_intent("session_check_in")

        assert prefill["energyLevel"] == 70
        assert "timeAvailable" not in prefill  # Not collected yet

    def test_ui_to_voice_context_workflow(self):
        """UI collects data, voice has context for follow-up."""
        session_id = "ui-to-voice-test"
        state = session_state_manager.get_or_create(session_id)

        # UI collects complete check-in
        state.set_modality_preference(InputModality.CHAT)
        state.merge_collected_data({
            "energyLevel": 85,
            "timeAvailable": "focused",
            "mindset": "curious",
        })
        state.check_in_complete = True
        session_state_manager.update(session_id, state)

        # User switches to voice
        state = session_state_manager.get(session_id)
        assert state is not None
        state.set_modality_preference(InputModality.VOICE)

        # Voice has full context
        assert state.check_in_data.energy_level == 85
        assert state.check_in_data.time_available == "focused"
        assert state.check_in_data.mindset == "curious"
        assert state.check_in_complete is True

    def test_multi_switch_workflow(self):
        """Multiple modality switches preserve state."""
        session_id = "multi-switch-test"
        state = session_state_manager.get_or_create(session_id)

        # Start in chat
        state.set_modality_preference(InputModality.CHAT)
        state.add_message("user", "Hello", InputModality.CHAT)
        session_state_manager.update(session_id, state)

        # Switch to voice, add message
        state = session_state_manager.get(session_id)
        assert state is not None
        state.set_modality_preference(InputModality.VOICE)
        state.add_message("user", "Hi there", InputModality.VOICE)
        session_state_manager.update(session_id, state)

        # Switch back to chat
        state = session_state_manager.get(session_id)
        assert state is not None
        state.set_modality_preference(InputModality.CHAT)
        state.add_message("assistant", "How can I help?", InputModality.CHAT)
        session_state_manager.update(session_id, state)

        # All messages preserved with modality tags
        assert len(state.messages) == 3
        assert state.messages[0].source_modality == InputModality.CHAT
        assert state.messages[1].source_modality == InputModality.VOICE
        assert state.messages[2].source_modality == InputModality.CHAT

    def test_pending_request_survives_switch(self):
        """Pending data request survives modality switch."""
        session_id = "pending-switch-test"
        state = session_state_manager.get_or_create(session_id)

        # Set up pending request in voice mode
        state.set_modality_preference(InputModality.VOICE)
        state.pending_data_request = PendingDataRequest(
            intent="practice_setup",
            required_fields=["scenario", "difficulty", "duration"],
            collected_data={"scenario": "negotiation"},
            voice_prompt="What scenario?",
        )
        session_state_manager.update(session_id, state)

        # Switch to UI
        state = session_state_manager.get(session_id)
        assert state is not None
        state.set_modality_preference(InputModality.CHAT)

        # Pending request still present
        assert state.pending_data_request is not None
        assert state.pending_data_request.intent == "practice_setup"
        assert state.pending_data_request.collected_data["scenario"] == "negotiation"

        # UI can continue collecting
        state.merge_collected_data({"difficulty": "medium"})

        assert state.pending_data_request.collected_data["difficulty"] == "medium"
