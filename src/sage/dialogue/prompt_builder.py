"""Prompt assembly from templates.

This module loads mode-specific prompt templates and assembles
them into full prompts for the LLM, injecting context data.
"""

from pathlib import Path
from typing import Optional

from sage.context.turn_context import TurnContext
from sage.graph.models import DialogueMode, Message


# Default prompt templates directory
DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "prompts"


class PromptTemplates:
    """Loads and caches prompt templates."""

    def __init__(self, prompts_dir: Optional[Path] = None):
        """Initialize with optional custom prompts directory."""
        self.prompts_dir = prompts_dir or DEFAULT_PROMPTS_DIR
        self._cache: dict[str, str] = {}

    def _load(self, name: str) -> str:
        """Load a template file, caching the result.

        Args:
            name: Template name (without .md extension)

        Returns:
            Template content
        """
        if name not in self._cache:
            path = self.prompts_dir / f"{name}.md"
            if not path.exists():
                raise FileNotFoundError(f"Prompt template not found: {path}")
            self._cache[name] = path.read_text()
        return self._cache[name]

    @property
    def system(self) -> str:
        """Load system prompt."""
        return self._load("system")

    def get_mode_prompt(self, mode: DialogueMode) -> str:
        """Get the prompt template for a specific mode."""
        return self._load(mode.value)


class PromptBuilder:
    """Assembles prompts from templates and context."""

    def __init__(self, templates: Optional[PromptTemplates] = None):
        """Initialize with optional custom templates."""
        self.templates = templates or PromptTemplates()

    def build_system_prompt(self, context: TurnContext) -> str:
        """Build the system prompt with learner context."""
        base_prompt = self.templates.system

        # Add adaptation section based on context
        adaptation = self._build_adaptation_section(context)

        return f"{base_prompt}\n\n{adaptation}"

    def build_turn_prompt(self, context: TurnContext) -> str:
        """Build the complete prompt for this turn.

        Includes:
        - Mode-specific instructions
        - Current context (learner, outcome, etc.)
        - Proven knowledge
        - Relevant applications
        - Adaptation hints
        """
        parts = []

        # Mode-specific prompt
        mode_prompt = self.templates.get_mode_prompt(context.mode)
        parts.append(mode_prompt)

        # Current context section
        parts.append(self._build_context_section(context))

        # Knowledge section
        if context.proven_concepts or context.related_concepts:
            parts.append(self._build_knowledge_section(context))

        # Application history section
        if context.relevant_applications or context.pending_followup:
            parts.append(self._build_applications_section(context))

        # Adaptation hints
        if context.adaptation_hints:
            parts.append(self._build_hints_section(context.adaptation_hints))

        # Recent conversation for continuity
        if context.recent_messages:
            parts.append(self._build_conversation_section(context.recent_messages))

        return "\n\n---\n\n".join(parts)

    def _build_adaptation_section(self, context: TurnContext) -> str:
        """Build learner-specific adaptation instructions."""
        lines = ["## Learner Adaptation"]

        learner = context.learner
        if learner.age_group:
            lines.append(f"\n**Age Group:** {learner.age_group}")
            lines.append(_age_group_guidance(learner.age_group))

        if learner.skill_level:
            lines.append(f"\n**Skill Level:** {learner.skill_level}")
            lines.append(_skill_level_guidance(learner.skill_level))

        # Learning preferences
        insights = context.insights
        if insights:
            prefs = []
            if insights.prefers_examples:
                prefs.append("Prefers concrete examples over abstractions")
            if insights.prefers_theory_first:
                prefs.append("Wants to understand 'why' before 'how'")
            if insights.needs_frequent_checks:
                prefs.append("Benefits from frequent understanding checks")
            if insights.responds_to_challenge:
                prefs.append("Responds well to challenging questions")

            if prefs:
                lines.append("\n**Learning Preferences:**")
                for p in prefs:
                    lines.append(f"- {p}")

            # Effective approaches
            if insights.effective_approaches:
                lines.append("\n**What's worked for this learner:**")
                for approach in insights.effective_approaches[:5]:
                    lines.append(f"- {approach}")

            # Known patterns
            if insights.patterns:
                lines.append("\n**Patterns noticed:**")
                for pattern in insights.patterns[:3]:
                    lines.append(f"- {pattern}")

        return "\n".join(lines)

    def _build_context_section(self, context: TurnContext) -> str:
        """Build the current context section."""
        lines = ["## Current Context"]

        # Session context (Set/Setting/Intention)
        if context.session_context:
            sc = context.session_context
            lines.append("\n### Session State")
            if sc.energy:
                lines.append(f"- **Energy:** {sc.energy}")
            if sc.time_available:
                lines.append(f"- **Time:** {sc.time_available}")
            if sc.mindset:
                lines.append(f"- **Mindset:** {sc.mindset}")
            if sc.intention_strength:
                lines.append(f"- **Intention:** {sc.intention_strength}")
            if sc.device:
                lines.append(f"- **Device:** {sc.device}")
            if sc.can_speak is not None:
                can_speak = "yes" if sc.can_speak else "no"
                lines.append(f"- **Can speak aloud:** {can_speak}")

        # Current outcome
        if context.outcome:
            lines.append("\n### Current Goal")
            lines.append(f"**Stated:** {context.outcome.stated_goal}")
            if context.outcome.clarified_goal:
                lines.append(f"**Clarified:** {context.outcome.clarified_goal}")
            if context.outcome.success_criteria:
                lines.append(f"**Success criteria:** {context.outcome.success_criteria}")

            # Progress
            if context.outcome_progress:
                prog = context.outcome_progress
                lines.append(
                    f"\n**Progress:** {prog.concepts_proven}/{prog.concepts_identified} "
                    f"concepts proven"
                )
                if prog.current_concept:
                    lines.append(f"**Working on:** {prog.current_concept}")

        # Current concept being taught
        if context.current_concept:
            lines.append("\n### Current Focus")
            lines.append(f"**Concept:** {context.current_concept.display_name}")
            if context.current_concept.summary:
                lines.append(f"**Summary:** {context.current_concept.summary}")

        return "\n".join(lines)

    def _build_knowledge_section(self, context: TurnContext) -> str:
        """Build the proven knowledge section."""
        lines = ["## What This Learner Already Knows"]

        if context.proven_concepts:
            lines.append("\n### Proven Concepts")
            for concept in context.proven_concepts[:10]:  # Limit for token efficiency
                confidence = ""
                if concept.proof_confidence:
                    confidence = f" ({concept.proof_confidence:.0%} confident)"
                lines.append(
                    f"- **{concept.display_name}**{confidence}: "
                    f"{concept.summary or 'No summary'}"
                )

        if context.related_concepts:
            lines.append("\n### Related to Current Topic")
            for related in context.related_concepts[:5]:
                lines.append(
                    f"- **{related.display_name}** ({related.relationship}): "
                    f"{related.summary or 'No summary'}"
                )

        return "\n".join(lines)

    def _build_applications_section(self, context: TurnContext) -> str:
        """Build the applications history section."""
        lines = ["## Real-World Applications"]

        if context.pending_followup:
            app = context.pending_followup
            lines.append("\n### NEEDS FOLLOW-UP")
            lines.append(f"**Context:** {app.context}")
            if app.planned_date:
                lines.append(f"**Planned for:** {app.planned_date}")
            lines.append(
                "Ask about this application before continuing with regular session."
            )

        if context.relevant_applications:
            lines.append("\n### Past Applications of Related Concepts")
            for app in context.relevant_applications[:3]:
                lines.append(f"\n**{app.context}**")
                if app.outcome_result:
                    lines.append(f"- Result: {app.outcome_result}")
                if app.what_worked:
                    lines.append(f"- What worked: {app.what_worked}")
                if app.what_struggled:
                    lines.append(f"- Struggled with: {app.what_struggled}")

            lines.append(
                "\n*Reference past experiences when teaching. "
                "Build on successes, address struggles.*"
            )

        return "\n".join(lines)

    def _build_hints_section(self, hints: list[str]) -> str:
        """Build adaptation hints section."""
        lines = ["## Adaptation Hints for This Turn"]
        for hint in hints:
            lines.append(f"- {hint}")
        return "\n".join(lines)

    def _build_conversation_section(self, messages: list[Message]) -> str:
        """Build recent conversation for continuity."""
        lines = ["## Recent Conversation"]
        lines.append(
            "\n*Continue naturally from this conversation. "
            "Don't repeat what's been said.*"
        )

        for msg in messages[-10:]:  # Last 10 messages for context
            role = "User" if msg.role == "user" else "SAGE"
            # Truncate long messages
            content = msg.content
            if len(content) > 500:
                content = content[:500] + "..."
            lines.append(f"\n**{role}:** {content}")

        return "\n".join(lines)


