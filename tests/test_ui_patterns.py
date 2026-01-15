"""Integration tests for UI pattern generation.

Tests that the UI Generation Agent can produce appropriate UIs for all SAGE
interaction types with proper structure and voice fallbacks.

Part of #76 - UI Patterns & Agent Verification
"""

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from sage.dialogue.structured_output import UITreeNode
from sage.orchestration.models import UITreeSpec
from sage.orchestration.ui_agent import UIGenerationAgent


def flatten_tree(node: UITreeNode) -> list[UITreeNode]:
    """Recursively flatten a UI tree into a list of all nodes."""
    result = [node]
    if node.children:
        for child in node.children:
            result.extend(flatten_tree(child))
    return result


def get_component_types(tree: UITreeNode) -> set[str]:
    """Get all unique component types in a tree."""
    return {node.component for node in flatten_tree(tree)}


def get_components_by_type(tree: UITreeNode, component_type: str) -> list[UITreeNode]:
    """Get all components of a specific type from the tree."""
    return [node for node in flatten_tree(tree) if node.component == component_type]


def create_mock_ui_response(tree_data: dict[str, Any], voice_fallback: str, purpose: str) -> str:
    """Create a mock LLM response for UI generation."""
    return json.dumps({
        "tree": tree_data,
        "voice_fallback": voice_fallback,
        "purpose": purpose,
        "estimated_interaction_time": 30,
    })


@pytest.fixture
def mock_client():
    """Create mock OpenAI client."""
    return MagicMock()


@pytest.fixture
def agent(mock_client):
    """Create agent with mock client."""
    return UIGenerationAgent(mock_client, model="test-model")


