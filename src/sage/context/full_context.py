"""FullContext loader - loads everything needed at session start.

This module provides eager loading of all context needed for a session,
avoiding database queries on every turn.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sage.graph.learning_graph import LearningGraph
from sage.graph.models import (
    ApplicationEvent,
    ApplicationStatus,
    Concept,
    Edge,
    EdgeType,
    Learner,
    LearnerInsights,
    Outcome,
    Proof,
    Session,
)


@dataclass
class FullContext:
    """Everything loaded at session start.

    This is eagerly loaded to avoid database queries on every turn.
    The session typically touches all this data anyway.
    """

    # WHO
    learner: Learner
    insights: LearnerInsights

    # KNOWLEDGE (what they've proven)
    proven_concepts: list[Concept]
    proofs: list[Proof]  # All proofs for this learner

    # CURRENT GOAL
    active_outcome: Optional[Outcome]
    outcome_concepts: list[Concept]  # Concepts found for this outcome

    # CONTINUITY
    last_session: Optional[Session]
    days_since_last_session: Optional[int]

    # CONNECTIONS (for fast lookup)
    concept_relations: dict[str, list[Edge]]  # concept_id -> related edges

    # PENDING FOLLOW-UPS (checked before check-in)
    pending_followups: list[ApplicationEvent]

    # PAST APPLICATIONS (for teaching context)
    completed_applications: list[ApplicationEvent]

    # ALL CONCEPTS (for reference)
    all_concepts: list[Concept]


class FullContextLoader:
    """Loads full context for a session."""

    def __init__(self, graph: LearningGraph):
        """Initialize with a LearningGraph instance."""
        self.graph = graph

    def load(self, learner_id: str) -> FullContext:
        """Load everything needed for a session.

        Args:
            learner_id: The learner's ID

        Returns:
            FullContext with all data loaded

        Raises:
            ValueError: If learner not found
        """
        # Load learner
        learner = self.graph.get_learner(learner_id)
        if not learner:
            raise ValueError(f"Learner not found: {learner_id}")

        # Load all data in parallel where possible
        all_concepts = self._load_all_concepts(learner_id)
        proofs = self._load_all_proofs(learner_id)
        proven_concept_ids = {p.concept_id for p in proofs}

        # Split concepts into proven and all
        proven_concepts = [c for c in all_concepts if c.id in proven_concept_ids]

        # Load active outcome and its concepts
        active_outcome = None
        outcome_concepts = []
        if learner.active_outcome_id:
            active_outcome = self.graph.get_outcome(learner.active_outcome_id)
            if active_outcome:
                outcome_concepts = [
                    c for c in all_concepts
                    if c.discovered_from == active_outcome.id
                ]

        # Load last session
        last_session = self._load_last_session(learner_id)
        days_since = None
        if last_session and last_session.ended_at:
            days_since = (datetime.utcnow() - last_session.ended_at).days

        # Load concept relations
        concept_relations = self._load_concept_relations(all_concepts)

        # Load application events
        pending_followups = self._load_pending_followups(learner_id)
        completed_applications = self._load_completed_applications(learner_id)

        return FullContext(
            learner=learner,
            insights=learner.insights,
            proven_concepts=proven_concepts,
            proofs=proofs,
            active_outcome=active_outcome,
            outcome_concepts=outcome_concepts,
            last_session=last_session,
            days_since_last_session=days_since,
            concept_relations=concept_relations,
            pending_followups=pending_followups,
            completed_applications=completed_applications,
            all_concepts=all_concepts,
        )

    def _load_all_concepts(self, learner_id: str) -> list[Concept]:
        """Load all concepts for a learner."""
        return self.graph.get_concepts_by_learner(learner_id)

    def _load_all_proofs(self, learner_id: str) -> list[Proof]:
        """Load all proofs for a learner."""
        return self.graph.get_proofs_by_learner(learner_id)

    def _load_last_session(self, learner_id: str) -> Optional[Session]:
        """Load the most recent session."""
        sessions = self.graph.get_sessions_by_learner(learner_id)
        if not sessions:
            return None
        # Sort by started_at descending and return the most recent
        return max(sessions, key=lambda s: s.started_at)

    def _load_concept_relations(
        self,
        all_concepts: list[Concept],
    ) -> dict[str, list[Edge]]:
        """Load all relates_to edges for quick lookup."""
        relations: dict[str, list[Edge]] = {}

        for concept in all_concepts:
            edges = self.graph.get_edges_from(concept.id, EdgeType.RELATES_TO)
            edges.extend(self.graph.get_edges_to(concept.id, EdgeType.RELATES_TO))
            if edges:
                relations[concept.id] = edges

        return relations

    def _load_pending_followups(self, learner_id: str) -> list[ApplicationEvent]:
        """Load applications that need follow-up."""
        all_apps = self.graph.get_application_events_by_learner(learner_id)
        today = datetime.utcnow().date()

        pending = []
        for app in all_apps:
            # Include if status is pending_followup
            if app.status == ApplicationStatus.PENDING_FOLLOWUP:
                pending.append(app)
            # Include if upcoming and planned_date has passed
            elif app.status == ApplicationStatus.UPCOMING:
                if app.planned_date and app.planned_date <= today:
                    pending.append(app)

        # Sort by planned_date
        pending.sort(key=lambda a: a.planned_date or datetime.max.date())
        return pending

    def _load_completed_applications(self, learner_id: str) -> list[ApplicationEvent]:
        """Load completed applications for teaching context."""
        all_apps = self.graph.get_application_events_by_learner(learner_id)
        completed = [
            app for app in all_apps
            if app.status == ApplicationStatus.COMPLETED
        ]
        # Sort by most recent first
        completed.sort(
            key=lambda a: a.followed_up_at or a.created_at,
            reverse=True
        )
        return completed

    def get_concepts_needing_reverification(
        self,
        context: FullContext,
        days_threshold: int = 60,
    ) -> list[Concept]:
        """Find proven concepts that may have decayed.

        Args:
            context: The loaded full context
            days_threshold: Days since proof before reverification needed

        Returns:
            List of concepts that should be reverified
        """
        threshold_date = datetime.utcnow() - timedelta(days=days_threshold)
        needs_check = []

        for proof in context.proofs:
            if proof.earned_at < threshold_date:
                # Find the concept
                concept = next(
                    (c for c in context.proven_concepts if c.id == proof.concept_id),
                    None
                )
                if concept:
                    needs_check.append(concept)

        return needs_check
