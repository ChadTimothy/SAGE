"""TurnContext builder - assembles context for each LLM call.

This module builds the specific context needed for each turn,
using snapshots for token efficiency.
"""

from dataclasses import dataclass, field
from typing import Optional

from sage.graph.models import (
    ApplicationEvent,
    Concept,
    DialogueMode,
    EnergyLevel,
    IntentionStrength,
    LearnerInsights,
    Message,
    Session,
    SessionContext,
)

from .full_context import FullContext
from .snapshots import (
    ApplicationSnapshot,
    ConceptSnapshot,
    LearnerSnapshot,
    OutcomeProgress,
    OutcomeSnapshot,
    RelatedConcept,
)


@dataclass
class TurnContext:
    """Context assembled for this turn's LLM call.

    Uses snapshots for token efficiency while providing
    all information needed for the LLM to make good decisions.
    """

    # WHO
    learner: LearnerSnapshot
    insights: LearnerInsights

    # CURRENT STATE
    mode: DialogueMode
    session_context: Optional[SessionContext]
    current_concept: Optional[ConceptSnapshot]

    # GOAL
    outcome: Optional[OutcomeSnapshot]
    outcome_progress: Optional[OutcomeProgress]

    # CONVERSATION
    recent_messages: list[Message]
    session_summary: Optional[str]

    # KNOWLEDGE
    proven_concepts: list[ConceptSnapshot]
    related_concepts: list[RelatedConcept]

    # APPLICATIONS
    pending_followup: Optional[ApplicationSnapshot]
    relevant_applications: list[ApplicationSnapshot]

    # ADAPTATION
    adaptation_hints: list[str] = field(default_factory=list)


