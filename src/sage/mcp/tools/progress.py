"""Progress and graph-related MCP tools for SAGE.

These tools provide visibility into learning progress.
"""

import logging
from typing import Any

from sage.core.config import get_settings
from sage.graph.learning_graph import LearningGraph

logger = logging.getLogger(__name__)


def _get_default_graph() -> LearningGraph:
    """Get default learning graph instance."""
    settings = get_settings()
    return LearningGraph(settings.db_path)


async def sage_progress(
    learner_id: str,
    graph: LearningGraph | None = None,
) -> dict[str, Any]:
    """Get the learner's overall progress summary.

    Returns statistics about learning progress including:
    - Total sessions completed
    - Proofs earned (demonstrations of understanding)
    - Active learning goal
    - Recent concepts learned

    Args:
        learner_id: The learner's ID
        graph: Optional LearningGraph instance (uses default if not provided)

    Returns:
        dict with progress statistics and recent activity
    """
    if graph is None:
        graph = _get_default_graph()
    learner = graph.get_learner(learner_id)

    if not learner:
        return {"error": "Learner not found"}

    # Get active outcome
    active_outcome = None
    if learner.active_outcome_id:
        outcome = graph.get_outcome(learner.active_outcome_id)
        if outcome:
            active_outcome = {
                "id": outcome.id,
                "goal": outcome.stated_goal,
                "status": outcome.status.value,
            }

    # Get recent concepts
    concepts = graph.get_concepts_by_learner(learner_id)
    recent_concepts = [
        {
            "id": c.id,
            "name": c.display_name,
            "status": c.status.value,
        }
        for c in concepts[:5]
    ]

    # Get recent proofs
    proofs = graph.get_proofs_by_learner(learner_id)
    recent_proofs = [
        {
            "id": p.id,
            "concept_id": p.concept_id,
            "type": p.demonstration_type.value,
            "confidence": p.confidence,
            "earned_at": p.earned_at.isoformat(),
        }
        for p in proofs[:5]
    ]

    # Get outcomes completed
    outcomes = graph.get_outcomes_by_learner(learner_id)
    completed_outcomes = [o for o in outcomes if o.achieved_at]

    return {
        "learner_name": learner.profile.name or "Learner",
        "total_sessions": learner.total_sessions,
        "total_proofs": learner.total_proofs,
        "outcomes_completed": len(completed_outcomes),
        "outcomes_total": len(outcomes),
        "active_outcome": active_outcome,
        "recent_concepts": recent_concepts,
        "recent_proofs": recent_proofs,
    }


async def sage_graph(
    learner_id: str,
    include_proofs: bool = True,
    include_edges: bool = True,
    graph: LearningGraph | None = None,
) -> dict[str, Any]:
    """Get the learner's knowledge graph for visualization.

    Returns the full knowledge graph including:
    - Outcomes (learning goals)
    - Concepts (topics learned)
    - Proofs (demonstrations of understanding)
    - Connections between them

    This can be used to visualize learning progress.

    Args:
        learner_id: The learner's ID
        include_proofs: Whether to include proof nodes (default: True)
        include_edges: Whether to include edge connections (default: True)
        graph: Optional LearningGraph instance (uses default if not provided)

    Returns:
        dict with nodes and edges for graph visualization
    """
    if graph is None:
        graph = _get_default_graph()
    learner = graph.get_learner(learner_id)

    if not learner:
        return {"error": "Learner not found"}

    nodes = []
    edges = []

    # Add learner node
    nodes.append({
        "id": learner.id,
        "type": "learner",
        "label": learner.profile.name or "You",
        "data": {
            "skill_level": learner.profile.skill_level.value if learner.profile.skill_level else "beginner",
        },
    })

    # Add outcome nodes
    outcomes = graph.get_outcomes_by_learner(learner_id)
    for o in outcomes:
        nodes.append({
            "id": o.id,
            "type": "outcome",
            "label": o.stated_goal[:50] + ("..." if len(o.stated_goal) > 50 else ""),
            "data": {
                "status": o.status.value,
                "achieved": o.achieved_at is not None,
            },
        })

    # Add concept nodes
    concepts = graph.get_concepts_by_learner(learner_id)
    for c in concepts:
        nodes.append({
            "id": c.id,
            "type": "concept",
            "label": c.display_name,
            "data": {
                "status": c.status.value,
            },
        })

    # Add proof nodes if requested
    if include_proofs:
        proofs = graph.get_proofs_by_learner(learner_id)
        for p in proofs:
            nodes.append({
                "id": p.id,
                "type": "proof",
                "label": f"Proof: {p.demonstration_type.value}",
                "data": {
                    "confidence": p.confidence,
                    "concept_id": p.concept_id,
                },
            })

    # Add edges if requested
    if include_edges:
        all_ids = {n["id"] for n in nodes}
        for node_id in all_ids:
            node_edges = graph.get_edges_from(node_id)
            for e in node_edges:
                if e.to_id in all_ids:
                    edges.append({
                        "id": e.id,
                        "from": e.from_id,
                        "to": e.to_id,
                        "type": e.edge_type.value if hasattr(e.edge_type, 'value') else str(e.edge_type),
                    })

    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }
