"""Probing question generation for gap discovery.

This module generates probing questions to discover gaps in learner
understanding. Questions are adapted to learner context and outcome.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from sage.context.snapshots import ConceptSnapshot, LearnerSnapshot, OutcomeSnapshot
from sage.graph.models import EnergyLevel, SessionContext


class ProbingStrategy(str, Enum):
    """Types of probing strategies."""

    DIRECT = "direct"  # Ask directly about blocks
    INDIRECT = "indirect"  # Have them try something
    SCENARIO = "scenario"  # Walk through a scenario
    MISCONCEPTION = "misconception"  # Test common misconceptions


@dataclass
class ProbingQuestion:
    """A generated probing question."""

    question: str
    strategy: ProbingStrategy
    target_gap: Optional[str] = None  # What we're trying to find
    follow_up_if_struggle: Optional[str] = None
    adaptation_notes: Optional[str] = None


@dataclass
class ProbingContext:
    """Context for generating probing questions."""

    learner: LearnerSnapshot
    outcome: Optional[OutcomeSnapshot]
    session_context: Optional[SessionContext]
    proven_concepts: list[ConceptSnapshot]
    concepts_explored: list[str]  # Already probed


class ProbingQuestionGenerator:
    """Generates probing questions adapted to learner context.

    Uses outcome, learner profile, and session state to generate
    questions that reveal understanding gaps.
    """

    # Question templates by strategy
    DIRECT_TEMPLATES = [
        "What's blocking you from {outcome}?",
        "When you think about {outcome}, what feels hardest?",
        "What would need to be true for you to feel confident doing this?",
        "If you had to do this tomorrow, what would worry you?",
    ]

    INDIRECT_TEMPLATES = [
        "Walk me through how you'd approach this.",
        "Let's try it - start explaining {topic} as if I knew nothing.",
        "Show me your process for thinking through this.",
        "If a friend asked you about this, what would you tell them?",
    ]

    SCENARIO_TEMPLATES = [
        "Imagine you're in a {scenario}. What do you do?",
        "Someone asks you {question}. How do you respond?",
        "Walk me through {scenario} step by step.",
        "If {situation} happened, what would be your first move?",
    ]

    # Language simplifications for children
    CHILD_LANGUAGE_MAP = {
        "obstacle": "hard part",
        "approach": "do",
    }

    def __init__(self):
        """Initialize the question generator."""

    def generate_initial_probe(self, context: ProbingContext) -> ProbingQuestion:
        """Generate the first probing question for an outcome.

        Starts with broad probing to find the most likely gap.

        Args:
            context: The probing context

        Returns:
            A probing question to start with
        """
        if not context.outcome:
            return ProbingQuestion(
                question="What's blocking you from doing this right now?",
                strategy=ProbingStrategy.DIRECT,
                target_gap="unknown",
                adaptation_notes="No specific outcome - broad probing",
            )

        # Adapt based on energy level
        if context.session_context and context.session_context.energy == EnergyLevel.LOW:
            return self._generate_low_energy_probe(context)

        # Default to scenario-based for adults with outcomes
        if context.learner.age_group == "adult":
            return self._generate_scenario_probe(context)

        # Simpler direct probing for younger learners
        return self._generate_direct_probe(context)

    def generate_followup_probe(
        self,
        context: ProbingContext,
        previous_response: str,
        gap_hint: Optional[str] = None,
    ) -> ProbingQuestion:
        """Generate a follow-up probing question.

        Uses the previous response to dig deeper or probe adjacent areas.

        Args:
            context: The probing context
            previous_response: What the learner just said
            gap_hint: Optional hint about where the gap might be

        Returns:
            A follow-up probing question
        """
        # If we have a hint, target it specifically
        if gap_hint:
            return self._generate_targeted_probe(context, gap_hint)

        # Otherwise, use indirect probing to find deeper gaps
        return self._generate_indirect_probe(context, previous_response)

    def generate_misconception_check(
        self,
        context: ProbingContext,
        topic: str,
    ) -> ProbingQuestion:
        """Generate a question to check for common misconceptions.

        Args:
            context: The probing context
            topic: The topic to check misconceptions for

        Returns:
            A question targeting common misconceptions
        """
        return ProbingQuestion(
            question=f"When it comes to {topic}, what do most people get wrong?",
            strategy=ProbingStrategy.MISCONCEPTION,
            target_gap="misconception",
            follow_up_if_struggle="What's your understanding of how it actually works?",
            adaptation_notes="Testing for misconceptions",
        )

    def _generate_direct_probe(self, context: ProbingContext) -> ProbingQuestion:
        """Generate a direct probing question."""
        outcome_text = context.outcome.stated_goal if context.outcome else "this"

        question = self._adapt_for_learner(
            base_question=f"When you think about {outcome_text}, what feels like the biggest obstacle?",
            context=context,
        )

        return ProbingQuestion(
            question=question,
            strategy=ProbingStrategy.DIRECT,
            target_gap="primary_obstacle",
            follow_up_if_struggle="Is it more about knowing what to do, or being able to do it?",
        )

    def _generate_indirect_probe(
        self, context: ProbingContext, previous_response: str
    ) -> ProbingQuestion:
        """Generate an indirect probing question."""
        return ProbingQuestion(
            question="Let's try something. Walk me through how you'd approach this right now.",
            strategy=ProbingStrategy.INDIRECT,
            target_gap="execution_gap",
            follow_up_if_struggle="Where does it start to feel uncertain?",
        )

    def _generate_scenario_probe(self, context: ProbingContext) -> ProbingQuestion:
        """Generate a scenario-based probing question."""
        outcome_text = context.outcome.stated_goal if context.outcome else "this"

        question = (
            f"Imagine you're about to {outcome_text}. "
            "Walk me through what you'd do, step by step."
        )

        return ProbingQuestion(
            question=question,
            strategy=ProbingStrategy.SCENARIO,
            target_gap="process_gap",
            follow_up_if_struggle="What would make you hesitate at that point?",
        )

    def _generate_targeted_probe(
        self, context: ProbingContext, target: str
    ) -> ProbingQuestion:
        """Generate a question targeting a specific potential gap."""
        return ProbingQuestion(
            question=f"Tell me about your understanding of {target}.",
            strategy=ProbingStrategy.DIRECT,
            target_gap=target,
            follow_up_if_struggle=f"When you encounter {target} in practice, what typically happens?",
        )

    def _generate_low_energy_probe(self, context: ProbingContext) -> ProbingQuestion:
        """Generate a simpler probe for low energy state."""
        return ProbingQuestion(
            question="Quick check - what's the one thing that would help most right now?",
            strategy=ProbingStrategy.DIRECT,
            target_gap="immediate_need",
            adaptation_notes="Low energy - focused, minimal probe",
        )

    def _adapt_for_learner(self, base_question: str, context: ProbingContext) -> str:
        """Adapt a question for the learner's profile."""
        if context.learner.age_group != "child":
            return base_question

        # Simplify language for children
        result = base_question
        for original, simple in self.CHILD_LANGUAGE_MAP.items():
            result = result.replace(original, simple)
        return result


