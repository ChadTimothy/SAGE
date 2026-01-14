"""Gap storage and persistence.

This module handles creating concepts from identified gaps and
linking them to outcomes in the learning graph.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sage.dialogue.structured_output import GapIdentified
from sage.graph.learning_graph import LearningGraph
from sage.graph.models import Concept, ConceptStatus, Edge, EdgeType


logger = logging.getLogger(__name__)


class GapStore:
    """Stores identified gaps as concepts in the learning graph.

    Handles:
    - Creating Concept from GapIdentified
    - Linking concept to outcome with 'requires' edge
    - Updating concept status as learning progresses
    """

    def __init__(self, graph: LearningGraph):
        """Initialize with a learning graph.

        Args:
            graph: The learning graph to store gaps in
        """
        self.graph = graph

    def create_concept_from_gap(
        self,
        gap: GapIdentified,
        learner_id: str,
        outcome_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Concept:
        """Create a concept from an identified gap.

        Args:
            gap: The gap identified by the LLM
            learner_id: The learner this gap belongs to
            outcome_id: The outcome this gap blocks (optional)
            session_id: The session where this was discovered (optional)

        Returns:
            The created Concept
        """
        concept_id = str(uuid4())

        concept = Concept(
            id=concept_id,
            name=gap.name,
            display_name=gap.display_name,
            description=gap.description,
            learner_id=learner_id,
            status=ConceptStatus.IDENTIFIED,
            discovered_from=outcome_id,
            discovered_at=datetime.utcnow(),
        )

        # Create the concept in the graph
        created_concept = self.graph.create_concept_obj(concept)
        logger.info(f"Created concept from gap: {concept.display_name} ({concept.id})")

        # Link to outcome if provided
        if outcome_id:
            self.link_gap_to_outcome(created_concept.id, outcome_id)

        return created_concept

    def link_gap_to_outcome(self, concept_id: str, outcome_id: str) -> Edge:
        """Link a gap concept to an outcome with 'requires' edge.

        Args:
            concept_id: The concept ID
            outcome_id: The outcome ID

        Returns:
            The created edge
        """
        edge = Edge(
            id=str(uuid4()),
            from_id=outcome_id,
            from_type="outcome",
            to_id=concept_id,
            to_type="concept",
            edge_type="requires",
            metadata={
                "reason": "Gap identified during probing",
                "created_at": datetime.utcnow().isoformat(),
            },
        )

        created_edge = self.graph.create_edge(edge)
        logger.info(f"Linked concept {concept_id} to outcome {outcome_id}")
        return created_edge

    def update_gap_status(
        self,
        concept_id: str,
        new_status: ConceptStatus,
    ) -> Optional[Concept]:
        """Update the status of a gap concept.

        Args:
            concept_id: The concept to update
            new_status: The new status

        Returns:
            The updated concept, or None if not found
        """
        concept = self.graph.get_concept(concept_id)
        if concept is None:
            logger.warning(f"Concept not found: {concept_id}")
            return None

        old_status = concept.status
        concept.status = new_status
        # Set understood_at when marking as understood
        if new_status == ConceptStatus.UNDERSTOOD:
            concept.understood_at = datetime.utcnow()

        self.graph.update_concept(concept)
        logger.info(
            f"Updated concept {concept_id} status: {old_status.value} -> {new_status.value}"
        )
        return concept

    def mark_teaching_started(self, concept_id: str) -> Optional[Concept]:
        """Mark a concept as being taught.

        Args:
            concept_id: The concept ID

        Returns:
            The updated concept
        """
        return self.update_gap_status(concept_id, ConceptStatus.TEACHING)

    def mark_understood(self, concept_id: str) -> Optional[Concept]:
        """Mark a concept as understood (proof earned).

        Args:
            concept_id: The concept ID

        Returns:
            The updated concept
        """
        return self.update_gap_status(concept_id, ConceptStatus.UNDERSTOOD)

    def get_gaps_for_outcome(self, outcome_id: str) -> list[Concept]:
        """Get all gap concepts for an outcome.

        Args:
            outcome_id: The outcome ID

        Returns:
            List of concepts linked to this outcome
        """
        return self.graph.get_concepts_for_outcome(outcome_id)

    def get_unresolved_gaps(self, outcome_id: str) -> list[Concept]:
        """Get gaps that haven't been proven yet.

        Args:
            outcome_id: The outcome ID

        Returns:
            List of concepts not yet understood
        """
        all_concepts = self.get_gaps_for_outcome(outcome_id)
        return [c for c in all_concepts if c.status != ConceptStatus.UNDERSTOOD]

    def get_current_gap(self, outcome_id: str) -> Optional[Concept]:
        """Get the concept currently being taught.

        Args:
            outcome_id: The outcome ID

        Returns:
            The concept in TEACHING status, or None
        """
        concepts = self.get_gaps_for_outcome(outcome_id)
        teaching = [c for c in concepts if c.status == ConceptStatus.TEACHING]
        return teaching[0] if teaching else None

    def find_existing_gap(
        self, name: str, learner_id: str
    ) -> Optional[Concept]:
        """Find if a gap already exists for this learner.

        Useful to avoid creating duplicate concepts.

        Args:
            name: The gap name
            learner_id: The learner ID

        Returns:
            Existing concept if found, None otherwise
        """
        concepts = self.graph.get_concepts_by_learner(learner_id)
        return next((c for c in concepts if c.name == name), None)

    def create_or_update_gap(
        self,
        gap: GapIdentified,
        learner_id: str,
        outcome_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Concept:
        """Create a new gap concept or return existing.

        If a concept with the same name already exists for this learner,
        it will be linked to the new outcome (if different) rather than
        creating a duplicate.

        Args:
            gap: The gap identified by the LLM
            learner_id: The learner this gap belongs to
            outcome_id: The outcome this gap blocks
            session_id: The session where discovered

        Returns:
            The concept (created or existing)
        """
        existing = self.find_existing_gap(gap.name, learner_id)

        if existing:
            logger.info(f"Found existing concept for gap: {gap.name}")
            # If new outcome provided, link it
            if outcome_id:
                # Check if already linked
                edges = self.graph.get_edges_to(existing.id, edge_type=EdgeType.REQUIRES)
                linked_outcomes = {e.from_id for e in edges}
                if outcome_id not in linked_outcomes:
                    self.link_gap_to_outcome(existing.id, outcome_id)
            return existing

        return self.create_concept_from_gap(gap, learner_id, outcome_id, session_id)
