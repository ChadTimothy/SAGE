"""Mid-session state change detection.

This module provides utilities for detecting when a learner's state
changes during a session, and recommending adaptations.

The primary detection happens in the LLM itself (via prompt instructions),
but this module provides:
- Signal patterns for the prompt
- Adaptation recommendations
- State change tracking
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sage.graph.models import EnergyLevel, Message, SessionContext


@dataclass
class StateChangeSignal:
    """A detected signal of state change."""

    signal_type: str  # energy_drop, confusion, time_pressure, etc.
    confidence: float  # 0.0-1.0 how confident we are in this detection
    evidence: str  # What triggered this detection
    detected_at: datetime


@dataclass
class AdaptationRecommendation:
    """Recommendation for how to adapt to a state change."""

    signal_type: str
    recommendations: list[str]
    example_responses: list[str]


# State change patterns and recommendations
STATE_CHANGE_PATTERNS: dict[str, AdaptationRecommendation] = {
    "energy_drop": AdaptationRecommendation(
        signal_type="energy_drop",
        recommendations=[
            "Switch to shorter, more practical content",
            "Offer a break or suggest wrapping up",
            "Focus on quick wins to maintain momentum",
            "Reduce cognitive load - simpler examples",
        ],
        example_responses=[
            "You seem like you might be hitting a wall. Want to wrap up with a quick win?",
            "Let's keep this focused. What's the one thing that would help most right now?",
            "We can pause here and pick up when you're fresher.",
        ],
    ),
    "confusion": AdaptationRecommendation(
        signal_type="confusion",
        recommendations=[
            "Slow down the pace",
            "Try a completely different explanation angle",
            "Use more analogies and concrete examples",
            "Check understanding more frequently",
            "Break into smaller steps",
        ],
        example_responses=[
            "Let me try explaining this a different way.",
            "I can see this isn't landing. Let's back up a step.",
            "Forget what I just said - here's another way to think about this.",
        ],
    ),
    "time_pressure": AdaptationRecommendation(
        signal_type="time_pressure",
        recommendations=[
            "Acknowledge the time constraint",
            "Prioritize ruthlessly - what's most important?",
            "Skip nice-to-haves, focus on essential",
            "End with clear next step for later",
        ],
        example_responses=[
            "Got it, let me give you the one thing that'll help most in the time we have.",
            "Since we're short on time, let's focus on [key point]. We can go deeper next time.",
            "Let's wrap this up with the most practical takeaway.",
        ],
    ),
    "frustration": AdaptationRecommendation(
        signal_type="frustration",
        recommendations=[
            "Acknowledge the frustration without dwelling on it",
            "Switch to smaller, achievable steps",
            "Validate that this is genuinely difficult",
            "Offer a different approach or tangent",
        ],
        example_responses=[
            "This is legitimately tricky - you're not missing something obvious.",
            "Let's try a different angle on this.",
            "Want to step back and approach this from a different direction?",
        ],
    ),
    "disengagement": AdaptationRecommendation(
        signal_type="disengagement",
        recommendations=[
            "Check if the topic is still relevant",
            "Ask directly about interest/motivation",
            "Offer to switch topics or take a break",
            "Connect back to their stated outcome",
        ],
        example_responses=[
            "Is this still what you want to focus on?",
            "Are we going in the right direction here?",
            "Let's check in - is this helping with what you actually need?",
        ],
    ),
    "overwhelm": AdaptationRecommendation(
        signal_type="overwhelm",
        recommendations=[
            "Simplify immediately",
            "Focus on just one concept",
            "Provide explicit structure and steps",
            "Offer reassurance about complexity",
        ],
        example_responses=[
            "Let's simplify. Just focus on this one thing for now.",
            "There's a lot here - let me break it down into smaller pieces.",
            "Let's take this one step at a time. First: [step].",
        ],
    ),
}


# Explicit signals that map to state changes
EXPLICIT_SIGNAL_PATTERNS: dict[str, list[str]] = {
    "energy_drop": [
        r"\bI'm (getting )?(tired|exhausted|worn out|sleepy)\b",
        r"\b(fading|flagging|losing steam)\b",
        r"\bmy (brain|head) (hurts|is fried)\b",
        r"\bcan't (think straight|focus)\b",
    ],
    "time_pressure": [
        r"\bI (have to|need to|gotta) (go|leave|run)\b",
        r"\bonly have (\d+) minutes?\b",
        r"\bI'm (almost )?out of time\b",
        r"\bmeeting in (\d+) minutes?\b",
        r"\bquick (question|thing)\b",
    ],
    "confusion": [
        r"\bI('m| am) (lost|confused)\b",
        r"\bI don't (understand|get it|follow)\b",
        r"\bwhat do you mean\b",
        r"\bcan you (explain|clarify)\b",
        r"\bhuh\?",
    ],
    "frustration": [
        r"\b(ugh|argh|damn|frustrated)\b",
        r"\bthis (is|makes) (no sense|ridiculous)\b",
        r"\bI('ve| have) been (trying|at this)\b",
        r"\bwhy (is|isn't) this (working|making sense)\b",
    ],
}


def detect_explicit_signals(message: str) -> list[StateChangeSignal]:
    """Detect explicit state change signals in a message.

    This is a simple pattern-based detection for obvious signals.
    The LLM does more nuanced detection.

    Args:
        message: The user's message

    Returns:
        List of detected signals
    """
    signals = []
    message_lower = message.lower()

    for signal_type, patterns in EXPLICIT_SIGNAL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                signals.append(
                    StateChangeSignal(
                        signal_type=signal_type,
                        confidence=0.8,  # High confidence for explicit signals
                        evidence=f"Pattern match: {pattern}",
                        detected_at=datetime.utcnow(),
                    )
                )
                break  # Only one signal per type

    return signals


def get_adaptation_for_signal(signal_type: str) -> Optional[AdaptationRecommendation]:
    """Get adaptation recommendation for a signal type.

    Args:
        signal_type: The type of state change signal

    Returns:
        Adaptation recommendation, or None if unknown signal
    """
    return STATE_CHANGE_PATTERNS.get(signal_type)


def detect_implicit_signals(
    recent_messages: list[Message],
    baseline_response_length: Optional[int] = None,
) -> list[StateChangeSignal]:
    """Detect implicit state change signals from message patterns.

    Looks at patterns like:
    - Response length decreasing (fatigue)
    - More questions than usual (confusion)
    - Short, minimal responses (disengagement)

    Args:
        recent_messages: Recent messages to analyze
        baseline_response_length: Typical response length for comparison

    Returns:
        List of detected signals
    """
    if not recent_messages:
        return []

    signals = []

    # Get user messages only
    user_messages = [m for m in recent_messages if m.role == "user"]
    if len(user_messages) < 3:
        return []  # Need at least 3 messages to detect patterns

    # Analyze response length trend
    recent_lengths = [len(m.content) for m in user_messages[-5:]]
    if len(recent_lengths) >= 3:
        # Check for decreasing length trend
        if all(
            recent_lengths[i] > recent_lengths[i + 1]
            for i in range(len(recent_lengths) - 1)
        ):
            signals.append(
                StateChangeSignal(
                    signal_type="energy_drop",
                    confidence=0.5,  # Lower confidence for implicit signals
                    evidence="Response length decreasing",
                    detected_at=datetime.utcnow(),
                )
            )

        # Check for very short responses
        avg_length = sum(recent_lengths) / len(recent_lengths)
        if avg_length < 20:  # Very short average
            signals.append(
                StateChangeSignal(
                    signal_type="disengagement",
                    confidence=0.4,
                    evidence="Consistently short responses",
                    detected_at=datetime.utcnow(),
                )
            )

    return signals


def get_prompt_instructions_for_detection() -> str:
    """Get prompt instructions for the LLM to detect state changes.

    Returns:
        Markdown instructions to include in the prompt
    """
    return """
