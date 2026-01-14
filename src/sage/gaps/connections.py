"""Connection discovery between concepts.

This module handles finding and persisting connections between concepts,
enabling "Remember when you learned X?" style teaching.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sage.dialogue.structured_output import ConnectionDiscovered
from sage.graph.learning_graph import LearningGraph
from sage.graph.models import Edge, EdgeType
from sage.graph.queries import GraphQueries, RelatedConcept


logger = logging.getLogger(__name__)


@dataclass
class ConnectionCandidate:
    """A potential connection to use in teaching."""

    concept_id: str
    concept_name: str
    display_name: str
    relationship: str
    strength: float
    has_proof: bool
    teaching_hook: str  # How to reference in teaching


class ConnectionFinder:
    """Finds and manages connections between concepts.

    Used to:
    - Find connections to proven concepts for teaching anchors
    - Persist connections discovered by the LLM
    - Generate teaching hooks like "Remember when you learned X?"
    """

    def __init__(self, graph: LearningGraph, queries: Optional[GraphQueries] = None):
        """Initialize with a learning graph.

        Args:
            graph: The learning graph
            queries: Optional GraphQueries instance (created if not provided)
        """
        self.graph = graph
        self.queries = queries or GraphQueries(graph.store)

    def find_connections_for_teaching(
        self,
        concept_id: str,
        learner_id: str,
        max_connections: int = 5,
    ) -> list[ConnectionCandidate]:
        """Find connections to use when teaching a concept.

        Prioritizes proven concepts (things they already know) as
        anchors for new learning.

        Args:
            concept_id: The concept being taught
            learner_id: The learner
            max_connections: Maximum connections to return

        Returns:
            List of connection candidates for teaching
        """
        related = self.queries.find_related_concepts(concept_id, learner_id)
        candidates = [self._to_candidate(rel) for rel in related]

        # Sort: proven first, then by strength
        candidates.sort(key=lambda x: (not x.has_proof, -x.strength))
        return candidates[:max_connections]

    def find_anchors_for_new_concept(
        self,
        concept_name: str,
        learner_id: str,
    ) -> list[ConnectionCandidate]:
        """Find existing knowledge to anchor a new concept.

        Used when introducing something new to find "in" points
        from what they already know.

        Args:
            concept_name: Name of the new concept
            learner_id: The learner

        Returns:
            Proven concepts that connect to this topic
        """
        related = self.queries.find_connections_to_known(concept_name, learner_id)
        return [self._to_candidate(rel, has_proof_override=True) for rel in related]

    def _to_candidate(
        self, rel: RelatedConcept, has_proof_override: Optional[bool] = None
    ) -> ConnectionCandidate:
        """Convert a RelatedConcept to a ConnectionCandidate."""
        has_proof = has_proof_override if has_proof_override is not None else rel.has_proof
        return ConnectionCandidate(
            concept_id=rel.concept.id,
            concept_name=rel.concept.name,
            display_name=rel.concept.display_name,
            relationship=rel.relationship,
            strength=rel.strength,
            has_proof=has_proof,
            teaching_hook=self._generate_teaching_hook(rel),
        )

    def persist_discovered_connection(
        self,
        connection: ConnectionDiscovered,
    ) -> Edge:
        """Persist a connection discovered by the LLM.

        Args:
            connection: The connection discovered during conversation

        Returns:
            The created edge
        """
        edge = Edge(
            id=str(uuid4()),
            from_id=connection.from_concept_id,
            from_type="concept",
            to_id=connection.to_concept_id,
            to_type="concept",
            edge_type="relates_to",
            metadata={
                "relationship": connection.relationship,
                "strength": connection.strength,
                "used_in_teaching": connection.used_in_teaching,
                "discovered_at": datetime.utcnow().isoformat(),
                "source": "llm_discovery",
            },
        )

        created = self.graph.create_edge(edge)
        logger.info(
            f"Persisted connection: {connection.from_concept_id} "
            f"--[{connection.relationship}]--> {connection.to_concept_id}"
        )
        return created

    def get_connections_for_concept(self, concept_id: str) -> list[Edge]:
        """Get all connections for a concept.

        Args:
            concept_id: The concept ID

        Returns:
            List of edges (both directions)
        """
        edges_from = self.graph.get_edges_from(concept_id, edge_type=EdgeType.RELATES_TO)
        edges_to = self.graph.get_edges_to(concept_id, edge_type=EdgeType.RELATES_TO)
        return edges_from + edges_to

    def connection_exists(
        self,
        from_concept_id: str,
        to_concept_id: str,
    ) -> bool:
        """Check if a connection already exists.

        Checks both directions since relates_to is symmetric.

        Args:
            from_concept_id: One concept
            to_concept_id: The other concept

        Returns:
            True if a connection exists in either direction
        """
        # Check forward direction
        edges_forward = self.graph.get_edges_from(
            from_concept_id, edge_type=EdgeType.RELATES_TO
        )
        if any(e.to_id == to_concept_id for e in edges_forward):
            return True

        # Check reverse direction
        edges_reverse = self.graph.get_edges_from(
            to_concept_id, edge_type=EdgeType.RELATES_TO
        )
        return any(e.to_id == from_concept_id for e in edges_reverse)

    def create_or_update_connection(
        self,
        connection: ConnectionDiscovered,
    ) -> Edge:
        """Create a connection or update if exists.

        If connection already exists, updates the strength and
        marks as used in teaching if applicable.

        Args:
            connection: The discovered connection

        Returns:
            The edge (created or updated)
        """
        if self.connection_exists(
            connection.from_concept_id, connection.to_concept_id
        ):
            logger.info(
                f"Connection already exists: {connection.from_concept_id} "
                f"-> {connection.to_concept_id}"
            )
            # Get existing edge and update it
            edges = self.graph.get_edges_from(
                connection.from_concept_id, edge_type=EdgeType.RELATES_TO
            )
            existing = next(
                (e for e in edges if e.to_id == connection.to_concept_id), None
            )

            if existing:
                # Update metadata
                existing.metadata["strength"] = max(
                    existing.metadata.get("strength", 0), connection.strength
                )
                if connection.used_in_teaching:
                    existing.metadata["used_in_teaching"] = True
                existing.metadata["updated_at"] = datetime.utcnow().isoformat()
                return self.graph.update_edge(existing)

        return self.persist_discovered_connection(connection)

    # Teaching hook templates by relationship type (for proven concepts)
    PROVEN_HOOK_TEMPLATES = {
        "builds_on": "This builds on {name}, which you already understand.",
        "prerequisite": "This builds on {name}, which you already understand.",
        "contrasts": "Unlike {name}, this works differently.",
        "similar_to": "This is similar to {name}.",
    }
    DEFAULT_PROVEN_HOOK = "Remember {name}? This connects to that."
    UNPROVEN_HOOK = "This relates to {name}."

    def _generate_teaching_hook(self, related: RelatedConcept) -> str:
        """Generate a teaching hook for referencing a related concept."""
        name = related.concept.display_name

        if not related.has_proof:
            return self.UNPROVEN_HOOK.format(name=name)

        template = self.PROVEN_HOOK_TEMPLATES.get(
            related.relationship, self.DEFAULT_PROVEN_HOOK
        )
        return template.format(name=name)


def get_connection_hints_for_prompt(
    candidates: list[ConnectionCandidate],
) -> str:
    """Generate connection hints for the LLM prompt.

    Args:
        candidates: Connection candidates found

    Returns:
        Markdown hints for the prompt
    """
    if not candidates:
        return ""

    lines = ["## Connections to Leverage"]
    lines.append(
        "\n*Use these connections to anchor new learning in what they already know:*\n"
    )

    for candidate in candidates:
        proven = "✓ proven" if candidate.has_proof else "not yet proven"
        lines.append(f"- **{candidate.display_name}** ({proven})")
        lines.append(f"  - Relationship: {candidate.relationship}")
        lines.append(f"  - Teaching hook: \"{candidate.teaching_hook}\"")

    lines.append(
        "\n*Reference proven concepts directly. For unproven, mention but don't assume.*"
    )
    return "\n".join(lines)
