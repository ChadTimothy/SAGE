"""Unified Session State for Cross-Modality Synchronization.

This module provides models and utilities for maintaining consistent
state across voice and UI modalities, enabling seamless modality switching
mid-session.

Part of #81 - Cross-Modality State Synchronization
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sage.orchestration.normalizer import InputModality
from sage.dialogue.structured_output import PendingDataRequest


class PartialSessionContext(BaseModel):
    """Partially collected session context during check-in.

    Allows check-in to be completed across multiple modality switches.
    """

    energy_level: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Energy level 0-100 if collected",
    )
    time_available: str | None = Field(
        default=None,
        description="Time available if collected (quick/focused/deep)",
    )
    mindset: str | None = Field(
        default=None,
        description="User's current mindset/state if collected",
    )
    physical_environment: str | None = Field(
        default=None,
        description="Physical environment if collected",
    )


class TaggedMessage(BaseModel):
    """A message tagged with its source modality for history tracking."""

    role: str = Field(description="Message role: user, assistant, system")
    content: str = Field(description="Message content")
    source_modality: InputModality = Field(
        description="Which modality this message came from"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When message was sent",
    )


class UnifiedSessionState(BaseModel):
    """Unified state that synchronizes across voice and UI modalities.

    This state object allows users to switch between modalities mid-session
    without losing context or collected data. It tracks:
    - Current modality preference
    - Pending data collection state
    - Check-in progress
    - Message history with modality tags
    """

    session_id: str = Field(description="Unique session identifier")

    modality_preference: InputModality = Field(
        default=InputModality.CHAT,
        description="User's preferred modality for this session",
    )

    pending_data_request: PendingDataRequest | None = Field(
        default=None,
        description="Current pending data collection request, survives modality switches",
    )

    check_in_data: PartialSessionContext = Field(
        default_factory=PartialSessionContext,
        description="Partially collected check-in data",
    )

    check_in_complete: bool = Field(
        default=False,
        description="Whether session check-in has been completed",
    )

    messages: list[TaggedMessage] = Field(
        default_factory=list,
        description="All messages tagged with source modality",
    )

    voice_enabled: bool = Field(
        default=False,
        description="Whether voice input/output is enabled",
    )

    last_activity: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of last activity",
    )

    def merge_collected_data(self, new_data: dict[str, Any]) -> None:
        """Merge newly collected data into pending request and check-in state.

        This method handles merging partial data collected via different
        modalities into the unified state.
        """
        if self.pending_data_request:
            # Merge into pending request's collected data
            self.pending_data_request.collected_data.update(new_data)

        # Also update check-in data if relevant fields are present
        if "energy_level" in new_data or "energyLevel" in new_data:
            energy = new_data.get("energy_level") or new_data.get("energyLevel")
            if energy is not None:
                self.check_in_data.energy_level = int(energy)

        if "time_available" in new_data or "timeAvailable" in new_data:
            time_val = new_data.get("time_available") or new_data.get("timeAvailable")
            if time_val:
                self.check_in_data.time_available = str(time_val)

        if "mindset" in new_data:
            self.check_in_data.mindset = new_data["mindset"]

        if "physical_environment" in new_data:
            self.check_in_data.physical_environment = new_data["physical_environment"]

        self.last_activity = datetime.utcnow()

    def add_message(
        self,
        role: str,
        content: str,
        modality: InputModality,
    ) -> None:
        """Add a message to history with modality tag."""
        self.messages.append(TaggedMessage(
            role=role,
            content=content,
            source_modality=modality,
        ))
        self.last_activity = datetime.utcnow()

    def get_prefill_data_for_intent(self, intent: str) -> dict[str, Any]:
        """Get data to prefill UI forms based on intent.

        When a user switches from voice to UI, this provides the
        already-collected data to prefill the form.
        """
        if intent == "session_check_in":
            # Return check-in data for prefilling
            data = {}
            if self.check_in_data.energy_level is not None:
                data["energyLevel"] = self.check_in_data.energy_level
            if self.check_in_data.time_available:
                data["timeAvailable"] = self.check_in_data.time_available
            if self.check_in_data.mindset:
                data["mindset"] = self.check_in_data.mindset
            return data

        # For other intents, return collected data from pending request
        if self.pending_data_request and self.pending_data_request.intent == intent:
            return self.pending_data_request.collected_data.copy()

        return {}

    def set_modality_preference(self, modality: InputModality) -> None:
        """Update the user's modality preference."""
        self.modality_preference = modality
        self.last_activity = datetime.utcnow()

    def clear_pending_request(self) -> None:
        """Clear the pending data request after completion."""
        self.pending_data_request = None
        self.last_activity = datetime.utcnow()

    def to_storage_dict(self) -> dict[str, Any]:
        """Convert to dict suitable for storage/transmission."""
        return self.model_dump(mode="json")

    @classmethod
    def from_storage_dict(cls, data: dict[str, Any]) -> "UnifiedSessionState":
        """Reconstruct from storage dict."""
        return cls.model_validate(data)


class SessionStateManager:
    """Manages session states across multiple sessions.

    This class provides an in-memory store for session states with
    methods for creating, retrieving, and updating states.
    In production, this would be backed by a persistent store.
    """

    def __init__(self) -> None:
        self._states: dict[str, UnifiedSessionState] = {}

    def get_or_create(self, session_id: str) -> UnifiedSessionState:
        """Get existing state or create new one for session."""
        if session_id not in self._states:
            self._states[session_id] = UnifiedSessionState(session_id=session_id)
        return self._states[session_id]

    def get(self, session_id: str) -> UnifiedSessionState | None:
        """Get state for session, or None if not found."""
        return self._states.get(session_id)

    def update(self, session_id: str, state: UnifiedSessionState) -> None:
        """Update state for session."""
        self._states[session_id] = state

    def delete(self, session_id: str) -> None:
        """Delete state for session."""
        self._states.pop(session_id, None)

    def clear_all(self) -> None:
        """Clear all session states (for testing)."""
        self._states.clear()


# Global state manager instance
session_state_manager = SessionStateManager()
