"""Tests for the UI Generation Agent."""

import json
from unittest.mock import MagicMock, AsyncMock

import pytest

from sage.dialogue.structured_output import UITreeNode
from sage.orchestration.models import UIGenerationRequest, UITreeSpec
from sage.orchestration.ui_agent import (
    UIGenerationAgent,
    UI_AGENT_SYSTEM_PROMPT,
    create_ui_agent,
)


@pytest.fixture
def mock_client():
    """Create mock OpenAI client."""
    return MagicMock()


@pytest.fixture
def agent(mock_client):
    """Create agent with mock client."""
    return UIGenerationAgent(mock_client, model="test-model")


class TestUITreeSpec:
    """Test UITreeSpec model."""

    def test_basic_creation(self):
        """Test creating a basic UITreeSpec."""
        tree = UITreeNode(component="Text", props={"content": "Hello"})
        spec = UITreeSpec(
            tree=tree,
            voice_fallback="Hello",
            purpose="Display greeting",
        )
        assert spec.tree.component == "Text"
        assert spec.voice_fallback == "Hello"
        assert spec.purpose == "Display greeting"
        assert spec.estimated_interaction_time == 30  # Default

    def test_custom_interaction_time(self):
        """Test custom estimated interaction time."""
        tree = UITreeNode(component="Card", props={})
        spec = UITreeSpec(
            tree=tree,
            voice_fallback="Check-in form",
            purpose="Collect session context",
            estimated_interaction_time=60,
        )
        assert spec.estimated_interaction_time == 60

    def test_nested_tree_structure(self):
        """Test nested UITreeNode structure."""
        tree = UITreeNode(
            component="Stack",
            props={"gap": 4},
            children=[
                UITreeNode(component="Text", props={"content": "Title"}),
                UITreeNode(component="Button", props={"label": "Submit", "action": "submit"}),
            ],
        )
        spec = UITreeSpec(
            tree=tree,
            voice_fallback="Title. Submit button.",
            purpose="Simple form",
        )
        assert len(spec.tree.children) == 2
        assert spec.tree.children[0].component == "Text"
        assert spec.tree.children[1].component == "Button"


class TestUIGenerationRequest:
    """Test UIGenerationRequest model."""

    def test_minimal_request(self):
        """Test creating request with just purpose."""
        request = UIGenerationRequest(purpose="Collect check-in data")
        assert request.purpose == "Collect check-in data"
        assert request.mode is None
        assert request.energy_level is None

    def test_full_request(self):
        """Test creating request with all fields."""
        request = UIGenerationRequest(
            purpose="Collect check-in data",
            mode="check_in",
            energy_level="high",
            time_available="focused",
            recent_topic="pricing strategies",
            requirements="Include energy slider",
        )
        assert request.purpose == "Collect check-in data"
        assert request.mode == "check_in"
        assert request.energy_level == "high"
        assert request.time_available == "focused"
        assert request.recent_topic == "pricing strategies"
        assert request.requirements == "Include energy slider"


