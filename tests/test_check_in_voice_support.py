"""
Tests for Check-in Voice Support (#59)

These tests verify that the check-in form supports:
1. Input mode selection (form/voice/both)
2. Prefill from voice-collected data
3. UI sync when using voice mode
"""

import pytest
from pathlib import Path


class TestCheckInModalStructure:
    """Test that CheckInModal has voice support features."""

    @pytest.fixture
    def modal_content(self) -> str:
        """Get CheckInModal component content."""
        modal_path = (
            Path(__file__).parent.parent
            / "web"
            / "components"
            / "sidebar"
            / "CheckInModal.tsx"
        )
        return modal_path.read_text()

    def test_has_input_mode_type(self, modal_content: str) -> None:
        """Should export InputMode type for form/voice/both."""
        assert 'export type InputMode = "form" | "voice" | "both"' in modal_content

    def test_has_prefill_data_prop(self, modal_content: str) -> None:
        """Should accept prefillData prop for voice-collected data."""
        assert "prefillData" in modal_content
        assert "Partial<SessionContext>" in modal_content

    def test_has_input_mode_change_callback(self, modal_content: str) -> None:
        """Should have callback for input mode changes."""
        assert "onInputModeChange" in modal_content

    def test_has_voice_available_prop(self, modal_content: str) -> None:
        """Should accept voiceAvailable prop to disable voice options."""
        assert "voiceAvailable" in modal_content


class TestInputModeOptions:
    """Test input mode selector configuration."""

    @pytest.fixture
    def modal_content(self) -> str:
        """Get CheckInModal component content."""
        modal_path = (
            Path(__file__).parent.parent
            / "web"
            / "components"
            / "sidebar"
            / "CheckInModal.tsx"
        )
        return modal_path.read_text()

    def test_has_form_mode_option(self, modal_content: str) -> None:
        """Should have form-only input mode."""
        assert 'value: "form"' in modal_content
        assert 'label: "Form"' in modal_content

    def test_has_voice_mode_option(self, modal_content: str) -> None:
        """Should have voice-only input mode."""
        assert 'value: "voice"' in modal_content
        assert 'label: "Voice"' in modal_content

    def test_has_both_mode_option(self, modal_content: str) -> None:
        """Should have combined voice+form input mode."""
        assert 'value: "both"' in modal_content
        assert 'label: "Both"' in modal_content


class TestVoiceModeUI:
    """Test voice mode user interface."""

    @pytest.fixture
    def modal_content(self) -> str:
        """Get CheckInModal component content."""
        modal_path = (
            Path(__file__).parent.parent
            / "web"
            / "components"
            / "sidebar"
            / "CheckInModal.tsx"
        )
        return modal_path.read_text()

    def test_shows_voice_hint_in_voice_mode(self, modal_content: str) -> None:
        """Should show voice input hint when in voice/both mode."""
        assert "showVoiceHint" in modal_content
        assert 'Try saying:' in modal_content

    def test_hides_form_in_voice_only_mode(self, modal_content: str) -> None:
        """Should conditionally show form based on mode."""
        assert "showForm" in modal_content
        assert 'inputMode === "form" || inputMode === "both"' in modal_content

    def test_voice_only_mode_has_close_option(self, modal_content: str) -> None:
        """Should allow closing modal in voice-only mode to start chatting."""
        assert "Close and start chatting" in modal_content


class TestPrefillDataSync:
    """Test that form syncs with prefill data from voice."""

    @pytest.fixture
    def modal_content(self) -> str:
        """Get CheckInModal component content."""
        modal_path = (
            Path(__file__).parent.parent
            / "web"
            / "components"
            / "sidebar"
            / "CheckInModal.tsx"
        )
        return modal_path.read_text()

    def test_syncs_time_available_from_prefill(self, modal_content: str) -> None:
        """Should update timeAvailable when prefillData changes."""
        assert "prefillData.timeAvailable" in modal_content
        assert "setTimeAvailable(prefillData.timeAvailable)" in modal_content

    def test_syncs_energy_level_from_prefill(self, modal_content: str) -> None:
        """Should update energyLevel when prefillData changes."""
        assert "prefillData.energyLevel" in modal_content
        assert "setEnergyLevel(prefillData.energyLevel)" in modal_content

    def test_syncs_mindset_from_prefill(self, modal_content: str) -> None:
        """Should update mindset when prefillData changes."""
        assert "prefillData.mindset" in modal_content
        assert "setMindset(prefillData.mindset)" in modal_content

    def test_uses_effect_for_sync(self, modal_content: str) -> None:
        """Should use useEffect to sync prefill data."""
        assert "useEffect" in modal_content
        assert "[prefillData]" in modal_content


class TestAccessibility:
    """Test accessibility features in voice-enabled check-in."""

    @pytest.fixture
    def modal_content(self) -> str:
        """Get CheckInModal component content."""
        modal_path = (
            Path(__file__).parent.parent
            / "web"
            / "components"
            / "sidebar"
            / "CheckInModal.tsx"
        )
        return modal_path.read_text()

    def test_input_mode_buttons_have_aria_pressed(self, modal_content: str) -> None:
        """Input mode buttons should have aria-pressed for screen readers."""
        assert 'aria-pressed={inputMode === option.value}' in modal_content

    def test_close_button_has_aria_label(self, modal_content: str) -> None:
        """Close button should have aria-label."""
        assert 'aria-label="Close"' in modal_content

    def test_slider_has_aria_attributes(self, modal_content: str) -> None:
        """Energy slider should have proper ARIA attributes."""
        assert "aria-valuemin" in modal_content
        assert "aria-valuemax" in modal_content
        assert "aria-valuenow" in modal_content

    def test_voice_unavailable_disables_options(self, modal_content: str) -> None:
        """Voice options should be disabled when voice is unavailable."""
        assert 'option.value !== "form" && !voiceAvailable' in modal_content
        assert "cursor-not-allowed" in modal_content


class TestBackendIntentSupport:
    """Test that backend supports check-in intent extraction."""

    def test_session_check_in_intent_schema_exists(self) -> None:
        """Backend should have session_check_in intent schema."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "intent_extractor",
            Path(__file__).parent.parent
            / "src"
            / "sage"
            / "orchestration"
            / "intent_extractor.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert "session_check_in" in module.INTENT_SCHEMAS

    def test_check_in_schema_has_required_fields(self) -> None:
        """Check-in schema should include timeAvailable, energyLevel, mindset."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "intent_extractor",
            Path(__file__).parent.parent
            / "src"
            / "sage"
            / "orchestration"
            / "intent_extractor.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        schema = module.INTENT_SCHEMAS["session_check_in"]
        optional_fields = schema.get("optional", [])

        assert "timeAvailable" in optional_fields
        assert "energyLevel" in optional_fields
        assert "mindset" in optional_fields