class TestSessionCheckInPattern:
    """Test session check-in UI pattern generation."""

    def test_generates_valid_check_in_structure(self, agent, mock_client):
        """Agent generates valid session check-in UI with required elements."""
        # Mock response with required check-in elements
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={
                "component": "Card",
                "props": {"title": "Session Check-in"},
                "children": [
                    {
                        "component": "Stack",
                        "props": {"gap": 4},
                        "children": [
                            {
                                "component": "RadioGroup",
                                "props": {"name": "timeAvailable", "label": "Time Available"},
                                "children": [
                                    {"component": "Radio", "props": {"value": "quick", "label": "Quick (15 min)"}},
                                    {"component": "Radio", "props": {"value": "focused", "label": "Focused (30-60 min)"}},
                                    {"component": "Radio", "props": {"value": "deep", "label": "Deep dive (1+ hours)"}},
                                ],
                            },
                            {
                                "component": "Slider",
                                "props": {"name": "energyLevel", "label": "Energy Level", "min": 0, "max": 100},
                            },
                            {
                                "component": "TextArea",
                                "props": {"name": "mindset", "label": "What's on your mind?", "placeholder": "Any thoughts..."},
                            },
                            {
                                "component": "Button",
                                "props": {"action": "submit_checkin", "label": "Start Session"},
                            },
                        ],
                    },
                ],
            },
            voice_fallback="How are you showing up today? How much time do you have - quick, focused, or a deep dive? And energy-wise, where are you at on a scale of 1-100? Anything on your mind?",
            purpose="Collect session check-in data",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(
            purpose="Collect session check-in: time, energy, mindset",
            context={"mode": "check_in"},
        )

        # Verify structure
        assert result.tree.component in ["Card", "Stack"]

        # Verify required inputs present
        component_types = get_component_types(result.tree)

        assert "RadioGroup" in component_types or "Select" in component_types  # Time
        assert "Slider" in component_types  # Energy
        assert "TextArea" in component_types or "TextInput" in component_types  # Mindset
        assert "Button" in component_types  # Submit

        # Verify voice fallback exists and is meaningful
        assert result.voice_fallback
        assert len(result.voice_fallback) > 20

    def test_check_in_voice_fallback_is_conversational(self, agent, mock_client):
        """Check-in voice fallback sounds natural, not robotic."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={"component": "Card", "props": {}, "children": [
                {"component": "Slider", "props": {"name": "energy", "label": "Energy"}},
                {"component": "Button", "props": {"action": "submit", "label": "Go"}},
            ]},
            voice_fallback="How are you showing up today? What's your energy level? Anything on your mind before we begin?",
            purpose="Session check-in",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(
            purpose="Collect energy level and time available",
            context={"mode": "check_in"},
        )

        fallback = result.voice_fallback.lower()

        # Should be conversational
        assert any(word in fallback for word in ["how", "what", "would", "your", "you"])

        # Should not be form-like
        assert "field" not in fallback
        assert "input" not in fallback
        assert "required" not in fallback


class TestPracticeSetupPattern:
    """Test practice scenario setup UI pattern generation."""

    def test_generates_valid_practice_setup_structure(self, agent, mock_client):
        """Agent generates valid practice setup UI with scenario options."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={
                "component": "Card",
                "props": {"title": "Practice Scenario"},
                "children": [
                    {
                        "component": "Stack",
                        "props": {"gap": 4},
                        "children": [
                            {"component": "Text", "props": {"content": "Choose a scenario to practice:"}},
                            {
                                "component": "Grid",
                                "props": {"columns": 2, "gap": 3},
                                "children": [
                                    {"component": "Card", "props": {"title": "Pricing Call"}},
                                    {"component": "Card", "props": {"title": "Negotiation"}},
                                    {"component": "Card", "props": {"title": "Presentation"}},
                                    {"component": "Card", "props": {"title": "Interview"}},
                                ],
                            },
                            {
                                "component": "TextInput",
                                "props": {"name": "customScenario", "label": "Or describe your own scenario"},
                            },
                            {
                                "component": "Button",
                                "props": {"action": "start_practice", "label": "Start Practice"},
                            },
                        ],
                    },
                ],
            },
            voice_fallback="Let's practice! Would you like to work on a pricing call, negotiation, presentation, interview, or something custom? Just tell me what situation you'd like to practice.",
            purpose="Set up practice scenario",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(
            purpose="Choose practice scenario from presets or custom",
            context={"mode": "practice_setup"},
        )

        component_types = get_component_types(result.tree)

        # Should have multiple selectable options (Grid, RadioGroup, or Cards)
        assert any(ct in component_types for ct in ["RadioGroup", "Grid", "Card"])
        # Should have submit action
        assert "Button" in component_types

        # Voice fallback should mention options
        fallback = result.voice_fallback.lower()
        assert any(word in fallback for word in ["practice", "scenario", "would", "like"])

    def test_practice_setup_includes_custom_option(self, agent, mock_client):
        """Practice setup allows custom scenario input."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={
                "component": "Stack",
                "props": {},
                "children": [
                    {"component": "RadioGroup", "props": {"name": "scenario"}, "children": [
                        {"component": "Radio", "props": {"value": "pricing", "label": "Pricing"}},
                        {"component": "Radio", "props": {"value": "custom", "label": "Custom"}},
                    ]},
                    {"component": "TextInput", "props": {"name": "customDescription", "label": "Custom scenario"}},
                    {"component": "Button", "props": {"action": "start", "label": "Start"}},
                ],
            },
            voice_fallback="What situation would you like to practice? Pricing, or describe your own scenario.",
            purpose="Practice setup",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(
            purpose="Let user choose a practice scenario",
            context={"mode": "practice_setup"},
        )

        component_types = get_component_types(result.tree)
        # Should have text input for custom scenario
        assert "TextInput" in component_types or "TextArea" in component_types


class TestVerificationChallengePattern:
    """Test verification challenge UI pattern generation."""

    def test_generates_multiple_choice_verification(self, agent, mock_client):
        """Agent generates valid multiple choice verification quiz."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={
                "component": "Card",
                "props": {"title": "Quick Check", "variant": "highlight"},
                "children": [
                    {
                        "component": "Stack",
                        "props": {"gap": 4},
                        "children": [
                            {"component": "Text", "props": {"content": "You mentioned anchor pricing. What's the key?"}},
                            {
                                "component": "RadioGroup",
                                "props": {"name": "answer"},
                                "children": [
                                    {"component": "Radio", "props": {"value": "a", "label": "Start low and negotiate up"}},
                                    {"component": "Radio", "props": {"value": "b", "label": "Start high with room to come down"}},
                                    {"component": "Radio", "props": {"value": "c", "label": "Match competitor pricing"}},
                                ],
                            },
                            {"component": "Button", "props": {"action": "submit_verification", "label": "Check my understanding"}},
                        ],
                    },
                ],
            },
            voice_fallback="Quick check: you mentioned anchor pricing. What's the key to making it work? A: Start low and negotiate up, B: Start high with room to come down, or C: Match competitor pricing?",
            purpose="Verify understanding of anchor pricing",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(
            purpose="Quiz on anchor pricing with 3 options",
            context={"mode": "verification", "concept": "anchor pricing"},
        )

        component_types = get_component_types(result.tree)

        # Must have answer selection
        assert "RadioGroup" in component_types
        # Must have submit button
        assert "Button" in component_types

        # Voice fallback should present options
        fallback = result.voice_fallback.lower()
        assert "anchor" in fallback or "pricing" in fallback

    def test_generates_explanation_verification(self, agent, mock_client):
        """Agent generates explanation-type verification challenge."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={
                "component": "Card",
                "props": {"title": "Explain This"},
                "children": [
                    {"component": "Text", "props": {"content": "Explain anchor pricing in your own words:"}},
                    {"component": "TextArea", "props": {"name": "explanation", "rows": 4}},
                    {"component": "Button", "props": {"action": "submit", "label": "Submit"}},
                ],
            },
            voice_fallback="Let's see if this landed. Can you explain anchor pricing in your own words?",
            purpose="Explanation verification",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(
            purpose="Verify understanding - explain anchor pricing",
            context={"mode": "verification", "challenge_type": "explanation"},
        )

        component_types = get_component_types(result.tree)

        # Should have text area for explanation
        assert "TextArea" in component_types or "TextInput" in component_types
        assert "Button" in component_types


class TestApplicationEventPattern:
    """Test application event UI pattern generation."""

    def test_generates_application_capture_ui(self, agent, mock_client):
        """Agent generates UI to capture application event."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={
                "component": "Card",
                "props": {"title": "Upcoming Application"},
                "children": [
                    {"component": "Text", "props": {"content": "You mentioned applying anchor pricing in a call tomorrow."}},
                    {"component": "Stack", "props": {"gap": 3}, "children": [
                        {"component": "TextInput", "props": {"name": "context", "label": "Context", "value": "Pricing call with new client"}},
                        {"component": "TextInput", "props": {"name": "date", "label": "When?", "value": "Tomorrow"}},
                        {"component": "Button", "props": {"action": "confirm_application", "label": "Remind me to check in"}},
                    ]},
                ],
            },
            voice_fallback="I heard you mention you're applying anchor pricing in a call tomorrow. Want me to check in with you after to see how it went?",
            purpose="Capture application event",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(
            purpose="Capture that they're applying anchor pricing in a call tomorrow",
            context={"mode": "application_capture"},
        )

        component_types = get_component_types(result.tree)

        # Should have context display and confirm
        assert "Button" in component_types
        assert any(ct in component_types for ct in ["Text", "TextInput"])

    def test_generates_application_followup_ui(self, agent, mock_client):
        """Agent generates UI for application followup."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={
                "component": "Card",
                "props": {"title": "How did it go?"},
                "children": [
                    {"component": "Text", "props": {"content": "You had that pricing call yesterday. How did it go?"}},
                    {"component": "RadioGroup", "props": {"name": "outcome"}, "children": [
                        {"component": "Radio", "props": {"value": "well", "label": "Went well"}},
                        {"component": "Radio", "props": {"value": "struggled", "label": "Struggled"}},
                        {"component": "Radio", "props": {"value": "mixed", "label": "Mixed results"}},
                    ]},
                    {"component": "TextArea", "props": {"name": "details", "label": "What happened?"}},
                    {"component": "Button", "props": {"action": "submit_followup", "label": "Share"}},
                ],
            },
            voice_fallback="Before we dive in - you had that pricing call yesterday. How did it go? Did it go well, were there struggles, or mixed results?",
            purpose="Follow up on application event",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(
            purpose="Follow up on the pricing call they had yesterday",
            context={"mode": "application_followup"},
        )

        component_types = get_component_types(result.tree)

        # Should have outcome selection and details
        assert "RadioGroup" in component_types or "Select" in component_types
        assert "Button" in component_types


class TestProofAcknowledgmentPattern:
    """Test proof acknowledgment UI pattern generation."""

    def test_generates_proof_acknowledgment_ui(self, agent, mock_client):
        """Agent generates celebratory proof acknowledgment UI."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={
                "component": "Card",
                "props": {"title": "Understanding Verified", "variant": "highlight"},
                "children": [
                    {"component": "Stack", "props": {"gap": 4, "align": "center"}, "children": [
                        {"component": "Badge", "props": {"label": "Proof Earned", "variant": "success"}},
                        {"component": "Text", "props": {"variant": "heading", "content": "Anchor Pricing"}},
                        {"component": "ProgressBar", "props": {"value": 90, "label": "Confidence: High"}},
                        {"component": "Text", "props": {"variant": "body", "content": "Demonstrated through: Clear explanation with real-world example"}},
                        {"component": "Button", "props": {"action": "continue", "label": "Continue"}},
                    ]},
                ],
            },
            voice_fallback="That's it. You've definitely got anchor pricing. I can tell because you explained it with a real-world example. This one's solid.",
            purpose="Acknowledge proof earned",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(
            purpose="Show proof acknowledgment for anchor pricing, high confidence",
            context={"mode": "proof_acknowledgment", "concept": "anchor pricing", "confidence": "high"},
        )

        component_types = get_component_types(result.tree)

        # Should have visual success indicators
        assert any(ct in component_types for ct in ["Badge", "ProgressBar", "Text"])
        # Should have continue action
        assert "Button" in component_types

        # Voice should be celebratory
        fallback = result.voice_fallback.lower()
        assert any(word in fallback for word in ["got", "solid", "definitely", "verified"])


