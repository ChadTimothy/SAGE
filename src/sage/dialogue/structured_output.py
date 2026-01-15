"""Structured output models and parsing for SAGE.

This module defines SAGEResponse - the structured output the LLM
returns each turn - and utilities for parsing and validating it.

Also includes ExtendedSAGEResponse for voice/UI parity with
composable UI trees and voice optimization hints.
"""

import logging
from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field

from sage.graph.models import DialogueMode, SessionContext


logger = logging.getLogger(__name__)


# =============================================================================
# State Update Models (returned by LLM)
# =============================================================================


class GapIdentified(BaseModel):
    """A gap/concept identified during probing."""

    name: str = Field(description="Machine-readable name (lowercase, hyphenated)")
    display_name: str = Field(description="Human-readable name")
    description: str = Field(description="What this gap is about")
    blocking_outcome_id: Optional[str] = Field(
        default=None, description="The outcome this gap blocks"
    )


class ProofExchange(BaseModel):
    """The exchange that led to a proof being earned."""

    prompt: str = Field(description="The verification question/challenge")
    response: str = Field(description="The learner's response")
    analysis: str = Field(description="Why this demonstrates understanding")


class ProofEarned(BaseModel):
    """A proof earned during verification."""

    concept_id: str = Field(description="ID of the concept proven")
    demonstration_type: str = Field(
        description="How understanding was shown: explanation, application, or both"
    )
    evidence: str = Field(description="Summary of what they demonstrated")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in understanding")
    exchange: ProofExchange = Field(description="The verification exchange")


class ConnectionDiscovered(BaseModel):
    """A connection discovered between concepts."""

    from_concept_id: str = Field(description="ID of the source concept")
    to_concept_id: str = Field(description="ID of the target concept")
    relationship: str = Field(description="How they relate (builds_on, contrasts, etc.)")
    strength: float = Field(ge=0.0, le=1.0, description="Relevance strength")
    used_in_teaching: bool = Field(
        default=False, description="Was this connection used in explanation?"
    )


class ApplicationDetected(BaseModel):
    """An upcoming application detected in conversation."""

    context: str = Field(description="What application (e.g., 'pricing call tomorrow')")
    concept_ids: list[str] = Field(
        default_factory=list, description="Concepts being applied"
    )
    planned_date: Optional[date] = Field(
        default=None, description="When the application is planned"
    )
    stakes: Optional[str] = Field(
        default=None, description="How high-stakes: high, medium, low"
    )


class FollowupResponse(BaseModel):
    """Response from following up on a past application."""

    event_id: str = Field(description="ID of the application event")
    outcome_result: str = Field(
        description="How it went: went_well, struggled, or mixed"
    )
    what_worked: Optional[str] = Field(default=None, description="What went well")
    what_struggled: Optional[str] = Field(
        default=None, description="What they struggled with"
    )
    gaps_revealed: list[str] = Field(
        default_factory=list, description="New gaps identified from struggles"
    )
    insights: Optional[str] = Field(
        default=None, description="Learner's own reflection"
    )


class StateChange(BaseModel):
    """A detected change in learner state mid-session."""

    what_changed: str = Field(
        description="What changed: energy_drop, time_pressure, confusion, etc."
    )
    detected_from: str = Field(description="How this was detected")
    recommended_adaptation: str = Field(description="How to adapt")


# =============================================================================
# SAGE Response (Main Output Model)
# =============================================================================


class SAGEResponse(BaseModel):
    """Structured output from SAGE each turn.

    This is what the LLM returns, containing both the user-facing
    message and structured data for state updates.
    """

    # === THE RESPONSE ===
    message: str = Field(description="What the user sees")

    # === MODE ===
    current_mode: DialogueMode = Field(description="Current dialogue mode")
    transition_to: Optional[DialogueMode] = Field(
        default=None, description="Mode to transition to (if any)"
    )
    transition_reason: Optional[str] = Field(
        default=None, description="Why the transition"
    )

    # === STATE UPDATES ===
    gap_identified: Optional[GapIdentified] = Field(
        default=None, description="New gap found (in PROBING mode)"
    )
    proof_earned: Optional[ProofEarned] = Field(
        default=None, description="Proof earned (in VERIFICATION mode)"
    )
    connection_discovered: Optional[ConnectionDiscovered] = Field(
        default=None, description="Connection between concepts found"
    )

    # === APPLICATION TRACKING ===
    application_detected: Optional[ApplicationDetected] = Field(
        default=None, description="Upcoming real-world application"
    )
    followup_response: Optional[FollowupResponse] = Field(
        default=None, description="Response to follow-up question"
    )

    # === CONTEXT UPDATES ===
    state_change_detected: Optional[StateChange] = Field(
        default=None, description="Mid-session state change"
    )
    context_update: Optional[SessionContext] = Field(
        default=None, description="Updated session context"
    )

    # === OUTCOME ===
    outcome_achieved: bool = Field(
        default=False, description="Has the learner achieved their outcome?"
    )
    outcome_reasoning: Optional[str] = Field(
        default=None, description="Why outcome is/isn't achieved"
    )

    # === LEARNING ===
    teaching_approach_used: Optional[str] = Field(
        default=None, description="Teaching approach for insights tracking"
    )

    # === DEBUG ===
    reasoning: Optional[str] = Field(
        default=None, description="Internal reasoning (debug only)"
    )


