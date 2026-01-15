"""Models for orchestration layer.

This module defines models for the UI Generation Agent and orchestration.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from sage.dialogue.structured_output import UITreeNode


class UITreeSpec(BaseModel):
    """Complete UI specification from the UI Generation Agent.

    This wraps a UITreeNode with metadata needed for voice parity
    and interaction tracking.

    Example:
        UITreeSpec(
            tree=UITreeNode(component="Card", props={"title": "Check-in"}, children=[...]),
            voice_fallback="How are you showing up today? How much time do you have?",
            purpose="Collect session context for personalized learning",
            estimated_interaction_time=30,
        )
    """

    tree: UITreeNode = Field(description="The composable UI component tree")
    voice_fallback: str = Field(
        description="Full voice alternative for users who can't see the UI"
    )
    purpose: str = Field(description="What this UI accomplishes")
    estimated_interaction_time: int = Field(
        default=30, description="Expected seconds to complete UI interaction"
    )


class UIGenerationRequest(BaseModel):
    """Request for UI generation.

    Contains the purpose and context needed to generate an appropriate UI.
    """

    purpose: str = Field(description="What the UI should accomplish")
    mode: Optional[str] = Field(default=None, description="Current dialogue mode")
    energy_level: Optional[str] = Field(default=None, description="Learner's energy level")
    time_available: Optional[str] = Field(default=None, description="Time available for session")
    recent_topic: Optional[str] = Field(default=None, description="Recent conversation topic")
    requirements: Optional[str] = Field(default=None, description="Specific UI requirements")


class UIGenerationHint(BaseModel):
    """Hint from the main LLM that UI would be helpful.

    The main conversation LLM returns this when it determines
    that showing a UI would be more effective than text.
    """

    should_show_ui: bool = Field(
        default=False, description="Whether to show a UI"
    )
    ui_purpose: Optional[str] = Field(
        default=None, description="What the UI should accomplish"
    )
    ui_requirements: Optional[str] = Field(
        default=None, description="Specific requirements for the UI"
    )
