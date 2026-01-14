"""Verification question generation.

Generates questions to confirm learner understanding, not just recall.
Real understanding means they can explain, apply, and recognize boundaries.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from sage.context.snapshots import ConceptSnapshot, LearnerSnapshot, OutcomeSnapshot
from sage.graph.models import SessionContext


class VerificationStrategy(str, Enum):
    """Strategies for verifying understanding."""

    EXPLAIN_BACK = "explain_back"
    NEW_SCENARIO = "new_scenario"
    TEST_BOUNDARIES = "test_boundaries"
    FIND_CONNECTIONS = "find_connections"


@dataclass
class VerificationQuestion:
    """A question to verify understanding."""

    question: str
    strategy: VerificationStrategy
    concept_id: str
    concept_name: str
    adaptations: list[str]


@dataclass
class VerificationContext:
    """Context for generating verification questions."""

    learner: LearnerSnapshot
    concept: ConceptSnapshot
    outcome: Optional[OutcomeSnapshot] = None
    session_context: Optional[SessionContext] = None
    related_concepts: list[ConceptSnapshot] = field(default_factory=list)


class VerificationQuestionGenerator:
    """Generates questions to verify understanding.

    Adapts verification to:
    - Learner's age group and skill level
    - Current energy/state
    - The specific concept being verified
    - Related concepts they already know
    """

    def generate_verification(
        self, context: VerificationContext
    ) -> VerificationQuestion:
        """Generate a verification question adapted to the learner."""
        strategy = self._select_strategy(context)
        adaptations = []

        generators = {
            VerificationStrategy.EXPLAIN_BACK: self._generate_explain_back,
            VerificationStrategy.NEW_SCENARIO: self._generate_new_scenario,
            VerificationStrategy.TEST_BOUNDARIES: self._generate_boundary_test,
            VerificationStrategy.FIND_CONNECTIONS: self._generate_connection_question,
        }
        question = generators[strategy](context, adaptations)

        return VerificationQuestion(
            question=question,
            strategy=strategy,
            concept_id=context.concept.id,
            concept_name=context.concept.display_name,
            adaptations=adaptations,
        )

    def generate_followup_verification(
        self,
        context: VerificationContext,
        previous_answer: str,
        understanding_level: str,
    ) -> VerificationQuestion:
        """Generate a follow-up verification after partial understanding."""
        name = context.concept.display_name
        adaptations = ["follow-up after partial understanding"]

        if understanding_level == "not_there":
            adaptations.append("simplified for gaps")
            question = f"Let's take a step back. What's the most important thing you took away about {name}?"
            strategy = VerificationStrategy.EXPLAIN_BACK
        else:
            adaptations.append("probing specific gap")
            question = f"You've got part of it. Can you walk me through how you'd apply {name} in a real situation?"
            strategy = VerificationStrategy.NEW_SCENARIO

        return VerificationQuestion(
            question=question,
            strategy=strategy,
            concept_id=context.concept.id,
            concept_name=name,
            adaptations=adaptations,
        )

    def _select_strategy(self, context: VerificationContext) -> VerificationStrategy:
        """Select the best verification strategy for this context."""
        learner = context.learner

        if learner.age_group == "child" or learner.skill_level == "beginner":
            return VerificationStrategy.EXPLAIN_BACK
        if context.related_concepts:
            return VerificationStrategy.FIND_CONNECTIONS
        if learner.skill_level == "advanced":
            return VerificationStrategy.TEST_BOUNDARIES
        return VerificationStrategy.NEW_SCENARIO

    def _generate_explain_back(
        self, context: VerificationContext, adaptations: list[str]
    ) -> str:
        """Generate an 'explain back' question."""
        name = context.concept.display_name
        learner = context.learner

        if learner.age_group == "child":
            adaptations.append("child-friendly language")
            return f"Can you tell me what {name} means in your own words?"
        if learner.skill_level == "beginner":
            adaptations.append("beginner-friendly")
            return f"In your own words, what's the key idea behind {name}?"
        return f"So in your words, what's the main thing about {name}?"

    def _generate_new_scenario(
        self, context: VerificationContext, adaptations: list[str]
    ) -> str:
        """Generate a 'new scenario' question."""
        name = context.concept.display_name

        if context.learner.age_group == "child":
            adaptations.append("simple scenario for child")
            return f"Imagine you had to explain {name} to a friend. What would you say?"
        if context.outcome:
            adaptations.append("tied to outcome")
            return f'Different situation: imagine you\'re actually doing "{context.outcome.stated_goal}". How would {name} help you?'
        return f"Okay, different scenario: how would you apply {name} in practice?"

    def _generate_boundary_test(
        self, context: VerificationContext, adaptations: list[str]
    ) -> str:
        """Generate a 'test boundaries' question."""
        adaptations.append("testing boundaries")
        name = context.concept.display_name
        return f"Here's an edge case: when would {name} NOT apply? What are its limits?"

    def _generate_connection_question(
        self, context: VerificationContext, adaptations: list[str]
    ) -> str:
        """Generate a 'find connections' question."""
        adaptations.append("connecting concepts")
        name = context.concept.display_name

        if context.related_concepts:
            related = context.related_concepts[0]
            return f"You already understand {related.display_name}. How does {name} connect to that?"
        return f"How does {name} connect to what you already know?"


def get_verification_hints_for_prompt(context: VerificationContext) -> str:
    """Generate verification hints for the LLM prompt."""
    lines = [
        "## Verification Guidance",
        f"\n*Verifying understanding of: **{context.concept.display_name}***\n",
    ]

    if context.learner.age_group:
        lines.append(f"- Age group: {context.learner.age_group}")
    if context.learner.skill_level:
        lines.append(f"- Skill level: {context.learner.skill_level}")

    if context.related_concepts:
        lines.append("\n**Connected concepts they know:**")
        lines.extend(f"- {rel.display_name}" for rel in context.related_concepts[:3])

    lines.extend([
        "\n**Remember:**",
        "- Test real understanding, not recall",
        "- Ask them to explain in THEIR words",
        "- Present new scenarios to test transfer",
        "- Don't accept parroting your explanation back",
    ])

    return "\n".join(lines)