class TurnContextBuilder:
    """Builds TurnContext from FullContext for each turn."""

    # How many recent messages to include
    DEFAULT_MESSAGE_LIMIT = 20

    def __init__(self, full_context: FullContext, session: Session):
        """Initialize with loaded context and current session.

        Args:
            full_context: The eagerly loaded session context
            session: The current session being worked on
        """
        self.full = full_context
        self.session = session
        self._concept_name_map = self._build_concept_name_map()

    def _build_concept_name_map(self) -> dict[str, str]:
        """Build map of concept_id -> display_name."""
        return {c.id: c.display_name for c in self.full.all_concepts}

    def build(
        self,
        mode: DialogueMode,
        current_concept: Optional[Concept] = None,
        message_limit: int = DEFAULT_MESSAGE_LIMIT,
    ) -> TurnContext:
        """Build context for this turn.

        Args:
            mode: The current dialogue mode
            current_concept: The concept being worked on (if any)
            message_limit: Max recent messages to include

        Returns:
            TurnContext ready for LLM prompt
        """
        # Build learner snapshot
        learner_snapshot = LearnerSnapshot.from_learner(self.full.learner)

        # Build outcome snapshots
        outcome_snapshot = None
        outcome_progress = None
        if self.full.active_outcome:
            outcome_snapshot = OutcomeSnapshot.from_outcome(self.full.active_outcome)
            outcome_progress = OutcomeProgress.from_outcome_and_concepts(
                outcome=self.full.active_outcome,
                concepts=self.full.outcome_concepts,
                proofs=self.full.proofs,
                current_concept=current_concept,
            )

        # Build concept snapshots
        current_concept_snapshot = None
        if current_concept:
            proof = next(
                (p for p in self.full.proofs if p.concept_id == current_concept.id),
                None
            )
            current_concept_snapshot = ConceptSnapshot.from_concept(
                current_concept, proof
            )

        proven_snapshots = self._build_proven_concept_snapshots()
        related_concepts = self._build_related_concepts(current_concept)

        # Build application snapshots
        pending_followup = self._get_pending_followup_snapshot()
        relevant_apps = self._get_relevant_applications(current_concept)

        # Get recent messages
        recent_messages = self._get_recent_messages(message_limit)

        # Build adaptation hints
        adaptation_hints = self._generate_adaptation_hints()

        return TurnContext(
            learner=learner_snapshot,
            insights=self.full.insights,
            mode=mode,
            session_context=self.session.context,
            current_concept=current_concept_snapshot,
            outcome=outcome_snapshot,
            outcome_progress=outcome_progress,
            recent_messages=recent_messages,
            session_summary=self.session.summary,
            proven_concepts=proven_snapshots,
            related_concepts=related_concepts,
            pending_followup=pending_followup,
            relevant_applications=relevant_apps,
            adaptation_hints=adaptation_hints,
        )

    def _build_proven_concept_snapshots(self) -> list[ConceptSnapshot]:
        """Build snapshots for all proven concepts."""
        snapshots = []
        for concept in self.full.proven_concepts:
            proof = next(
                (p for p in self.full.proofs if p.concept_id == concept.id),
                None
            )
            snapshots.append(ConceptSnapshot.from_concept(concept, proof))
        return snapshots

    def _build_related_concepts(
        self,
        current_concept: Optional[Concept],
    ) -> list[RelatedConcept]:
        """Find concepts related to current context."""
        if not current_concept:
            return []

        related = []
        edges = self.full.concept_relations.get(current_concept.id, [])

        for edge in edges:
            # Find the other concept in this relationship
            other_id = (
                edge.to_id if edge.from_id == current_concept.id else edge.from_id
            )
            other_concept = next(
                (c for c in self.full.proven_concepts if c.id == other_id),
                None
            )
            if other_concept:
                related.append(
                    RelatedConcept.from_concept_and_edge(other_concept, edge)
                )

        # Sort by strength descending
        related.sort(key=lambda r: r.strength, reverse=True)
        return related

    def _get_pending_followup_snapshot(self) -> Optional[ApplicationSnapshot]:
        """Get the most urgent pending follow-up."""
        if not self.full.pending_followups:
            return None

        # Get the first (most urgent) pending follow-up
        app = self.full.pending_followups[0]
        return ApplicationSnapshot.from_application_event(app, self._concept_name_map)

    def _get_relevant_applications(
        self,
        current_concept: Optional[Concept],
    ) -> list[ApplicationSnapshot]:
        """Get applications relevant to current teaching."""
        if not current_concept:
            return []

        relevant = []
        for app in self.full.completed_applications:
            if current_concept.id in app.concept_ids:
                relevant.append(
                    ApplicationSnapshot.from_application_event(
                        app, self._concept_name_map
                    )
                )

        # Limit to most recent 3
        return relevant[:3]

    def _get_recent_messages(self, limit: int) -> list[Message]:
        """Get the most recent messages from the session."""
        messages = self.session.messages
        if len(messages) <= limit:
            return messages
        return messages[-limit:]

    def _generate_adaptation_hints(self) -> list[str]:
        """Generate adaptation hints based on current state.

        These hints help the LLM adjust its approach based on
        Set/Setting/Intention and learner patterns.
        """
        hints = []
        ctx = self.session.context

        if not ctx:
            return hints

        # Energy-based hints
        if ctx.energy == EnergyLevel.LOW:
            hints.append("Keep explanations SHORT and practical")
            hints.append("Focus on one thing at a time")
            hints.append("Offer breaks proactively")

        if ctx.energy == EnergyLevel.HIGH:
            hints.append("Can go deeper and explore tangents")
            hints.append("Challenge with harder questions")

        # Time-based hints
        if ctx.time_available:
            time_lower = ctx.time_available.lower()
            if any(t in time_lower for t in ["15", "short", "quick"]):
                hints.append("Acknowledge time constraint")
                hints.append("Prioritize ruthlessly")
                hints.append("End with clear next step for later")

        # Intention-based hints
        if ctx.intention_strength == IntentionStrength.URGENT:
            hints.append("Skip background theory")
            hints.append("Focus on immediate applicability")
            hints.append("What's the ONE thing they need?")

        if ctx.intention_strength == IntentionStrength.CURIOUS:
            hints.append("Can explore freely without pressure")
            hints.append("Follow interesting tangents")

        # Mindset-based hints
        if ctx.mindset:
            mindset_lower = ctx.mindset.lower()
            if "stress" in mindset_lower or "anxious" in mindset_lower:
                hints.append("Gentler pace, smaller steps")
                hints.append("Acknowledge the pressure")

            if "tired" in mindset_lower or "fatigue" in mindset_lower:
                hints.append("Very short chunks only")
                hints.append("Consider wrapping up soon")

        # Learner insight-based hints
        insights = self.full.insights

        if insights.prefers_examples:
            hints.append("Lead with concrete examples")

        if insights.prefers_theory_first:
            hints.append("Explain the 'why' before the 'how'")

        if insights.needs_frequent_checks:
            hints.append("Check understanding frequently")

        if insights.responds_to_challenge:
            hints.append("Can use challenging questions")

        # Long break handling
        if self.full.days_since_last_session and self.full.days_since_last_session > 14:
            hints.append("Long break detected - verify key concepts still solid")

        return hints


def build_turn_context(
    full_context: FullContext,
    session: Session,
    mode: DialogueMode,
    current_concept: Optional[Concept] = None,
) -> TurnContext:
    """Convenience function to build turn context.

    Args:
        full_context: The eagerly loaded session context
        session: The current session
        mode: The current dialogue mode
        current_concept: The concept being worked on (if any)

    Returns:
        TurnContext ready for LLM prompt
    """
    builder = TurnContextBuilder(full_context, session)
    return builder.build(mode, current_concept)