# =============================================================================
# Voice/UI Parity Models (for ExtendedSAGEResponse)
# =============================================================================


class UITreeNode(BaseModel):
    """A node in the composable UI component tree.

    The UI tree is recursive, allowing arbitrary nesting of components.
    The frontend renders this tree using a primitive component library.

    Example:
        UITreeNode(
            component="Stack",
            props={"gap": 4},
            children=[
                UITreeNode(component="Text", props={"content": "Hello"}),
                UITreeNode(component="Button", props={"label": "Click me"}),
            ]
        )
    """

    component: str = Field(description="Primitive component name (Stack, Text, Button, etc.)")
    props: dict[str, Any] = Field(
        default_factory=dict, description="Component properties"
    )
    children: Optional[list["UITreeNode"]] = Field(
        default=None, description="Child nodes (for container components)"
    )


# Resolve forward references for recursive type
UITreeNode.model_rebuild()


class VoiceHints(BaseModel):
    """Hints for text-to-speech optimization.

    These hints help the voice synthesizer produce more natural speech.
    The voice_fallback provides a complete conversational alternative
    for users who can't see the UI.
    """

    voice_fallback: Optional[str] = Field(
        default=None, description="Full voice alternative for UI-based content"
    )
    emphasis: list[str] = Field(
        default_factory=list, description="Words to emphasize in speech"
    )
    pause_after: list[str] = Field(
        default_factory=list, description="Words after which to pause"
    )
    tone: str = Field(default="neutral", description="Suggested emotional tone")
    slower: bool = Field(default=False, description="Request slower speech rate")


class PendingDataRequest(BaseModel):
    """Tracks incomplete data collection across conversation turns.

    When collecting structured data (like session check-in), this tracks
    what we've gathered so far and what's still missing. This enables:
    - Multi-turn data collection
    - Cross-modality state sync (voice -> UI prefill)
    - Validation feedback
    """

    intent: str = Field(description="What we're trying to collect (e.g., 'session_check_in')")
    collected_data: dict[str, Any] = Field(
        default_factory=dict, description="Data collected so far"
    )
    missing_fields: list[str] = Field(
        default_factory=list, description="Fields still needed"
    )
    validation_errors: list[str] = Field(
        default_factory=list, description="Validation errors to show user"
    )


class ExtendedSAGEResponse(SAGEResponse):
    """Enhanced SAGE response supporting voice/UI parity.

    Extends SAGEResponse with:
    - ui_tree: Composable UI tree for ad-hoc UI generation
    - voice_hints: TTS optimization hints
    - pending_data_request: State for multi-turn data collection

    The UI Generation Agent creates ui_tree from ~15 primitive
    components, enabling any UI to be generated dynamically.
    """

    # === UI TREE (Ad-hoc UI generation) ===
    ui_tree: Optional[UITreeNode] = Field(
        default=None, description="Composable UI tree for rendering"
    )

    # === VOICE HINTS ===
    voice_hints: Optional[VoiceHints] = Field(
        default=None, description="TTS optimization hints"
    )

    # === DATA COLLECTION STATE ===
    pending_data_request: Optional[PendingDataRequest] = Field(
        default=None, description="Incomplete data collection state"
    )

    # === UI METADATA ===
    ui_purpose: Optional[str] = Field(
        default=None, description="What the UI accomplishes"
    )
    estimated_interaction_time: Optional[int] = Field(
        default=None, description="Expected seconds to complete UI interaction"
    )


# =============================================================================
# Parsing and Validation
# =============================================================================


def parse_sage_response(response_data: dict) -> SAGEResponse:
    """Parse a response dict into SAGEResponse.

    Args:
        response_data: The response data (from JSON or structured output)

    Returns:
        Validated SAGEResponse

    Raises:
        ValidationError: If response doesn't match schema
    """
    return SAGEResponse.model_validate(response_data)


