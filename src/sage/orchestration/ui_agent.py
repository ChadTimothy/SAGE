"""UI Generation Agent for SAGE.

This module implements a fast, composition-aware UI generation agent
that can construct arbitrary UIs from primitive components based on
conversation context.

Key design principles:
- Tool, not monitor: Called by orchestrator when UI would help
- Composition-aware: Builds trees from primitives, not fixed templates
- Fast: Target <500ms using Grok-2
- Voice-first: Every UI includes voice_fallback
- Context-aware: Uses conversation context to generate relevant UIs
"""

import json
import logging
import time
from typing import Any, Optional

from openai import AsyncOpenAI, OpenAI
from pydantic import ValidationError

from sage.dialogue.structured_output import UITreeNode
from sage.orchestration.models import UIGenerationRequest, UITreeSpec


logger = logging.getLogger(__name__)


# System prompt documenting all available primitives
UI_AGENT_SYSTEM_PROMPT = """You are a UI generation agent for SAGE, an AI tutor.

You generate UI component trees using these primitives:

LAYOUT:
- Stack: { direction: "vertical"|"horizontal", gap: 1-12, align: "start"|"center"|"end"|"stretch" }
- Grid: { columns: 1-4, gap: 1-12 }
- Card: { title?: string, variant?: "default"|"highlight"|"warning" }
- Divider: { label?: string }

TYPOGRAPHY:
- Text: { content: string, variant: "heading"|"subheading"|"body"|"caption"|"label", color?: "default"|"muted"|"accent"|"success"|"warning"|"error" }
- Markdown: { content: string }

INPUTS:
- TextInput: { name: string, label: string, placeholder?: string, required?: boolean }
- TextArea: { name: string, label: string, placeholder?: string, rows?: number }
- Slider: { name: string, label: string, min?: number, max?: number, leftEmoji?: string, rightEmoji?: string }
- RadioGroup: { name: string, label?: string } with Radio children
- Radio: { value: string, label: string, description?: string }
- Checkbox: { name: string, label: string }
- Select: { name: string, label: string, options: [{value, label}] }

ACTIONS:
- Button: { action: string, label: string, variant?: "primary"|"secondary"|"ghost" }
- ButtonGroup: {} (contains Button children)

DISPLAY:
- ImageDisplay: { src: string, alt: string, caption?: string }
- Table: { columns: [{key, header}], rows: [{...}] }
- ProgressBar: { value: number, max?: number, label?: string }
- Badge: { label: string, variant?: "default"|"success"|"warning"|"error" }

RULES:
1. Every form MUST have a Button with an action
2. Use Stack for most layouts (vertical by default)
3. Use Card to group related content
4. Keep UIs simple - prefer fewer fields over many
5. Include descriptive labels and placeholders
6. Consider the user's context (energy level, time available)
7. All input components MUST have a unique "name" prop for form data

OUTPUT FORMAT:
Return a JSON object with:
- tree: The UITreeNode structure
- voice_fallback: How to present this UI conversationally (for voice-only users)
- purpose: What this UI accomplishes
- estimated_interaction_time: Seconds expected (default 30)

IMPORTANT: Your voice_fallback MUST be a complete, natural-sounding alternative that asks the same questions or presents the same information as the UI. It should be something SAGE would actually say to a learner.
"""


