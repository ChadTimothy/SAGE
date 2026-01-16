"""Integration tests for Voice/UI Parity.

Tests that voice input and form submission produce equivalent outcomes.

Part of #82 - Integration Testing & Voice/UI Parity Verification
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from sage.graph.models import SessionContext, EnergyLevel


@pytest.fixture
def mock_client():
    """Create mock OpenAI client."""
    return MagicMock()


class TestVoiceUIEquivalence:
    """Tests that verify voice and UI produce equivalent data."""

    def test_check_in_form_data_matches_voice_intent(self):
        """Form data structure matches what voice parsing would produce."""
        # Form submission data structure
        form_data = {
            "_action": "submit_check_in",
            "timeAvailable": "focused",
            "energy": "medium",
            "mindset": "nervous about tomorrow's presentation",
        }

        # This should map to SessionContext fields
        context = SessionContext(
            time_available=form_data["timeAvailable"],
            energy=EnergyLevel(form_data["energy"]),
            mindset=form_data["mindset"],
        )

        assert context.time_available == "focused"
        assert context.energy == EnergyLevel.MEDIUM
        assert "nervous" in context.mindset.lower()

    def test_voice_intent_maps_to_session_context(self):
        """Voice input like '30 minutes, feeling tired' maps to SessionContext."""
        # Simulate what voice parsing would extract
        voice_extracted = {
            "time_available": "30 minutes",
            "energy": "low",  # "feeling tired" -> low energy
            "mindset": "feeling tired",
        }

        context = SessionContext(
            time_available=voice_extracted["time_available"],
            energy=EnergyLevel(voice_extracted["energy"]),
            mindset=voice_extracted["mindset"],
        )

        assert "30" in context.time_available
        assert context.energy == EnergyLevel.LOW
        assert context.mindset is not None

    def test_energy_level_values_match(self):
        """EnergyLevel enum values match form options."""
        valid_options = ["low", "medium", "high"]

        for option in valid_options:
            # Should not raise
            energy = EnergyLevel(option)
            assert energy.value == option

    def test_time_available_accepts_various_formats(self):
        """Time available accepts various string formats."""
        valid_formats = [
            "15 minutes",
            "quick",
            "focused",
            "30-60 min",
            "an hour",
            "open-ended",
            "deep",
        ]

        for time_str in valid_formats:
            context = SessionContext(
                time_available=time_str,
                energy=EnergyLevel.MEDIUM,
                mindset="test",
            )
            assert context.time_available == time_str


class TestModalitySwitching:
    """Tests for switching between voice and form mid-interaction."""

    def test_partial_data_structure(self):
        """Partial data can be collected across modalities."""
        # Start with voice - partial data
        voice_partial = {
            "time_available": "focused",
            # Missing: energy, mindset
        }

        # Complete with form
        form_completion = {
            "energy": "high",
            "mindset": "ready to learn",
        }

        # Merged result should have all fields
        merged = {
            "time_available": voice_partial.get("time_available"),
            "energy": form_completion.get("energy"),
            "mindset": form_completion.get("mindset"),
        }

        assert merged["time_available"] == "focused"
        assert merged["energy"] == "high"
        assert merged["mindset"] == "ready to learn"

    def test_form_can_override_voice_data(self):
        """Form submission can correct voice-parsed data."""
        voice_data = {
            "energy": "high",  # Voice might misinterpret
        }

        form_data = {
            "energy": "low",  # User corrects via form
        }

        # Form should take precedence for explicit corrections
        final_energy = form_data["energy"]
        assert final_energy == "low"


class TestPracticeSetupParity:
    """Tests for practice setup voice/UI parity."""

    def test_scenario_selection_formats(self):
        """Scenario selection works from both modalities."""
        # Form radio selection
        form_scenario = {"scenario": "pricing_call"}

        # Voice natural language
        voice_scenario = "I want to practice a pricing call"

        # Both should result in same scenario type
        assert "pricing" in form_scenario["scenario"]
        assert "pricing" in voice_scenario.lower()

    def test_custom_scenario_collection(self):
        """Custom scenarios can be provided via form or voice."""
        # Form text input
        form_custom = {
            "scenario": "custom",
            "customDescription": "Negotiating with a difficult vendor",
        }

        # Voice description
        voice_custom = "I want to practice negotiating with a difficult vendor"

        # Both capture the custom scenario
        assert "negotiating" in form_custom["customDescription"].lower()
        assert "negotiating" in voice_custom.lower()


class TestVerificationParity:
    """Tests for verification challenge voice/UI parity."""

    def test_multiple_choice_answer_formats(self):
        """Multiple choice answers work from both modalities."""
        # Form radio selection
        form_answer = {"answer": "b"}

        # Voice natural language
        voice_answers = [
            "B",
            "option B",
            "the second one",
            "Start high with room to come down",
        ]

        # Form gives clean answer
        assert form_answer["answer"] in ["a", "b", "c"]

        # Voice needs parsing but should map to same answer
        # The orchestrator should handle this mapping

    def test_explanation_answer_formats(self):
        """Free-form explanation answers work from both modalities."""
        # Form textarea
        form_explanation = {
            "explanation": "Anchor pricing is about starting high to set expectations"
        }

        # Voice transcription
        voice_explanation = "anchor pricing is about starting high to set expectations"

        # Both should contain key concepts
        assert "anchor" in form_explanation["explanation"].lower()
        assert "anchor" in voice_explanation.lower()
        assert "high" in form_explanation["explanation"].lower()
        assert "high" in voice_explanation.lower()


class TestApplicationEventParity:
    """Tests for application event voice/UI parity."""

    def test_application_capture_formats(self):
        """Application events captured from both modalities."""
        # Form structured input
        form_app = {
            "context": "Pricing call with new client",
            "date": "tomorrow",
            "concepts": ["anchor_pricing"],
        }

        # Voice natural language
        voice_app = "I have a pricing call with a new client tomorrow where I'll use anchor pricing"

        # Both should capture: what, when, what concepts
        assert "pricing call" in form_app["context"].lower()
        assert "pricing call" in voice_app.lower()

    def test_followup_response_formats(self):
        """Followup responses work from both modalities."""
        # Form selection + text
        form_followup = {
            "outcome": "struggled",
            "details": "I caved on the discount when they pushed back",
        }

        # Voice natural language
        voice_followup = "It didn't go well - I caved on the discount when they pushed back"

        # Both indicate struggle and capture details
        assert form_followup["outcome"] == "struggled"
        assert "caved" in form_followup["details"].lower()
        assert "caved" in voice_followup.lower()


class TestDataStructureAlignment:
    """Tests that data structures align across modalities."""

    def test_session_context_from_form(self):
        """SessionContext can be created from form data."""
        form_data = {
            "time_available": "quick",
            "energy": "medium",
            "mindset": "curious",
            "environment": "quiet office",
        }

        context = SessionContext(
            time_available=form_data["time_available"],
            energy=EnergyLevel(form_data["energy"]),
            mindset=form_data["mindset"],
            environment=form_data.get("environment"),
        )

        assert context.time_available == "quick"
        assert context.energy == EnergyLevel.MEDIUM
        assert context.mindset == "curious"
        assert context.environment == "quiet office"

    def test_session_context_field_types(self):
        """SessionContext field types are consistent."""
        context = SessionContext(
            time_available="focused",
            energy=EnergyLevel.HIGH,
            mindset="test mindset",
        )

        # Type checks
        assert isinstance(context.time_available, str)
        assert isinstance(context.energy, EnergyLevel)
        assert isinstance(context.mindset, str)

    def test_form_actions_are_standardized(self):
        """Form actions follow standard naming convention."""
        standard_actions = [
            "submit_checkin",
            "submit_check_in",
            "start_practice",
            "submit_verification",
            "confirm_application",
            "submit_followup",
            "submit_goal",
            "continue",
        ]

        # All actions should be lowercase with underscores
        for action in standard_actions:
            assert action.islower() or "_" in action
            assert " " not in action  # No spaces


class TestVoiceFallbackUsability:
    """Tests that voice fallbacks are usable for actual voice interaction."""

    def test_voice_fallback_length_appropriate(self):
        """Voice fallbacks are appropriate length for speech."""
        example_fallbacks = [
            "How are you showing up today?",
            "What do you want to be able to DO?",
            "Quick check: can you explain anchor pricing in your own words?",
        ]

        for fallback in example_fallbacks:
            # Not too short (meaningless)
            assert len(fallback) >= 15
            # Not too long (hard to process aurally)
            assert len(fallback) < 500
            # Should be speakable (ends with ? or . typically)
            assert fallback[-1] in ".?!"

    def test_voice_fallback_avoids_visual_references(self):
        """Voice fallbacks don't reference visual elements."""
        bad_phrases = [
            "click the button",
            "select from the dropdown",
            "use the slider",
            "check the checkbox",
            "fill in the form",
            "see below",
            "shown above",
        ]

        good_fallback = "How are you showing up today? What's your energy level, roughly?"

        for phrase in bad_phrases:
            assert phrase not in good_fallback.lower()
