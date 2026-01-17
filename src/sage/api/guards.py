"""Route guards for ownership verification."""

from fastapi import HTTPException, status

from sage.graph.learning_graph import LearningGraph

from .auth import CurrentUser


class OwnershipVerifier:
    """Verify resource ownership for the current user."""

    def __init__(self, graph: LearningGraph):
        self.graph = graph

    def verify_learner(self, user: CurrentUser, learner_id: str) -> None:
        """Verify user owns this learner profile.

        Raises:
            HTTPException: 403 if learner_id doesn't match user's learner_id
        """
        if user.learner_id != learner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: not your learner profile",
            )

    def verify_session(self, user: CurrentUser, session_id: str) -> None:
        """Verify user owns this session.

        Raises:
            HTTPException: 404 if session not found, 403 if not owner
        """
        session = self.graph.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        if session.learner_id != user.learner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: not your session",
            )

    def verify_outcome(self, user: CurrentUser, outcome_id: str) -> None:
        """Verify user owns this outcome.

        Raises:
            HTTPException: 404 if outcome not found, 403 if not owner
        """
        outcome = self.graph.get_outcome(outcome_id)
        if not outcome:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outcome not found",
            )
        if outcome.learner_id != user.learner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: not your outcome",
            )

    def verify_concept(self, user: CurrentUser, concept_id: str) -> None:
        """Verify user owns this concept.

        Raises:
            HTTPException: 404 if concept not found, 403 if not owner
        """
        concept = self.graph.get_concept(concept_id)
        if not concept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Concept not found",
            )
        if concept.learner_id != user.learner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: not your concept",
            )

    def verify_proof(self, user: CurrentUser, proof_id: str) -> None:
        """Verify user owns this proof.

        Raises:
            HTTPException: 404 if proof not found, 403 if not owner
        """
        proof = self.graph.get_proof(proof_id)
        if not proof:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proof not found",
            )
        if proof.learner_id != user.learner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: not your proof",
            )

    def verify_scenario(self, user: CurrentUser, scenario_id: str) -> None:
        """Verify user can access this scenario.

        Preset scenarios are accessible to all authenticated users.
        Custom scenarios are only accessible to their owner.

        Raises:
            HTTPException: 404 if scenario not found, 403 if not accessible
        """
        scenario = self.graph.store.get_scenario(scenario_id)
        if not scenario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scenario not found",
            )
        # Preset scenarios are accessible to all authenticated users
        if scenario.is_preset:
            return
        # Custom scenarios only accessible to owner
        if scenario.learner_id != user.learner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: not your scenario",
            )

    def verify_scenario_owner(self, user: CurrentUser, scenario_id: str) -> None:
        """Verify user owns this scenario (for modifications).

        Preset scenarios cannot be modified by anyone.
        Custom scenarios can only be modified by their owner.

        Raises:
            HTTPException: 404 if not found, 403 if preset or not owner
        """
        scenario = self.graph.store.get_scenario(scenario_id)
        if not scenario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scenario not found",
            )
        if scenario.is_preset:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify preset scenarios",
            )
        if scenario.learner_id != user.learner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: not your scenario",
            )
