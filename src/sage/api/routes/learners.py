"""Learner API routes."""

from fastapi import APIRouter, HTTPException

from sage.graph.models import AgeGroup, Learner, LearnerProfile, SkillLevel

from ..deps import Graph, User, Verifier
from ..schemas import (
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphResponse,
    LearnerCreate,
    LearnerResponse,
    LearnerStateResponse,
    OutcomeResponse,
    ProofResponse,
)

router = APIRouter(prefix="/api/learners", tags=["learners"])


def _learner_to_response(learner: Learner) -> LearnerResponse:
    """Convert Learner model to response schema."""
    profile = learner.profile
    age_group = profile.age_group.value if profile.age_group else "adult"
    skill_level = profile.skill_level.value if profile.skill_level else "beginner"

    return LearnerResponse(
        id=learner.id,
        name=profile.name or "Anonymous",
        age_group=age_group,
        skill_level=skill_level,
        active_outcome_id=learner.active_outcome_id,
        total_sessions=learner.total_sessions,
        total_proofs=learner.total_proofs,
        created_at=learner.created_at,
    )


@router.post("", response_model=LearnerResponse)
def create_learner(
    data: LearnerCreate,
    user: User,
    graph: Graph,
) -> LearnerResponse:
    """Create a new learner.

    Note: This endpoint is deprecated. Learners are created during registration.
    This remains for backward compatibility but only returns the user's own learner.
    """
    # Users can only access their own learner (created during registration)
    learner = graph.get_learner(user.learner_id)
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")
    return _learner_to_response(learner)


@router.get("/{learner_id}", response_model=LearnerResponse)
def get_learner(
    learner_id: str,
    user: User,
    graph: Graph,
    verifier: Verifier,
) -> LearnerResponse:
    """Get a learner by ID."""
    verifier.verify_learner(user, learner_id)
    learner = graph.get_learner(learner_id)
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")
    return _learner_to_response(learner)


@router.get("/{learner_id}/state", response_model=LearnerStateResponse)
def get_learner_state(
    learner_id: str,
    user: User,
    graph: Graph,
    verifier: Verifier,
) -> LearnerStateResponse:
    """Get full learner state for UI."""
    verifier.verify_learner(user, learner_id)
    learner = graph.get_learner(learner_id)
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    # Get active outcome
    active_outcome = None
    if learner.active_outcome_id:
        outcome = graph.get_outcome(learner.active_outcome_id)
        if outcome:
            active_outcome = {
                "id": outcome.id,
                "description": outcome.stated_goal,
                "status": outcome.status.value,
            }

    # Get recent concepts
    concepts = graph.get_concepts_by_learner(learner_id)
    recent_concepts = [
        {
            "id": c.id,
            "name": c.name,
            "display_name": c.display_name,
            "status": c.status.value,
        }
        for c in concepts[:10]
    ]

    # Get recent proofs
    proofs = graph.get_proofs_by_learner(learner_id)
    recent_proofs = [
        {
            "id": p.id,
            "concept_id": p.concept_id,
            "demonstration_type": p.demonstration_type.value,
            "confidence": p.confidence,
            "earned_at": p.earned_at.isoformat(),
        }
        for p in proofs[:10]
    ]

    # Get pending followups
    followups = graph.get_pending_followups(learner_id)
    pending_followups = [
        {
            "id": f.id,
            "context": f.context,
            "planned_date": f.planned_date.isoformat() if f.planned_date else None,
        }
        for f in followups[:5]
    ]

    return LearnerStateResponse(
        learner=_learner_to_response(learner),
        active_outcome=active_outcome,
        recent_concepts=recent_concepts,
        recent_proofs=recent_proofs,
        pending_followups=pending_followups,
    )


@router.get("/{learner_id}/outcomes", response_model=list[OutcomeResponse])
def get_learner_outcomes(
    learner_id: str,
    user: User,
    graph: Graph,
    verifier: Verifier,
) -> list[OutcomeResponse]:
    """Get outcomes for a learner."""
    verifier.verify_learner(user, learner_id)
    learner = graph.get_learner(learner_id)
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    outcomes = graph.get_outcomes_by_learner(learner_id)
    return [
        OutcomeResponse(
            id=o.id,
            learner_id=o.learner_id,
            description=o.stated_goal,
            status=o.status.value,
            created_at=o.created_at,
            achieved_at=o.achieved_at,
        )
        for o in outcomes
    ]


@router.get("/{learner_id}/proofs", response_model=list[ProofResponse])
def get_learner_proofs(
    learner_id: str,
    user: User,
    graph: Graph,
    verifier: Verifier,
) -> list[ProofResponse]:
    """Get proofs for a learner."""
    verifier.verify_learner(user, learner_id)
    learner = graph.get_learner(learner_id)
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    proofs = graph.get_proofs_by_learner(learner_id)
    return [
        ProofResponse(
            id=p.id,
            concept_id=p.concept_id,
            learner_id=p.learner_id,
            demonstration_type=p.demonstration_type.value,
            confidence=p.confidence,
            earned_at=p.earned_at,
        )
        for p in proofs
    ]


@router.get("/{learner_id}/graph", response_model=GraphResponse)
def get_learner_graph(
    learner_id: str,
    user: User,
    graph: Graph,
    verifier: Verifier,
) -> GraphResponse:
    """Get knowledge graph data for visualization."""
    verifier.verify_learner(user, learner_id)
    learner = graph.get_learner(learner_id)
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    nodes = []
    edges_list = []

    # Add learner node
    nodes.append(
        GraphNodeResponse(
            id=learner.id,
            type="learner",
            label=learner.profile.name or "Anonymous",
            data={"skill_level": learner.profile.skill_level.value if learner.profile.skill_level else "beginner"},
        )
    )

    # Add outcome nodes
    outcomes = graph.get_outcomes_by_learner(learner_id)
    for o in outcomes:
        nodes.append(
            GraphNodeResponse(
                id=o.id,
                type="outcome",
                label=o.stated_goal[:50],
                data={"status": o.status.value},
            )
        )

    # Add concept nodes
    concepts = graph.get_concepts_by_learner(learner_id)
    for c in concepts:
        nodes.append(
            GraphNodeResponse(
                id=c.id,
                type="concept",
                label=c.display_name,
                data={"status": c.status.value},
            )
        )

    # Add proof nodes
    proofs = graph.get_proofs_by_learner(learner_id)
    for p in proofs:
        nodes.append(
            GraphNodeResponse(
                id=p.id,
                type="proof",
                label=f"Proof ({p.demonstration_type.value})",
                data={"confidence": p.confidence},
            )
        )

    # Get all edges for learner's items
    all_ids = [n.id for n in nodes]
    for node_id in all_ids:
        edges = graph.get_edges_from(node_id)
        for e in edges:
            if e.to_id in all_ids:
                edges_list.append(
                    GraphEdgeResponse(
                        id=e.id,
                        from_id=e.from_id,
                        to_id=e.to_id,
                        edge_type=e.edge_type.value if hasattr(e.edge_type, 'value') else str(e.edge_type),
                    )
                )

    return GraphResponse(nodes=nodes, edges=edges_list)
