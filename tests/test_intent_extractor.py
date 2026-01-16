"""Tests for the Semantic Intent Extractor."""

from unittest.mock import MagicMock

import pytest

from sage.orchestration.intent_extractor import (
    ExtractedIntent,
    INTENT_SCHEMAS,
    SemanticIntentExtractor,
    _build_extraction_prompt,
    _parse_llm_response,
)


@pytest.fixture
def mock_client():
    """Create mock OpenAI client."""
    return MagicMock()


@pytest.fixture
def extractor(mock_client):
    """Create extractor with mock client."""
    return SemanticIntentExtractor(mock_client, model="test-model")


class TestExtractedIntent:
    """Test ExtractedIntent dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        result = ExtractedIntent(intent="test")
        assert result.intent == "test"
        assert result.data == {}
        assert result.data_complete is False
        assert result.missing_fields == []
        assert result.confidence == 0.0

    def test_custom_values(self):
        """Test custom values are preserved."""
        result = ExtractedIntent(
            intent="session_check_in",
            data={"timeAvailable": "focused", "energyLevel": 75},
            data_complete=True,
            missing_fields=[],
            confidence=0.95,
        )
        assert result.intent == "session_check_in"
        assert result.data["timeAvailable"] == "focused"
        assert result.data["energyLevel"] == 75
        assert result.data_complete is True
        assert result.confidence == 0.95


class TestIntentSchemas:
    """Test INTENT_SCHEMAS definitions."""

    def test_session_check_in_schema(self):
        """Test session_check_in schema structure."""
        schema = INTENT_SCHEMAS["session_check_in"]
        assert "description" in schema
        assert "required" in schema
        assert "optional" in schema
        assert "extraction_hints" in schema
        assert "timeAvailable" in schema["extraction_hints"]
        assert "energyLevel" in schema["extraction_hints"]

    def test_practice_setup_schema(self):
        """Test practice_setup schema structure."""
        schema = INTENT_SCHEMAS["practice_setup"]
        assert "scenario_type" in schema["required"]
        assert "difficulty" in schema["optional"]
        assert schema["extraction_hints"]["difficulty"]["type"] == "enum"

    def test_application_event_schema(self):
        """Test application_event schema structure."""
        schema = INTENT_SCHEMAS["application_event"]
        assert "context" in schema["required"]
        assert "stakes" in schema["optional"]

    def test_verification_schema(self):
        """Test verification schema structure."""
        schema = INTENT_SCHEMAS["verification"]
        assert "answer" in schema["required"]
        assert "confidence" in schema["optional"]

    def test_outcome_discovery_schema(self):
        """Test outcome_discovery schema structure."""
        schema = INTENT_SCHEMAS["outcome_discovery"]
        assert "goal" in schema["optional"]
        assert "motivation" in schema["optional"]

    def test_filter_graph_schema(self):
        """Test filter_graph schema structure."""
        schema = INTENT_SCHEMAS["filter_graph"]
        assert schema["required"] == []  # All fields optional
        assert "show_proven_only" in schema["optional"]
        assert "show_concepts" in schema["optional"]
        assert "show_outcomes" in schema["optional"]
        assert "text_filter" in schema["optional"]
        assert "reset_filters" in schema["optional"]
        # Check mappings exist for boolean fields
        assert schema["extraction_hints"]["show_proven_only"]["type"] == "boolean"
        assert schema["extraction_hints"]["reset_filters"]["type"] == "boolean"

    def test_all_schemas_have_required_keys(self):
        """Test all schemas have required structure."""
        required_keys = {"description", "required", "optional", "extraction_hints"}
        for intent, schema in INTENT_SCHEMAS.items():
            for key in required_keys:
                assert key in schema, f"{intent} missing key: {key}"


class TestBuildExtractionPrompt:
    """Test _build_extraction_prompt function."""

    def test_basic_prompt_generation(self):
        """Test prompt includes input text."""
        prompt = _build_extraction_prompt("I have 30 minutes", None)
        assert "I have 30 minutes" in prompt
        assert "session_check_in" in prompt
        assert "practice_setup" in prompt

    def test_prompt_includes_schemas(self):
        """Test prompt includes schema descriptions."""
        prompt = _build_extraction_prompt("test input", None)
        assert "timeAvailable" in prompt
        assert "energyLevel" in prompt
        assert "scenario_type" in prompt

    def test_prompt_includes_pending_context(self):
        """Test prompt includes pending context when provided."""
        pending = {"timeAvailable": "focused"}
        prompt = _build_extraction_prompt("feeling tired", pending)
        assert "Previously collected data" in prompt
        assert '"timeAvailable": "focused"' in prompt

    def test_prompt_without_pending_context(self):
        """Test prompt without pending context."""
        prompt = _build_extraction_prompt("test input", None)
        assert "Previously collected data" not in prompt


class TestParseLLMResponse:
    """Test _parse_llm_response function."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        response = '{"intent": "session_check_in", "data": {"timeAvailable": "quick"}, "confidence": 0.9}'
        result = _parse_llm_response(response)
        assert result["intent"] == "session_check_in"
        assert result["data"]["timeAvailable"] == "quick"
        assert result["confidence"] == 0.9

    def test_parse_json_with_extra_text(self):
        """Test parsing JSON embedded in other text."""
        response = 'Here is the result: {"intent": "practice_setup", "data": {}, "confidence": 0.5} done'
        result = _parse_llm_response(response)
        assert result["intent"] == "practice_setup"
        assert result["confidence"] == 0.5

    def test_parse_invalid_json(self):
        """Test handling invalid JSON gracefully."""
        result = _parse_llm_response("not valid json at all")
        assert result["intent"] == "unknown"
        assert result["data"] == {}
        assert result["confidence"] == 0.0

    def test_parse_empty_string(self):
        """Test handling empty string."""
        result = _parse_llm_response("")
        assert result["intent"] == "unknown"


