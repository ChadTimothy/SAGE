"""Graph queries for SAGE Learning Graph.

Higher-level queries that combine multiple store operations to answer
questions about the learner's state and progress.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .models import (
    ApplicationEvent,
    Concept,
    Edge,
    Learner,
    Outcome,
    Proof,
    Session,
)
from .store import GraphStore


@dataclass
class LearnerState:
    """Complete state of a learner for session continuity."""

    learner: Learner
    active_outcome: Optional[Outcome]
    last_session: Optional[Session]
    proven_concepts: list[Concept]  # Concepts with proofs
    pending_followups: list[ApplicationEvent]
    total_proofs: int


@dataclass
class RelatedConcept:
    """A concept related to another through an edge."""

    concept: Concept
    relationship: str  # How they connect
    strength: float  # Connection strength
    has_proof: bool  # Whether learner has proven this concept


# PastApplication is simply an alias for ApplicationEvent.
# The wrapper class was removed since it only delegated to the underlying event.
# Code that needs ApplicationEvent data can access event attributes directly.
PastApplication = ApplicationEvent


class GraphQueries:
    """Query interface for the learning graph.

    Provides higher-level queries that combine basic store operations
    to answer questions about learning state and progress.
    """

    def __init__(self, store: GraphStore):
        self.store = store

    def get_learner_state(self, learner_id: str) -> Optional[LearnerState]:
        """Get complete learner state for session continuity.

        This is the "where did we leave off?" query that provides
        everything needed to resume a learning session.

        Returns:
            LearnerState with all relevant context, or None if learner not found.
        """
        learner = self.store.get_learner(learner_id)
        if learner is None:
            return None

        # Get active outcome if any
        active_outcome = None
        if learner.active_outcome_id:
            active_outcome = self.store.get_outcome(learner.active_outcome_id)

        # Get last session
        last_session = self.store.get_last_session(learner_id)

        # Get all concepts with proofs (proven understanding)
        proofs = self.store.get_proofs_by_learner(learner_id)
        proven_concept_ids = {p.concept_id for p in proofs}
        proven_concepts = []
        for concept_id in proven_concept_ids:
            concept = self.store.get_concept(concept_id)
            if concept:
                proven_concepts.append(concept)

        # Get pending follow-ups
        pending_followups = self.store.get_pending_followups(learner_id)

        return LearnerState(
            learner=learner,
            active_outcome=active_outcome,
            last_session=last_session,
            proven_concepts=proven_concepts,
            pending_followups=pending_followups,
            total_proofs=len(proofs),
        )

    def get_proven_concepts(self, learner_id: str) -> list[tuple[Concept, Proof]]:
        """Get all concepts the learner has proven understanding of.

        Returns:
            List of (Concept, most recent Proof) tuples.
        """
        proofs = self.store.get_proofs_by_learner(learner_id)

        # Group by concept, keeping most recent proof
        concept_proofs: dict[str, Proof] = {}
        for proof in proofs:
            if proof.concept_id not in concept_proofs:
                concept_proofs[proof.concept_id] = proof
            elif proof.earned_at > concept_proofs[proof.concept_id].earned_at:
                concept_proofs[proof.concept_id] = proof

        result = []
        for concept_id, proof in concept_proofs.items():
            concept = self.store.get_concept(concept_id)
            if concept:
                result.append((concept, proof))

        return result

    def find_related_concepts(
        self, concept_id: str, learner_id: str
    ) -> list[RelatedConcept]:
        """Find concepts related to the given concept.

        Looks for relates_to edges and checks if the learner has
        proven the related concepts.

        Args:
            concept_id: The concept to find relations for
            learner_id: The learner to check proofs for

        Returns:
            List of related concepts with relationship info.
        """
        edges_from = self.store.get_edges_from(concept_id, edge_type="relates_to")
        edges_to = self.store.get_edges_to(concept_id, edge_type="relates_to")

        proofs = self.store.get_proofs_by_learner(learner_id)
        proven_ids = {p.concept_id for p in proofs}

        # Build list of (related_concept_id, edge) pairs from both directions
        edge_pairs = [(e.to_id, e) for e in edges_from] + [(e.from_id, e) for e in edges_to]

        result = []
        for related_id, edge in edge_pairs:
            related = self.store.get_concept(related_id)
            if related:
                result.append(
                    RelatedConcept(
                        concept=related,
                        relationship=edge.metadata.get("relationship", "related"),
                        strength=edge.metadata.get("strength", 0.5),
                        has_proof=related.id in proven_ids,
                    )
                )

        result.sort(key=lambda x: x.strength, reverse=True)
        return result

    def get_applications_for_concept(
        self, concept_id: str, learner_id: str, completed_only: bool = True
    ) -> list[PastApplication]:
        """Get past applications of a concept for teaching context.

        Useful for referencing past real-world usage when teaching
        related concepts.

        Args:
            concept_id: The concept to find applications for
            learner_id: The learner to search for
            completed_only: If True, only return completed applications

        Returns:
            List of past applications with outcome details.
        """
        events = self.store.get_application_events_by_learner(learner_id)

        if completed_only:
            events = [e for e in events if e.status.value == "completed"]

        return [e for e in events if concept_id in e.concept_ids]

    def find_connections_to_known(
        self, new_concept_name: str, learner_id: str
    ) -> list[RelatedConcept]:
        """Find connections from a new concept to concepts the learner knows.

        Used when introducing a new concept to find anchors in
        existing knowledge.

        Args:
            new_concept_name: Name of the concept being introduced
            learner_id: The learner to check knowledge for

        Returns:
            Related concepts that the learner has proven.
        """
        # First, find if there's a concept with this name for this learner
        concepts = self.store.get_concepts_by_learner(learner_id)
        new_concept = next(
            (c for c in concepts if c.name == new_concept_name), None
        )

        if new_concept is None:
            return []

        # Get related concepts that have proofs
        related = self.find_related_concepts(new_concept.id, learner_id)
        return [r for r in related if r.has_proof]

    def get_outcome_progress(self, outcome_id: str) -> dict:
        """Get progress on an outcome including concepts and proofs.

        Returns:
            Dictionary with outcome details and progress stats.
        """
        outcome = self.store.get_outcome(outcome_id)
        if outcome is None:
            return {}

        concepts = self.store.get_concepts_by_outcome(outcome_id)

        # Count proven vs teaching vs identified
        status_counts = {"identified": 0, "teaching": 0, "understood": 0}
        for concept in concepts:
            status_counts[concept.status.value] += 1

        return {
            "outcome": outcome,
            "total_concepts": len(concepts),
            "concepts_identified": status_counts["identified"],
            "concepts_teaching": status_counts["teaching"],
            "concepts_understood": status_counts["understood"],
            "concepts": concepts,
        }

    def get_learning_history(
        self, learner_id: str, limit: int = 10
    ) -> list[dict]:
        """Get recent learning history with sessions and achievements.

        Returns:
            List of session summaries with what was learned.
        """
        sessions = self.store.get_sessions_by_learner(learner_id, limit=limit)

        history = []
        for session in sessions:
            # Get concepts explored in this session
            explored_concepts = []
            for concept_id in session.concepts_explored:
                concept = self.store.get_concept(concept_id)
                if concept:
                    explored_concepts.append(concept)

            # Get proofs earned
            earned_proofs = []
            for proof_id in session.proofs_earned:
                proof = self.store.get_proof(proof_id)
                if proof:
                    earned_proofs.append(proof)

            history.append({
                "session": session,
                "concepts_explored": explored_concepts,
                "proofs_earned": earned_proofs,
                "summary": session.summary,
            })

        return history