def _age_group_guidance(age_group: str) -> str:
    """Get teaching guidance for age group."""
    guidance = {
        "child": (
            "Use simple vocabulary and everyday examples (school, games, family). "
            "Be encouraging and patient. Celebrate small wins."
        ),
        "teen": (
            "Use accessible language without being childish. "
            "Examples from their world (social, school, early work). "
            "Respectful tone—they're not kids but not adults either."
        ),
        "adult": (
            "Professional vocabulary appropriate to their domain. "
            "Real-world examples (work, business, life). "
            "Direct, peer-like tone."
        ),
    }
    return guidance.get(age_group, "")


def _skill_level_guidance(skill_level: str) -> str:
    """Get teaching guidance for skill level."""
    guidance = {
        "beginner": (
            "Start from fundamentals. More scaffolding, smaller steps. "
            "Simpler verification questions."
        ),
        "intermediate": (
            "Assume basics are understood. Build on existing knowledge. "
            "Standard complexity in examples."
        ),
        "advanced": (
            "Focus on nuance and edge cases. Efficient explanations. "
            "Challenging application scenarios."
        ),
    }
    return guidance.get(skill_level, "")


def build_messages_for_llm(
    system_prompt: str,
    turn_prompt: str,
    user_message: str,
) -> list[dict[str, str]]:
    """Build the messages list for the LLM API call.

    Args:
        system_prompt: The system prompt with SAGE personality
        turn_prompt: The assembled turn context
        user_message: The user's message

    Returns:
        List of message dicts for the API
    """
    return [
        {"role": "system", "content": f"{system_prompt}\n\n---\n\n{turn_prompt}"},
        {"role": "user", "content": user_message},
    ]