def get_probing_hints_for_prompt(context: ProbingContext) -> str:
    """Generate probing hints to include in the LLM prompt.

    This provides context-specific guidance for the LLM to generate
    better probing questions during the conversation.

    Args:
        context: The probing context

    Returns:
        Markdown hints for the prompt
    """
    lines = ["## Probing Guidance for This Learner"]

    # Age-appropriate probing
    if context.learner.age_group == "child":
        lines.append("\n**Age adaptation:** Use simple language and relatable examples.")
        lines.append("Keep questions short and concrete.")
    elif context.learner.age_group == "teen":
        lines.append("\n**Age adaptation:** Be direct but not condescending.")
        lines.append("Use examples from school, social situations, early work.")
    else:
        lines.append("\n**Age adaptation:** Professional tone, real-world scenarios.")
        lines.append("Respect their time and intelligence.")

    # Skill level
    if context.learner.skill_level == "beginner":
        lines.append("\n**Skill level:** Probe fundamentals first. Likely gaps in basics.")
    elif context.learner.skill_level == "advanced":
        lines.append("\n**Skill level:** Probe nuance and edge cases. Basics likely solid.")

    # Proven concepts - what they already know
    if context.proven_concepts:
        lines.append("\n**What they've proven:**")
        for concept in context.proven_concepts[:5]:
            lines.append(f"- {concept.display_name}")
        lines.append("\n*Build on these. Don't reprobe what they know.*")

    # Energy state
    if context.session_context:
        if context.session_context.energy == EnergyLevel.LOW:
            lines.append("\n**Current state:** Low energy. Keep probes short and focused.")
        elif context.session_context.time_available:
            lines.append(f"\n**Time available:** {context.session_context.time_available}")
            lines.append("Prioritize probing the most critical gaps.")

    # Outcome focus
    if context.outcome:
        lines.append(f"\n**Their goal:** {context.outcome.stated_goal}")
        if context.outcome.success_criteria:
            lines.append(f"**Success looks like:** {context.outcome.success_criteria}")
        lines.append("\n*Probe for gaps that block THIS specific goal.*")

    return "\n".join(lines)