class TestSemanticIntentExtractor:
    """Test SemanticIntentExtractor class."""

    def test_init_stores_config(self, mock_client):
        """Test initialization stores configuration."""
        extractor = SemanticIntentExtractor(
            mock_client,
            model="custom-model",
            temperature=0.5,
        )
        assert extractor.model == "custom-model"
        assert extractor.temperature == 0.5

    def test_extract_sync_session_check_in(self, extractor, mock_client):
        """Test sync extraction for session check-in."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"intent": "session_check_in", "data": {"timeAvailable": "focused", "energyLevel": 30}, "confidence": 0.85}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = extractor.extract_sync("I have 30 minutes and feeling tired")

        assert result.intent == "session_check_in"
        assert result.data["timeAvailable"] == "focused"
        assert result.data["energyLevel"] == 30
        assert result.confidence == 0.85
        assert result.data_complete is True  # No required fields

    def test_extract_sync_practice_setup_incomplete(self, extractor, mock_client):
        """Test sync extraction with missing required field."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"intent": "practice_setup", "data": {"difficulty": "hard"}, "confidence": 0.7}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = extractor.extract_sync("I want to do a hard practice")

        assert result.intent == "practice_setup"
        assert result.data_complete is False
        assert "scenario_type" in result.missing_fields

    def test_extract_sync_with_pending_context(self, extractor, mock_client):
        """Test sync extraction merges with pending context."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"intent": "session_check_in", "data": {"energyLevel": 80}, "confidence": 0.9}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = extractor.extract_sync(
            "feeling energized",
            pending_context={"timeAvailable": "deep"},
        )

        assert result.data["timeAvailable"] == "deep"  # From pending
        assert result.data["energyLevel"] == 80  # From extraction

    def test_extract_sync_handles_llm_error(self, extractor, mock_client):
        """Test sync extraction handles LLM errors gracefully."""
        mock_client.chat.completions.create.side_effect = Exception("API error")

        result = extractor.extract_sync("test input")

        assert result.intent == "unknown"
        assert result.confidence == 0.0

    def test_extract_sync_preserves_pending_on_error(self, extractor, mock_client):
        """Test pending context is preserved on error."""
        mock_client.chat.completions.create.side_effect = Exception("API error")

        result = extractor.extract_sync(
            "test input",
            pending_context={"timeAvailable": "quick"},
        )

        assert result.data["timeAvailable"] == "quick"

    def test_extract_sync_unknown_intent(self, extractor, mock_client):
        """Test handling of unknown intent."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"intent": "unknown", "data": {}, "confidence": 0.2}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = extractor.extract_sync("random unrelated text")

        assert result.intent == "unknown"
        assert result.data_complete is True  # No required fields for unknown

    def test_extract_sync_application_event(self, extractor, mock_client):
        """Test extraction for application capture."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"intent": "application_event", "data": {"context": "pricing call tomorrow", "stakes": "high"}, "confidence": 0.92}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = extractor.extract_sync("I have a big pricing call tomorrow")

        assert result.intent == "application_event"
        assert result.data["context"] == "pricing call tomorrow"
        assert result.data["stakes"] == "high"
        assert result.data_complete is True  # context is the only required field

    def test_extract_sync_verification(self, extractor, mock_client):
        """Test extraction for verification response."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"intent": "verification", "data": {"answer": "Start high with room to come down", "confidence": 85}, "confidence": 0.88}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = extractor.extract_sync("My answer is to start high with room to come down")

        assert result.intent == "verification"
        assert "Start high" in result.data["answer"]
        assert result.data_complete is True  # answer is present

    def test_extract_sync_filter_graph_show_proven(self, extractor, mock_client):
        """Test extraction for filter_graph show proven only."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"intent": "filter_graph", "data": {"show_proven_only": true}, "confidence": 0.9}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = extractor.extract_sync("show only proven concepts")

        assert result.intent == "filter_graph"
        assert result.data["show_proven_only"] is True
        assert result.data_complete is True  # No required fields

    def test_extract_sync_filter_graph_hide_outcomes(self, extractor, mock_client):
        """Test extraction for filter_graph hide outcomes."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"intent": "filter_graph", "data": {"show_outcomes": false}, "confidence": 0.85}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = extractor.extract_sync("hide goals")

        assert result.intent == "filter_graph"
        assert result.data["show_outcomes"] is False

    def test_extract_sync_filter_graph_text_filter(self, extractor, mock_client):
        """Test extraction for filter_graph text filter."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"intent": "filter_graph", "data": {"text_filter": "pricing"}, "confidence": 0.88}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = extractor.extract_sync("filter by pricing")

        assert result.intent == "filter_graph"
        assert result.data["text_filter"] == "pricing"

    def test_extract_sync_filter_graph_reset(self, extractor, mock_client):
        """Test extraction for filter_graph reset filters."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"intent": "filter_graph", "data": {"reset_filters": true}, "confidence": 0.92}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = extractor.extract_sync("show everything")

        assert result.intent == "filter_graph"
        assert result.data["reset_filters"] is True


@pytest.mark.asyncio
class TestSemanticIntentExtractorAsync:
    """Test async methods of SemanticIntentExtractor."""

    async def test_extract_async_basic(self, extractor, mock_client):
        """Test async extraction works correctly."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"intent": "session_check_in", "data": {"timeAvailable": "quick"}, "confidence": 0.8}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = await extractor.extract("I only have 15 minutes")

        assert result.intent == "session_check_in"
        assert result.data["timeAvailable"] == "quick"

    async def test_extract_async_with_pending(self, extractor, mock_client):
        """Test async extraction with pending context."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"intent": "session_check_in", "data": {"mindset": "excited"}, "confidence": 0.75}'
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        result = await extractor.extract(
            "feeling excited about learning",
            pending_context={"timeAvailable": "focused", "energyLevel": 70},
        )

        assert result.data["timeAvailable"] == "focused"
        assert result.data["energyLevel"] == 70
        assert result.data["mindset"] == "excited"

    async def test_extract_async_handles_error(self, extractor, mock_client):
        """Test async extraction handles errors gracefully."""
        mock_client.chat.completions.create.side_effect = Exception("Network error")

        result = await extractor.extract("test input")

        assert result.intent == "unknown"
        assert result.confidence == 0.0