def create_fallback_response(
    mode: DialogueMode,
    error: Optional[Exception] = None,
) -> SAGEResponse:
    """Create a safe fallback response when parsing fails.

    Args:
        mode: The current dialogue mode
        error: The error that occurred (for logging)

    Returns:
        A safe response that continues the conversation
    """
    if error:
        logger.error(f"Creating fallback response due to error: {error}")

    return SAGEResponse(
        message="I need a moment to gather my thoughts. Could you repeat that?",
        current_mode=mode,
        reasoning=f"Fallback response: {error}" if error else None,
    )


def validate_response_consistency(
    response: SAGEResponse,
    expected_mode: DialogueMode,
) -> list[str]:
    """Validate that the response is internally consistent.

    Checks:
    - Proofs should only be earned in VERIFICATION mode
    - Gaps should only be identified in PROBING mode
    - Mode transitions follow valid paths

    Args:
        response: The response to validate
        expected_mode: The mode we expected to be in

    Returns:
        List of warning messages (empty if consistent)
    """
    warnings = []

    # Mode consistency
    if response.current_mode != expected_mode:
        warnings.append(
            f"Mode mismatch: expected {expected_mode}, got {response.current_mode}"
        )

    # Proof earned outside VERIFICATION
    if response.proof_earned and response.current_mode != DialogueMode.VERIFICATION:
        warnings.append(
            f"Proof earned in {response.current_mode} mode (expected VERIFICATION)"
        )

    # Gap identified outside PROBING
    if response.gap_identified and response.current_mode != DialogueMode.PROBING:
        warnings.append(
            f"Gap identified in {response.current_mode} mode (expected PROBING)"
        )

    # Followup response outside FOLLOWUP
    if response.followup_response and response.current_mode != DialogueMode.FOLLOWUP:
        warnings.append(
            f"Followup response in {response.current_mode} mode (expected FOLLOWUP)"
        )

    # Valid mode transitions
    if response.transition_to:
        valid = get_valid_transitions(response.current_mode)
        if response.transition_to not in valid:
            warnings.append(
                f"Invalid transition: {response.current_mode} -> {response.transition_to}. "
                f"Valid: {[m.value for m in valid]}"
            )

    return warnings


def get_valid_transitions(from_mode: DialogueMode) -> list[DialogueMode]:
    """Get valid transitions from a mode.

    Uses MODE_BEHAVIORS as the single source of truth.

    Args:
        from_mode: The current mode

    Returns:
        List of valid modes to transition to
    """
    from sage.dialogue.modes import MODE_BEHAVIORS

    behavior = MODE_BEHAVIORS.get(from_mode)
    if not behavior:
        return []
    return behavior.next_modes.copy()


# =============================================================================
# Output Instructions for LLM
# =============================================================================


def get_output_instructions() -> str:
    """Get instructions for the LLM about structured output format.

    This is appended to the prompt to tell the LLM how to structure
    its response.
    """
    return """
## Response Format

You must respond with valid JSON matching this structure:

```json
{
    "message": "Your response to the learner",
    "current_mode": "probing",  // One of: check_in, followup, outcome_discovery, framing, probing, teaching, verification, outcome_check
    "transition_to": null,  // Mode to switch to, or null to stay in current mode
    "transition_reason": null,  // Why transitioning, or null
    "gap_identified": null,  // If in PROBING and found a gap: {"name": "...", "display_name": "...", "description": "...", "blocking_outcome_id": "..."}
    "proof_earned": null,  // If in VERIFICATION and they demonstrated understanding: {"concept_id": "...", "demonstration_type": "...", "evidence": "...", "confidence": 0.0-1.0, "exchange": {...}}
    "connection_discovered": null,  // If you found a connection: {"from_concept_id": "...", "to_concept_id": "...", "relationship": "...", "strength": 0.0-1.0, "used_in_teaching": true/false}
    "application_detected": null,  // If learner mentioned upcoming application: {"context": "...", "concept_ids": [...], "planned_date": "YYYY-MM-DD", "stakes": "high/medium/low"}
    "followup_response": null,  // If in FOLLOWUP and got response: {"event_id": "...", "outcome_result": "...", "what_worked": "...", "what_struggled": "...", "gaps_revealed": [...], "insights": "..."}
    "state_change_detected": null,  // If learner state changed mid-session: {"what_changed": "...", "detected_from": "...", "recommended_adaptation": "..."}
    "context_update": null,  // Updated session context if state changed
    "outcome_achieved": false,  // True if learner can now "do the thing"
    "outcome_reasoning": null,  // Why outcome is/isn't achieved
    "teaching_approach_used": null  // e.g., "example", "analogy", "socratic", "direct explanation"
}
```

Important:
- Only include fields that have values (null fields can be omitted)
- `gap_identified` only in PROBING mode when you find a specific gap
- `proof_earned` only in VERIFICATION mode when they demonstrate understanding
- `transition_to` only when you're ready to move to the next mode
- Watch for state changes (energy drop, confusion, time pressure) and report them
"""
