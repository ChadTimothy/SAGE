"""Dialogue mode management and transitions.

This module handles the SAGE dialogue state machine, including:
- Mode behaviors and goals
- Valid transitions between modes
- Determining initial mode for a session
"""

from dataclasses import dataclass
from typing import Optional

from sage.context.full_context import FullContext
from sage.graph.models import DialogueMode, Outcome, Session


@dataclass
class ModeBehavior:
    """Defines behavior for a dialogue mode."""

    goal: str
    tone: str
    expected_output: str
    next_modes: list[DialogueMode]


# Mode behaviors - what each mode does
MODE_BEHAVIORS: dict[DialogueMode, ModeBehavior] = {
    DialogueMode.CHECK_IN: ModeBehavior(
        goal="Gather Set/Setting/Intention for this session",
        tone="Warm, quick, not intrusive",
        expected_output="SessionContext populated with energy, time, mindset",
        next_modes=[
            DialogueMode.FOLLOWUP,
            DialogueMode.OUTCOME_DISCOVERY,
            DialogueMode.PROBING,
            DialogueMode.FRAMING,
        ],
    ),
    DialogueMode.FOLLOWUP: ModeBehavior(
        goal="Learn how a past application went",
        tone="Curious, non-judgmental",
        expected_output="FollowupResponse with outcome and gaps revealed",
        next_modes=[
            DialogueMode.PROBING,
            DialogueMode.TEACHING,
            DialogueMode.OUTCOME_DISCOVERY,
        ],
    ),
    DialogueMode.OUTCOME_DISCOVERY: ModeBehavior(
        goal="Clarify what they want to be able to DO",
        tone="Curious, clarifying",
        expected_output="Outcome with stated and clarified goal",
        next_modes=[
            DialogueMode.FRAMING,
            DialogueMode.PROBING,
        ],
    ),
    DialogueMode.FRAMING: ModeBehavior(
        goal="Light sketch of territory - what's typically involved",
        tone="Informative but brief",
        expected_output="Territory list, expectations set",
        next_modes=[
            DialogueMode.PROBING,
        ],
    ),
    DialogueMode.PROBING: ModeBehavior(
        goal="Find what's blocking them from the outcome",
        tone="Exploratory, Socratic",
        expected_output="GapIdentified or determination that no gaps remain",
        next_modes=[
            DialogueMode.TEACHING,
            DialogueMode.VERIFICATION,
            DialogueMode.OUTCOME_CHECK,
        ],
    ),
    DialogueMode.TEACHING: ModeBehavior(
        goal="Fill the specific gap that was identified",
        tone="Clear, adapted to learner state",
        expected_output="Concept taught, ready for verification",
        next_modes=[
            DialogueMode.VERIFICATION,
            DialogueMode.TEACHING,  # Retry with different approach
        ],
    ),
    DialogueMode.VERIFICATION: ModeBehavior(
        goal="Confirm real understanding, not just recall",
        tone="Testing but supportive",
        expected_output="ProofEarned or back to teaching",
        next_modes=[
            DialogueMode.OUTCOME_CHECK,
            DialogueMode.TEACHING,
            DialogueMode.PROBING,
        ],
    ),
    DialogueMode.OUTCOME_CHECK: ModeBehavior(
        goal="Can they do the thing yet?",
        tone="Direct, honest",
        expected_output="outcome_achieved or more probing needed",
        next_modes=[
            DialogueMode.PROBING,
            DialogueMode.OUTCOME_DISCOVERY,
        ],
    ),
}


