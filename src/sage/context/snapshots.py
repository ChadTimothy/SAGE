"""Lightweight snapshot models for token-efficient prompts.

These models are read-only summaries optimized for LLM context.
They contain only the fields needed for prompts, reducing token usage.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from sage.graph.models import (
    ApplicationEvent,
    Concept,
    Edge,
    Learner,
    Outcome,
    Proof,
)


class LearnerSnapshot(BaseModel):
    """Lightweight learner info for prompt context."""

    id: str
    name: Optional[str]
    age_group: Optional[str]
    skill_level: Optional[str]
    context: Optional[str]  # "freelance designer", "PM at a startup"
    total_sessions: int
    total_proofs: int
    active_outcome_id: Optional[str]

    # Preferences (affects content format)
    prefers_examples: bool = True
    prefers_theory_first: bool = False

    @classmethod
    def from_learner(cls, learner: Learner) -> "LearnerSnapshot":
        """Create snapshot from full Learner model."""
        return cls(
            id=learner.id,
            name=learner.profile.name,
            age_group=learner.profile.age_group.value if learner.profile.age_group else None,
            skill_level=learner.profile.skill_level.value if learner.profile.skill_level else None,
            context=learner.profile.context,
            total_sessions=learner.total_sessions,
            total_proofs=learner.total_proofs,
            active_outcome_id=learner.active_outcome_id,
            prefers_examples=learner.insights.prefers_examples,
            prefers_theory_first=learner.insights.prefers_theory_first,
        )


class OutcomeSnapshot(BaseModel):
    """Lightweight outcome info for prompt context."""

    id: str
    stated_goal: str
    clarified_goal: Optional[str]
    motivation: Optional[str]
    success_criteria: Optional[str]
    status: str
    territory: Optional[list[str]]

    @classmethod
    def from_outcome(cls, outcome: Outcome) -> "OutcomeSnapshot":
        """Create snapshot from full Outcome model."""
        return cls(
            id=outcome.id,
            stated_goal=outcome.stated_goal,
            clarified_goal=outcome.clarified_goal,
            motivation=outcome.motivation,
            success_criteria=outcome.success_criteria,
            status=outcome.status.value,
            territory=outcome.territory,
        )


class ConceptSnapshot(BaseModel):
    """Lightweight concept info for prompt context."""

    id: str
    name: str
    display_name: str
    description: Optional[str]
    summary: Optional[str]
    status: str
    has_proof: bool = False
    proof_confidence: Optional[float] = None

    @classmethod
    def from_concept(
        cls,
        concept: Concept,
        proof: Optional[Proof] = None,
    ) -> "ConceptSnapshot":
        """Create snapshot from full Concept model with optional proof."""
        return cls(
            id=concept.id,
            name=concept.name,
            display_name=concept.display_name,
            description=concept.description,
            summary=concept.summary,
            status=concept.status.value,
            has_proof=proof is not None,
            proof_confidence=proof.confidence if proof else None,
        )


class ApplicationSnapshot(BaseModel):
    """Lightweight application event for prompt context."""

    id: str
    context: str  # "pricing call with new client"
    planned_date: Optional[date]
    status: str
    outcome_result: Optional[str]  # went_well, struggled, mixed
    what_worked: Optional[str]
    what_struggled: Optional[str]
    concepts_applied: list[str]  # Display names of concepts

    @classmethod
    def from_application_event(
        cls,
        event: ApplicationEvent,
        concept_names: Optional[dict[str, str]] = None,
    ) -> "ApplicationSnapshot":
        """Create snapshot from full ApplicationEvent model.

        Args:
            event: The application event
            concept_names: Map of concept_id -> display_name
        """
        names = concept_names or {}
        return cls(
            id=event.id,
            context=event.context,
            planned_date=event.planned_date,
            status=event.status.value,
            outcome_result=event.outcome_result,
            what_worked=event.what_worked,
            what_struggled=event.what_struggled,
            concepts_applied=[names.get(cid, cid) for cid in event.concept_ids],
        )


class RelatedConcept(BaseModel):
    """A concept related to the current context."""

    id: str
    name: str
    display_name: str
    summary: Optional[str]
    relationship: str  # How it relates ("builds on", "contrasts with", etc.)
    strength: float  # 0.0-1.0 relevance

    @classmethod
    def from_concept_and_edge(
        cls,
        concept: Concept,
        edge: Edge,
    ) -> "RelatedConcept":
        """Create from concept and its relating edge."""
        metadata = edge.metadata or {}
        return cls(
            id=concept.id,
            name=concept.name,
            display_name=concept.display_name,
            summary=concept.summary,
            relationship=metadata.get("relationship", "relates to"),
            strength=metadata.get("strength", 0.5),
        )


class ProofSnapshot(BaseModel):
    """Lightweight proof info for prompt context."""

    id: str
    concept_id: str
    concept_name: str
    demonstration_type: str
    confidence: float
    evidence: str
    earned_at: datetime

    @classmethod
    def from_proof(
        cls,
        proof: Proof,
        concept_name: str,
    ) -> "ProofSnapshot":
        """Create snapshot from full Proof model."""
        return cls(
            id=proof.id,
            concept_id=proof.concept_id,
            concept_name=concept_name,
            demonstration_type=proof.demonstration_type.value,
            confidence=proof.confidence,
            evidence=proof.evidence,
            earned_at=proof.earned_at,
        )


class OutcomeProgress(BaseModel):
    """Progress toward current goal."""

    outcome_id: str
    stated_goal: str
    clarified_goal: Optional[str]
    concepts_identified: int
    concepts_proven: int
    current_concept: Optional[str]  # Display name if working on one

    @classmethod
    def from_outcome_and_concepts(
        cls,
        outcome: Outcome,
        concepts: list[Concept],
        proofs: list[Proof],
        current_concept: Optional[Concept] = None,
    ) -> "OutcomeProgress":
        """Create progress snapshot from outcome and its concepts."""
        proven_concept_ids = {p.concept_id for p in proofs}
        return cls(
            outcome_id=outcome.id,
            stated_goal=outcome.stated_goal,
            clarified_goal=outcome.clarified_goal,
            concepts_identified=len(concepts),
            concepts_proven=len([c for c in concepts if c.id in proven_concept_ids]),
            current_concept=current_concept.display_name if current_concept else None,
        )
