"""Proof creation and graph updates.

Handles processing ProofEarned from SAGEResponse, creating Proof models,
updating concept status, and maintaining graph integrity.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sage.dialogue.structured_output import ProofEarned
from sage.graph.learning_graph import LearningGraph
from sage.graph.models import (
    Concept,
    ConceptStatus,
    DemoType,
    Edge,
    Proof,
    ProofExchange,
)

from .confidence import ConfidenceScorer, calculate_confidence


logger = logging.getLogger(__name__)


class ProofHandler:
    """Handles proof creation and related graph updates."""

    def __init__(self, graph: LearningGraph):
        self.graph = graph
        self.confidence_scorer = ConfidenceScorer()

    def process_proof_earned(
        self,
        proof_earned: ProofEarned,
        learner_id: str,
        session_id: str,
    ) -> Optional[Proof]:
        """Process a ProofEarned from SAGEResponse."""
        try:
            demo_type = self._parse_demo_type(proof_earned.demonstration_type)
            confidence = proof_earned.confidence or calculate_confidence(demo_type, proof_earned.exchange)

            exchange = ProofExchange(
                prompt=proof_earned.exchange.prompt,
                response=proof_earned.exchange.response,
                analysis=proof_earned.exchange.analysis,
            )

            proof = self.create_proof(
                concept_id=proof_earned.concept_id,
                learner_id=learner_id,
                session_id=session_id,
                demonstration_type=demo_type,
                evidence=proof_earned.evidence,
                confidence=confidence,
                exchange=exchange,
            )

            self.mark_concept_understood(proof_earned.concept_id)
            self.create_demonstrated_by_edge(proof_earned.concept_id, proof.id)
            self.increment_learner_proofs(learner_id)
            logger.info(f"Processed proof for concept {proof_earned.concept_id}: confidence={confidence:.2f}")

            return proof

        except Exception as e:
            logger.error(f"Failed to process proof: {e}")
            return None

    def create_proof(
        self,
        concept_id: str,
        learner_id: str,
        session_id: str,
        demonstration_type: DemoType,
        evidence: str,
        confidence: float,
        exchange: ProofExchange,
    ) -> Proof:
        """Create a new proof in the graph."""
        proof = Proof(
            id=str(uuid4()),
            concept_id=concept_id,
            learner_id=learner_id,
            session_id=session_id,
            demonstration_type=demonstration_type,
            evidence=evidence,
            confidence=confidence,
            exchange=exchange,
            earned_at=datetime.utcnow(),
        )

        created = self.graph.create_proof_obj(proof)
        logger.info(f"Created proof {created.id} for concept {concept_id}")
        return created

    def mark_concept_understood(self, concept_id: str) -> Optional[Concept]:
        """Mark a concept as understood."""
        concept = self.graph.get_concept(concept_id)
        if not concept:
            logger.warning(f"Concept not found: {concept_id}")
            return None

        old_status = concept.status
        concept.status = ConceptStatus.UNDERSTOOD
        concept.understood_at = datetime.utcnow()

        updated = self.graph.update_concept(concept)
        logger.info(f"Updated concept {concept_id} status: {old_status.value} -> {ConceptStatus.UNDERSTOOD.value}")
        return updated

    def create_demonstrated_by_edge(self, concept_id: str, proof_id: str) -> Optional[Edge]:
        """Create a demonstrated_by edge from concept to proof."""
        edge = Edge(
            id=str(uuid4()),
            from_id=concept_id,
            from_type="concept",
            to_id=proof_id,
            to_type="proof",
            edge_type="demonstrated_by",
            metadata={"created_at": datetime.utcnow().isoformat()},
        )

        created = self.graph.create_edge(edge)
        logger.info(f"Created demonstrated_by edge: {concept_id} -> {proof_id}")
        return created

    def increment_learner_proofs(self, learner_id: str) -> None:
        """Increment the learner's total proof count."""
        learner = self.graph.get_learner(learner_id)
        if learner:
            learner.total_proofs += 1
            self.graph.update_learner(learner)
            logger.info(f"Incremented learner {learner_id} proofs to {learner.total_proofs}")

    def _parse_demo_type(self, demo_type_str: str) -> DemoType:
        """Parse demonstration type string to enum."""
        lower = demo_type_str.lower()
        if any(term in lower for term in ["both", "synthesis"]):
            return DemoType.BOTH
        if any(term in lower for term in ["application", "apply"]):
            return DemoType.APPLICATION
        return DemoType.EXPLANATION

    def get_proofs_for_concept(self, concept_id: str) -> list[Proof]:
        """Get all proofs for a concept."""
        return self.graph.get_proofs_by_concept(concept_id)

    def has_proof(self, concept_id: str, learner_id: str) -> bool:
        """Check if a learner has proven a concept."""
        proofs = self.get_proofs_for_concept(concept_id)
        return any(p.learner_id == learner_id for p in proofs)

    def get_latest_proof(self, concept_id: str, learner_id: str) -> Optional[Proof]:
        """Get the most recent proof for a concept."""
        proofs = self.get_proofs_for_concept(concept_id)
        learner_proofs = [p for p in proofs if p.learner_id == learner_id]

        if not learner_proofs:
            return None
        return max(learner_proofs, key=lambda p: p.earned_at)


def create_proof_handler(graph: LearningGraph) -> ProofHandler:
    """Factory function to create a ProofHandler."""
    return ProofHandler(graph)