## Monitor for State Changes

Watch for signs the learner's state has shifted during this session:

### Explicit Signals (direct statements)
- Fatigue: "I'm tired", "brain is fried", "can't think straight"
- Time pressure: "I have to go soon", "only have 10 minutes", "quick question"
- Confusion: "I'm lost", "don't understand", "what do you mean"
- Frustration: "ugh", "this makes no sense", "why isn't this working"

### Implicit Signals (patterns to notice)
- Fatigue: shorter responses, less engagement, asking to repeat things
- Confusion: hesitation, contradictions, "I think..." hedging, multiple wrong attempts
- Stress: rushed responses, frustration signals, asking to skip ahead
- Disengagement: minimal responses ("ok", "sure"), topic changes, flat affect

### When You Detect a Change

1. Acknowledge it naturally (don't make it weird)
2. Adapt your approach:
   - Energy drop → shorter content, quick wins, offer break
   - Confusion → different explanation, smaller steps, more analogies
   - Time pressure → prioritize ruthlessly, focus on most useful thing
   - Frustration → validate, try different angle, smaller steps

3. Report it in your response:
```json
{
    "state_change_detected": {
        "what_changed": "energy_drop",
        "detected_from": "shorter responses, asked to repeat",
        "recommended_adaptation": "switch to quick wins, offer to wrap up"
    }
}
```
"""


def update_context_for_state_change(
    current_context: SessionContext,
    state_change: str,
) -> SessionContext:
    """Update session context based on detected state change.

    Args:
        current_context: The current session context
        state_change: The type of state change detected

    Returns:
        Updated session context
    """
    # Use Pydantic's model_copy for clean copying
    updated = current_context.model_copy()

    # Define state change effects
    state_effects = {
        "energy_drop": {"energy": EnergyLevel.LOW},
        "time_pressure": {"time_available": "short", "mindset_tag": "time pressured"},
        "confusion": {"mindset_tag": "needs clarification"},
        "frustration": {"mindset_tag": "frustrated"},
        "disengagement": {"energy": EnergyLevel.LOW, "mindset_tag": "disengaged"},
        "overwhelm": {"mindset_tag": "overwhelmed"},
    }

    effects = state_effects.get(state_change, {})

    if "energy" in effects:
        updated.energy = effects["energy"]

    if "time_available" in effects:
        updated.time_available = effects["time_available"]

    if "mindset_tag" in effects:
        tag = effects["mindset_tag"]
        updated.mindset = f"{current_context.mindset or ''} [{tag}]".strip()

    return updated