class ModeManager:
    """Manages dialogue mode state and transitions."""

    def __init__(self):
        """Initialize the mode manager."""
        self.behaviors = MODE_BEHAVIORS

    def get_behavior(self, mode: DialogueMode) -> ModeBehavior:
        """Get the behavior definition for a mode."""
        return self.behaviors[mode]

    def is_valid_transition(
        self,
        from_mode: DialogueMode,
        to_mode: DialogueMode,
    ) -> bool:
        """Check if a mode transition is valid.

        Args:
            from_mode: Current mode
            to_mode: Proposed next mode

        Returns:
            True if transition is valid
        """
        behavior = self.behaviors.get(from_mode)
        if not behavior:
            return False
        return to_mode in behavior.next_modes

    def get_valid_transitions(self, mode: DialogueMode) -> list[DialogueMode]:
        """Get all valid transitions from a mode.

        Args:
            mode: The current mode

        Returns:
            List of valid next modes
        """
        behavior = self.behaviors.get(mode)
        if not behavior:
            return []
        return behavior.next_modes.copy()

    def determine_initial_mode(self, context: FullContext) -> DialogueMode:
        """Determine the initial mode for a session.

        Logic:
        1. If there are pending follow-ups, start with CHECK_IN then FOLLOWUP
        2. If no active outcome, start with CHECK_IN then OUTCOME_DISCOVERY
        3. If resuming an outcome, start with CHECK_IN then PROBING

        We always start with CHECK_IN to gather Set/Setting/Intention.

        Args:
            context: The full context loaded at session start

        Returns:
            The initial dialogue mode (always CHECK_IN)
        """
        # Always start with CHECK_IN to gather context
        return DialogueMode.CHECK_IN

    def determine_post_checkin_mode(self, context: FullContext) -> DialogueMode:
        """Determine which mode to transition to after CHECK_IN.

        Args:
            context: The full context

        Returns:
            The next mode after CHECK_IN completes
        """
        # If there are pending follow-ups, ask about them first
        if context.pending_followups:
            return DialogueMode.FOLLOWUP

        # If no active outcome, help them define one
        if not context.active_outcome:
            return DialogueMode.OUTCOME_DISCOVERY

        # If continuing an outcome, probe for the next gap
        return DialogueMode.PROBING

    def determine_post_followup_mode(
        self,
        context: FullContext,
        gaps_revealed: bool,
    ) -> DialogueMode:
        """Determine which mode to transition to after FOLLOWUP.

        Args:
            context: The full context
            gaps_revealed: Whether the follow-up revealed new gaps

        Returns:
            The next mode
        """
        # If new gaps were revealed, teach them
        if gaps_revealed:
            return DialogueMode.TEACHING

        # Otherwise continue with normal flow
        if not context.active_outcome:
            return DialogueMode.OUTCOME_DISCOVERY
        return DialogueMode.PROBING


def get_mode_prompt_name(mode: DialogueMode) -> str:
    """Get the prompt template name for a mode.

    Args:
        mode: The dialogue mode

    Returns:
        Name of the prompt template file (without extension)
    """
    return mode.value


def should_verify_before_building(
    session: Session,
    days_since_proof: int,
    concept_is_foundational: bool,
) -> bool:
    """Check if we should re-verify understanding before building on it.

    After a long break, foundational concepts may have decayed.

    Args:
        session: The current session
        days_since_proof: Days since the concept was proven
        concept_is_foundational: Whether this concept is foundational

    Returns:
        True if we should verify before building on this concept
    """
    # If it's been more than 60 days and the concept is foundational,
    # re-verify before building on it
    if days_since_proof > 60 and concept_is_foundational:
        return True

    # If it's been more than 90 days for any concept
    if days_since_proof > 90:
        return True

    return False


def get_transition_signals() -> dict[DialogueMode, dict[str, DialogueMode]]:
    """Get the transition signals for each mode.

    Returns a dict mapping mode -> {signal -> target_mode}.
    These are the conversation signals that trigger transitions.
    """
    return {
        DialogueMode.CHECK_IN: {
            "pending_followups_exist": DialogueMode.FOLLOWUP,
            "no_active_outcome": DialogueMode.OUTCOME_DISCOVERY,
            "has_active_outcome": DialogueMode.PROBING,
        },
        DialogueMode.FOLLOWUP: {
            "followup_complete": DialogueMode.PROBING,
            "new_gap_revealed": DialogueMode.TEACHING,
        },
        DialogueMode.OUTCOME_DISCOVERY: {
            "outcome_clarified": DialogueMode.FRAMING,
        },
        DialogueMode.FRAMING: {
            "territory_sketched": DialogueMode.PROBING,
        },
        DialogueMode.PROBING: {
            "gap_identified": DialogueMode.TEACHING,
            "user_claims_knowledge": DialogueMode.VERIFICATION,
            "no_gaps_found": DialogueMode.OUTCOME_CHECK,
        },
        DialogueMode.TEACHING: {
            "teaching_complete": DialogueMode.VERIFICATION,
            "user_confused": DialogueMode.TEACHING,
        },
        DialogueMode.VERIFICATION: {
            "proof_earned": DialogueMode.OUTCOME_CHECK,
            "not_yet_understood": DialogueMode.TEACHING,
            "partial_understanding": DialogueMode.PROBING,
        },
        DialogueMode.OUTCOME_CHECK: {
            "outcome_achieved": None,  # Session can end or new outcome
            "more_gaps_exist": DialogueMode.PROBING,
        },
    }