class TestOutcomeDiscoveryPattern:
    """Test outcome discovery UI pattern generation."""

    def test_generates_outcome_discovery_ui(self, agent, mock_client):
        """Agent generates outcome discovery UI."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={
                "component": "Card",
                "props": {"title": "What's Your Goal?"},
                "children": [
                    {"component": "Stack", "props": {"gap": 4}, "children": [
                        {"component": "Text", "props": {"content": "What do you want to be able to DO after we're done?"}},
                        {"component": "TextArea", "props": {"name": "goal", "placeholder": "Something concrete you want to achieve..."}},
                        {"component": "Text", "props": {"variant": "caption", "content": "Examples: 'Price my services confidently', 'Give better presentations'"}},
                        {"component": "Button", "props": {"action": "submit_goal", "label": "Set Goal"}},
                    ]},
                ],
            },
            voice_fallback="What do you want to be able to DO after we're done? Something concrete - not just learn about, but actually do.",
            purpose="Discover learning outcome",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(
            purpose="Help user articulate what they want to be able to DO",
            context={"mode": "outcome_discovery"},
        )

        component_types = get_component_types(result.tree)

        # Should have goal input
        assert "TextArea" in component_types or "TextInput" in component_types
        # Should have submit
        assert "Button" in component_types

        # Voice should focus on action/doing
        fallback = result.voice_fallback.lower()
        assert "do" in fallback


class TestVoiceFallbackQuality:
    """Test voice fallback quality across patterns."""

    def test_voice_fallback_is_not_empty(self, agent, mock_client):
        """Voice fallbacks are never empty."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={"component": "Card", "props": {}, "children": [
                {"component": "Button", "props": {"action": "test", "label": "Test"}},
            ]},
            voice_fallback="Here's a simple card with a test button.",
            purpose="Test",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(purpose="Test purpose", context={})

        assert result.voice_fallback
        assert len(result.voice_fallback) > 0

    def test_voice_fallback_minimum_length(self, agent, mock_client):
        """Voice fallbacks have meaningful content (>20 chars)."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={"component": "Card", "props": {}, "children": [
                {"component": "TextInput", "props": {"name": "test", "label": "Test"}},
                {"component": "Button", "props": {"action": "submit", "label": "Submit"}},
            ]},
            voice_fallback="Please tell me about your situation so I can help you better with this.",
            purpose="Collect information",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(purpose="Collect information", context={})

        assert len(result.voice_fallback) >= 20

    def test_voice_fallback_is_conversational(self, agent, mock_client):
        """Voice fallbacks use natural language."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={"component": "Stack", "props": {}, "children": [
                {"component": "Slider", "props": {"name": "value", "label": "Value"}},
                {"component": "Button", "props": {"action": "confirm", "label": "Confirm"}},
            ]},
            voice_fallback="How would you rate this on a scale of 1 to 10? Just give me a number when you're ready.",
            purpose="Rating input",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(purpose="Get rating input", context={})

        fallback = result.voice_fallback.lower()

        # Should be conversational - contains question words or you/your
        assert any(word in fallback for word in ["how", "what", "would", "your", "you", "?"])

    def test_voice_fallback_avoids_form_language(self, agent, mock_client):
        """Voice fallbacks don't use form/UI terminology."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={"component": "Card", "props": {}, "children": [
                {"component": "TextInput", "props": {"name": "name", "label": "Name"}},
                {"component": "Button", "props": {"action": "save", "label": "Save"}},
            ]},
            voice_fallback="What's your name? Just tell me and we can continue.",
            purpose="Collect name",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(purpose="Collect name input", context={})

        fallback = result.voice_fallback.lower()

        # Should NOT use UI/form language
        form_words = ["field", "input", "select", "click", "button", "form", "submit", "checkbox"]
        for word in form_words:
            assert word not in fallback, f"Voice fallback should not contain '{word}'"


class TestEdgeCases:
    """Test edge cases in UI pattern generation."""

    def test_handles_missing_context(self, agent, mock_client):
        """Agent handles missing context gracefully."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={"component": "Card", "props": {}, "children": [
                {"component": "Text", "props": {"content": "How can I help you today?"}},
                {"component": "Button", "props": {"action": "start", "label": "Start"}},
            ]},
            voice_fallback="How can I help you today?",
            purpose="General start",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        # Should not raise even with no context
        result = agent.generate(purpose="General UI", context=None)

        assert result.tree is not None
        assert result.voice_fallback

    def test_handles_empty_context(self, agent, mock_client):
        """Agent handles empty context dict."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={"component": "Text", "props": {"content": "Ready to help"}},
            voice_fallback="Ready to help. What would you like to work on?",
            purpose="Ready state",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(purpose="General UI", context={})

        assert result.tree is not None

    def test_generates_estimated_interaction_time(self, agent, mock_client):
        """UI specs include estimated interaction time."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={
                "component": "Card",
                "props": {"title": "Complex Form"},
                "children": [
                    {"component": "TextInput", "props": {"name": "field1", "label": "Field 1"}},
                    {"component": "TextInput", "props": {"name": "field2", "label": "Field 2"}},
                    {"component": "TextArea", "props": {"name": "details", "label": "Details"}},
                    {"component": "Button", "props": {"action": "submit", "label": "Submit"}},
                ],
            },
            voice_fallback="I need a few pieces of information from you.",
            purpose="Complex data collection",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(purpose="Complex form", context={})

        assert result.estimated_interaction_time > 0
        assert isinstance(result.estimated_interaction_time, int)