class TestUIGenerationAgent:
    """Test UIGenerationAgent class."""

    def test_initialization(self, mock_client):
        """Test agent initialization."""
        agent = UIGenerationAgent(mock_client)
        assert agent.model == "grok-2"
        assert agent.max_tokens == 1000
        assert agent.temperature == 0.3

    def test_custom_initialization(self, mock_client):
        """Test agent with custom settings."""
        agent = UIGenerationAgent(
            mock_client,
            model="custom-model",
            max_tokens=500,
            temperature=0.5,
        )
        assert agent.model == "custom-model"
        assert agent.max_tokens == 500
        assert agent.temperature == 0.5

    def test_build_user_prompt_minimal(self, agent):
        """Test building user prompt with minimal context."""
        request = UIGenerationRequest(purpose="Test purpose")
        prompt = agent._build_user_prompt(request)

        assert "Test purpose" in prompt
        assert "No additional context" in prompt

    def test_build_user_prompt_full_context(self, agent):
        """Test building user prompt with full context."""
        request = UIGenerationRequest(
            purpose="Collect session data",
            mode="check_in",
            energy_level="medium",
            time_available="focused",
            recent_topic="negotiation",
            requirements="simple form",
        )
        prompt = agent._build_user_prompt(request)

        assert "Collect session data" in prompt
        assert "check_in" in prompt
        assert "medium" in prompt
        assert "focused" in prompt
        assert "negotiation" in prompt
        assert "simple form" in prompt

    def test_parse_response_valid(self, agent):
        """Test parsing valid JSON response."""
        response_json = json.dumps({
            "tree": {
                "component": "Card",
                "props": {"title": "Check-in"},
                "children": [
                    {"component": "Text", "props": {"content": "How are you?"}}
                ],
            },
            "voice_fallback": "How are you showing up today?",
            "purpose": "Session check-in",
            "estimated_interaction_time": 45,
        })

        spec = agent._parse_response(response_json)

        assert spec.tree.component == "Card"
        assert spec.tree.props["title"] == "Check-in"
        assert len(spec.tree.children) == 1
        assert spec.voice_fallback == "How are you showing up today?"
        assert spec.purpose == "Session check-in"
        assert spec.estimated_interaction_time == 45

    def test_parse_response_minimal(self, agent):
        """Test parsing response with minimal fields."""
        response_json = json.dumps({
            "tree": {"component": "Text", "props": {"content": "Hello"}},
            "voice_fallback": "Hello",
            "purpose": "Greeting",
        })

        spec = agent._parse_response(response_json)

        assert spec.tree.component == "Text"
        assert spec.estimated_interaction_time == 30  # Default

    def test_parse_response_invalid_json(self, agent):
        """Test parsing invalid JSON raises error."""
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            agent._parse_response("not valid json")

    def test_parse_response_invalid_structure(self, agent):
        """Test parsing invalid structure raises error."""
        with pytest.raises(ValueError, match="Failed to validate"):
            agent._parse_response(json.dumps({"invalid": "structure"}))

    def test_generate_sync(self, agent, mock_client):
        """Test synchronous generation."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "tree": {"component": "Card", "props": {}},
                        "voice_fallback": "A card",
                        "purpose": "Display card",
                    })
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        spec = agent.generate("Test purpose")

        assert spec.tree.component == "Card"
        assert spec.voice_fallback == "A card"
        mock_client.chat.completions.create.assert_called_once()

        # Verify call arguments
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"

    def test_generate_with_context(self, agent, mock_client):
        """Test generation with context dict."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "tree": {"component": "Stack", "props": {}},
                        "voice_fallback": "Form content",
                        "purpose": "Data collection",
                    })
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        spec = agent.generate(
            "Collect data",
            context={
                "mode": "check_in",
                "energy_level": "high",
            },
        )

        assert spec.tree.component == "Stack"

        # Verify context was included in prompt
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        user_prompt = call_kwargs["messages"][1]["content"]
        assert "check_in" in user_prompt
        assert "high" in user_prompt

    def test_generate_empty_response_raises(self, agent, mock_client):
        """Test that empty response raises error."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]
        mock_client.chat.completions.create.return_value = mock_response

        with pytest.raises(ValueError, match="Empty response"):
            agent.generate("Test")

    def test_generate_api_error_propagates(self, agent, mock_client):
        """Test that API errors propagate."""
        mock_client.chat.completions.create.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            agent.generate("Test")


class TestUIAgentSystemPrompt:
    """Test the system prompt content."""

    def test_includes_layout_components(self):
        """Test system prompt includes layout primitives."""
        assert "Stack:" in UI_AGENT_SYSTEM_PROMPT
        assert "Grid:" in UI_AGENT_SYSTEM_PROMPT
        assert "Card:" in UI_AGENT_SYSTEM_PROMPT
        assert "Divider:" in UI_AGENT_SYSTEM_PROMPT

    def test_includes_typography_components(self):
        """Test system prompt includes typography primitives."""
        assert "Text:" in UI_AGENT_SYSTEM_PROMPT
        assert "Markdown:" in UI_AGENT_SYSTEM_PROMPT

    def test_includes_input_components(self):
        """Test system prompt includes input primitives."""
        assert "TextInput:" in UI_AGENT_SYSTEM_PROMPT
        assert "TextArea:" in UI_AGENT_SYSTEM_PROMPT
        assert "Slider:" in UI_AGENT_SYSTEM_PROMPT
        assert "RadioGroup:" in UI_AGENT_SYSTEM_PROMPT
        assert "Radio:" in UI_AGENT_SYSTEM_PROMPT
        assert "Checkbox:" in UI_AGENT_SYSTEM_PROMPT
        assert "Select:" in UI_AGENT_SYSTEM_PROMPT

    def test_includes_action_components(self):
        """Test system prompt includes action primitives."""
        assert "Button:" in UI_AGENT_SYSTEM_PROMPT
        assert "ButtonGroup:" in UI_AGENT_SYSTEM_PROMPT

    def test_includes_display_components(self):
        """Test system prompt includes display primitives."""
        assert "ImageDisplay:" in UI_AGENT_SYSTEM_PROMPT
        assert "Table:" in UI_AGENT_SYSTEM_PROMPT
        assert "ProgressBar:" in UI_AGENT_SYSTEM_PROMPT
        assert "Badge:" in UI_AGENT_SYSTEM_PROMPT

    def test_includes_output_format(self):
        """Test system prompt specifies output format."""
        assert "tree:" in UI_AGENT_SYSTEM_PROMPT
        assert "voice_fallback:" in UI_AGENT_SYSTEM_PROMPT
        assert "purpose:" in UI_AGENT_SYSTEM_PROMPT
        assert "estimated_interaction_time:" in UI_AGENT_SYSTEM_PROMPT

    def test_includes_rules(self):
        """Test system prompt includes rules."""
        assert "RULES:" in UI_AGENT_SYSTEM_PROMPT
        assert "Button" in UI_AGENT_SYSTEM_PROMPT
        assert "action" in UI_AGENT_SYSTEM_PROMPT


class TestCreateUIAgent:
    """Test the create_ui_agent factory function."""

    def test_creates_sync_agent(self):
        """Test creating synchronous agent."""
        agent = create_ui_agent(api_key="test-key", async_client=False)
        assert isinstance(agent, UIGenerationAgent)
        assert agent.model == "grok-2"

    def test_creates_async_agent(self):
        """Test creating async agent."""
        agent = create_ui_agent(api_key="test-key", async_client=True)
        assert isinstance(agent, UIGenerationAgent)

    def test_custom_base_url(self):
        """Test creating agent with custom base URL."""
        agent = create_ui_agent(
            api_key="test-key",
            base_url="https://custom.api.com/v1",
        )
        assert isinstance(agent, UIGenerationAgent)


@pytest.mark.asyncio
class TestUIGenerationAgentAsync:
    """Test async methods of UIGenerationAgent."""

    async def test_generate_async_with_async_client(self):
        """Test async generation with AsyncOpenAI client."""
        from openai import AsyncOpenAI

        mock_client = MagicMock(spec=AsyncOpenAI)
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "tree": {"component": "Card", "props": {}},
                        "voice_fallback": "Test",
                        "purpose": "Test",
                    })
                )
            )
        ]

        # Create async mock that returns the response
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        agent = UIGenerationAgent(mock_client, model="test")
        spec = await agent.generate_async("Test purpose")

        assert spec.tree.component == "Card"
        mock_client.chat.completions.create.assert_awaited_once()

    async def test_generate_async_with_sync_client_fallback(self):
        """Test async generation falls back for sync client."""
        mock_client = MagicMock()  # Not spec=AsyncOpenAI
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "tree": {"component": "Text", "props": {"content": "Hello"}},
                        "voice_fallback": "Hello",
                        "purpose": "Greeting",
                    })
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        agent = UIGenerationAgent(mock_client, model="test")
        spec = await agent.generate_async("Test")

        assert spec.tree.component == "Text"


class TestUITreeNodeValidation:
    """Test UITreeNode validation scenarios."""

    def test_valid_simple_node(self):
        """Test valid simple node."""
        node = UITreeNode(component="Text", props={"content": "Hello"})
        assert node.component == "Text"
        assert node.props["content"] == "Hello"
        assert node.children is None

    def test_valid_node_with_children(self):
        """Test valid node with children."""
        node = UITreeNode(
            component="Stack",
            props={"gap": 4},
            children=[
                UITreeNode(component="Text", props={"content": "A"}),
                UITreeNode(component="Text", props={"content": "B"}),
            ],
        )
        assert len(node.children) == 2

    def test_empty_props(self):
        """Test node with empty props."""
        node = UITreeNode(component="Divider")
        assert node.props == {}

    def test_deeply_nested_structure(self):
        """Test deeply nested structure."""
        node = UITreeNode(
            component="Card",
            props={"title": "Form"},
            children=[
                UITreeNode(
                    component="Stack",
                    props={},
                    children=[
                        UITreeNode(
                            component="Grid",
                            props={"columns": 2},
                            children=[
                                UITreeNode(component="Text", props={"content": "A"}),
                                UITreeNode(component="Text", props={"content": "B"}),
                            ],
                        ),
                    ],
                ),
            ],
        )
        assert node.component == "Card"
        assert node.children[0].component == "Stack"
        assert node.children[0].children[0].component == "Grid"
        assert len(node.children[0].children[0].children) == 2