class UIGenerationAgent:
    """Generates arbitrary UIs from primitives using Grok-2.

    This agent is called as a tool by the orchestrator when it determines
    that showing a UI would be more effective than text responses.

    Example:
        agent = UIGenerationAgent(client)
        spec = await agent.generate_async(
            purpose="Collect session check-in data",
            context={"mode": "check_in", "energy_level": "medium"}
        )
        # spec.tree is the UITreeNode, spec.voice_fallback is the voice alternative
    """

    MODEL = "grok-2"  # Fast model for quick generation
    MAX_TOKENS = 1000
    TEMPERATURE = 0.3  # Lower for consistent structure

    def __init__(
        self,
        client: OpenAI | AsyncOpenAI,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ):
        """Initialize the UI generation agent.

        Args:
            client: OpenAI-compatible client (sync or async)
            model: Model to use (default: grok-2)
            max_tokens: Max tokens for response (default: 1000)
            temperature: Temperature for generation (default: 0.3)
        """
        self.client = client
        self.model = model or self.MODEL
        self.max_tokens = max_tokens or self.MAX_TOKENS
        self.temperature = temperature or self.TEMPERATURE

    def _build_user_prompt(self, request: UIGenerationRequest) -> str:
        """Build the user prompt from the generation request."""
        context_parts = []
        if request.mode:
            context_parts.append(f"- Current dialogue mode: {request.mode}")
        if request.energy_level:
            context_parts.append(f"- User energy level: {request.energy_level}")
        if request.time_available:
            context_parts.append(f"- Time available: {request.time_available}")
        if request.recent_topic:
            context_parts.append(f"- Recent topic: {request.recent_topic}")
        if request.requirements:
            context_parts.append(f"- Specific requirements: {request.requirements}")

        context_str = "\n".join(context_parts) if context_parts else "No additional context"

        return f"""Generate a UI for: {request.purpose}

Context:
{context_str}

Generate a focused, appropriate UI that serves this purpose."""

    def _parse_response(self, content: str) -> UITreeSpec:
        """Parse the LLM response into a UITreeSpec.

        Args:
            content: The raw JSON content from the LLM

        Returns:
            Validated UITreeSpec

        Raises:
            ValueError: If parsing fails
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}") from e

        try:
            # Recursively validate the tree structure
            tree_data = data.get("tree", {})
            tree = UITreeNode.model_validate(tree_data)

            return UITreeSpec(
                tree=tree,
                voice_fallback=data.get("voice_fallback", ""),
                purpose=data.get("purpose", ""),
                estimated_interaction_time=data.get("estimated_interaction_time", 30),
            )
        except ValidationError as e:
            raise ValueError(f"Failed to validate UI spec: {e}") from e

    def generate(
        self,
        purpose: str,
        context: Optional[dict[str, Any]] = None,
    ) -> UITreeSpec:
        """Generate a UI tree for the given purpose and context (sync).

        Args:
            purpose: What the UI should accomplish
            context: Optional context dict with mode, energy_level, etc.

        Returns:
            UITreeSpec with tree, voice_fallback, purpose, and estimated_interaction_time

        Raises:
            ValueError: If generation or parsing fails
        """
        request = UIGenerationRequest(
            purpose=purpose,
            mode=context.get("mode") if context else None,
            energy_level=context.get("energy_level") if context else None,
            time_available=context.get("time_available") if context else None,
            recent_topic=context.get("recent_topic") if context else None,
            requirements=context.get("requirements") if context else None,
        )

        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": UI_AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": self._build_user_prompt(request)},
                ],
                response_format={"type": "json_object"},
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            elapsed = (time.time() - start_time) * 1000
            logger.info(f"UI generation completed in {elapsed:.0f}ms")

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from LLM")

            return self._parse_response(content)

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"UI generation failed after {elapsed:.0f}ms: {e}")
            raise

    async def generate_async(
        self,
        purpose: str,
        context: Optional[dict[str, Any]] = None,
    ) -> UITreeSpec:
        """Generate a UI tree for the given purpose and context (async).

        Args:
            purpose: What the UI should accomplish
            context: Optional context dict with mode, energy_level, etc.

        Returns:
            UITreeSpec with tree, voice_fallback, purpose, and estimated_interaction_time

        Raises:
            ValueError: If generation or parsing fails
        """
        request = UIGenerationRequest(
            purpose=purpose,
            mode=context.get("mode") if context else None,
            energy_level=context.get("energy_level") if context else None,
            time_available=context.get("time_available") if context else None,
            recent_topic=context.get("recent_topic") if context else None,
            requirements=context.get("requirements") if context else None,
        )

        start_time = time.time()

        try:
            # For async client, we need to use async method
            if isinstance(self.client, AsyncOpenAI):
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": UI_AGENT_SYSTEM_PROMPT},
                        {"role": "user", "content": self._build_user_prompt(request)},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
            else:
                # Fall back to sync for non-async client
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": UI_AGENT_SYSTEM_PROMPT},
                        {"role": "user", "content": self._build_user_prompt(request)},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )

            elapsed = (time.time() - start_time) * 1000
            logger.info(f"UI generation completed in {elapsed:.0f}ms")

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from LLM")

            return self._parse_response(content)

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"UI generation failed after {elapsed:.0f}ms: {e}")
            raise


def create_ui_agent(
    api_key: str,
    base_url: str = "https://api.x.ai/v1",
    async_client: bool = False,
) -> UIGenerationAgent:
    """Create a UI generation agent with default configuration.

    Args:
        api_key: API key for the LLM provider
        base_url: Base URL for the LLM API
        async_client: Whether to use async client

    Returns:
        Configured UIGenerationAgent
    """
    if async_client:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    else:
        client = OpenAI(api_key=api_key, base_url=base_url)

    return UIGenerationAgent(client)