class TestUITreeStructure:
    """Test UI tree structure validation."""

    def test_tree_is_valid_uitreenode(self, agent, mock_client):
        """Generated tree is a valid UITreeNode."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={"component": "Card", "props": {"title": "Test"}},
            voice_fallback="Test UI",
            purpose="Test",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(purpose="Test", context={})

        assert isinstance(result.tree, UITreeNode)
        assert result.tree.component is not None

    def test_nested_children_are_valid(self, agent, mock_client):
        """Nested children in tree are valid UITreeNodes."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={
                "component": "Stack",
                "props": {},
                "children": [
                    {"component": "Text", "props": {"content": "Hello"}},
                    {
                        "component": "Stack",
                        "props": {},
                        "children": [
                            {"component": "Button", "props": {"action": "test", "label": "Nested"}},
                        ],
                    },
                ],
            },
            voice_fallback="Hello with nested button",
            purpose="Nested structure test",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(purpose="Nested test", context={})

        # All nodes should be UITreeNode instances
        all_nodes = flatten_tree(result.tree)
        for node in all_nodes:
            assert isinstance(node, UITreeNode)

    def test_buttons_have_actions(self, agent, mock_client):
        """All buttons in generated UI have action props."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={
                "component": "Stack",
                "props": {},
                "children": [
                    {"component": "Button", "props": {"action": "primary_action", "label": "Primary"}},
                    {"component": "Button", "props": {"action": "secondary_action", "label": "Secondary", "variant": "ghost"}},
                ],
            },
            voice_fallback="Choose primary or secondary action",
            purpose="Multiple buttons",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(purpose="Multiple buttons", context={})

        buttons = get_components_by_type(result.tree, "Button")
        for button in buttons:
            assert "action" in button.props, "All buttons should have an action prop"
            assert button.props["action"], "Button action should not be empty"

    def test_inputs_have_names(self, agent, mock_client):
        """All input components have name props for form data."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=create_mock_ui_response(
            tree_data={
                "component": "Stack",
                "props": {},
                "children": [
                    {"component": "TextInput", "props": {"name": "username", "label": "Username"}},
                    {"component": "Slider", "props": {"name": "rating", "label": "Rating", "min": 1, "max": 10}},
                    {"component": "TextArea", "props": {"name": "comments", "label": "Comments"}},
                ],
            },
            voice_fallback="Enter your username, rating, and any comments",
            purpose="Form with multiple inputs",
        )))]
        mock_client.chat.completions.create.return_value = mock_response

        result = agent.generate(purpose="Form inputs", context={})

        input_types = ["TextInput", "TextArea", "Slider", "Checkbox", "Select"]
        all_nodes = flatten_tree(result.tree)

        for node in all_nodes:
            if node.component in input_types:
                assert "name" in node.props, f"{node.component} should have a name prop"
                assert node.props["name"], f"{node.component} name should not be empty"
