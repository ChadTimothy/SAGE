"""State persistence after each turn.

This module handles persisting changes from SAGEResponse back to the database
after each conversation turn.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sage.graph.learning_graph import LearningGraph
from sage.graph.models import (
    ApplicationEvent,
    ApplicationStatus,
    Concept,
    ConceptStatus,
    DemoType,
    DialogueMode,
    Edge,
    EdgeType,
    Message,
    OutcomeStatus,
    Proof,
    ProofExchange,
    Session,
    SessionContext,
)


@dataclass
class GapIdentified:
    """A gap identified during probing."""

    name: str
    display_name: str
    description: str
    blocking_outcome_id: Optional[str] = None


@dataclass
class ProofEarned:
    """A proof earned during verification."""

    concept_id: str
    demonstration_type: str  # explanation, application, both
    evidence: str
    confidence: float
    prompt: str
    response: str
    analysis: str


@dataclass
class ConnectionDiscovered:
    """A connection discovered between concepts."""

    from_concept_id: str
    to_concept_id: str
    relationship: str
    strength: float
    used_in_teaching: bool = False


@dataclass
class ApplicationDetected:
    """An upcoming application detected in conversation."""

    context: str  # "pricing call tomorrow"
    concept_ids: list[str]
    planned_date: Optional[datetime] = None
    stakes: Optional[str] = None


@dataclass
class FollowupResponse:
    """Response from a follow-up conversation."""

    event_id: str
    outcome_result: str  # went_well, struggled, mixed
    what_worked: Optional[str] = None
    what_struggled: Optional[str] = None
    gaps_revealed: Optional[list[str]] = None
    insights: Optional[str] = None


@dataclass
class StateChange:
    """A detected change in learner state."""

    what_changed: str  # energy_drop, time_pressure, confusion, etc.
    detected_from: str
    recommended_adaptation: str


@dataclass
class TurnChanges:
    """All changes from a single turn to persist."""

    # Messages
    user_message: str
    sage_message: str
    sage_mode: DialogueMode

    # Mode transition
    transition_to: Optional[DialogueMode] = None
    transition_reason: Optional[str] = None

    # State updates
    gap_identified: Optional[GapIdentified] = None
    proof_earned: Optional[ProofEarned] = None
    connection_discovered: Optional[ConnectionDiscovered] = None

    # Application tracking
    application_detected: Optional[ApplicationDetected] = None
    followup_response: Optional[FollowupResponse] = None

    # Context updates
    state_change_detected: Optional[StateChange] = None
    context_update: Optional[SessionContext] = None

    # Outcome
    outcome_achieved: bool = False
    outcome_reasoning: Optional[str] = None

    # Learning
    teaching_approach_used: Optional[str] = None


class TurnPersistence:
    """Persists turn changes to the database."""

    def __init__(self, graph: LearningGraph):
        """Initialize with a LearningGraph instance."""
        self.graph = graph

    def persist(
        self,
        session: Session,
        changes: TurnChanges,
    ) -> Session:
        """Persist all changes from a turn.

        Note: gap_identified, proof_earned, and connection_discovered are now
        handled by GapFinder and ProofHandler in ConversationEngine._persist_turn().
        This method only handles messages, applications, follow-ups, context, and outcomes.

        Args:
            session: The current session
            changes: All changes to persist

        Returns:
            Updated session
        """
        # ALWAYS: Record messages
        session = self._add_messages(session, changes)

        # NOTE: gap_identified, proof_earned, and connection_discovered
        # are handled by GapFinder and ProofHandler in ConversationEngine

        # Handle application detected -> create event
        if changes.application_detected:
            self._handle_application_detected(session, changes.application_detected)

        # Handle followup response -> update event
        if changes.followup_response:
            self._handle_followup_response(session, changes.followup_response)

        # Handle state change -> update context
        if changes.state_change_detected and changes.context_update:
            session.context = changes.context_update

        # Handle outcome achieved
        if changes.outcome_achieved:
            self._handle_outcome_achieved(session)

        # Save the session
        self.graph.update_session(session)

        return session

    def _add_messages(self, session: Session, changes: TurnChanges) -> Session:
        """Add user and SAGE messages to session."""
        # User message
        session.messages.append(
            Message(
                role="user",
                content=changes.user_message,
                timestamp=datetime.utcnow(),
            )
        )

        # SAGE message
        session.messages.append(
            Message(
                role="sage",
                content=changes.sage_message,
                timestamp=datetime.utcnow(),
                mode=changes.sage_mode.value,
            )
        )

        return session

    def _handle_gap_identified(
        self,
        session: Session,
        gap: GapIdentified,
    ) -> Concept:
        """Create concept from identified gap."""
        concept = Concept(
            learner_id=session.learner_id,
            name=gap.name,
            display_name=gap.display_name,
            description=gap.description,
            discovered_from=gap.blocking_outcome_id,
            status=ConceptStatus.IDENTIFIED,
        )

        concept = self.graph.create_concept_obj(concept)

        # Link to outcome if specified
        if gap.blocking_outcome_id:
            edge = Edge(
                from_id=gap.blocking_outcome_id,
                from_type="outcome",
                to_id=concept.id,
                to_type="concept",
                edge_type=EdgeType.REQUIRES,
            )
            self.graph.create_edge(edge)

        # Track in session
        if concept.id not in session.concepts_explored:
            session.concepts_explored.append(concept.id)

        return concept

    def _handle_proof_earned(
        self,
        session: Session,
        proof_data: ProofEarned,
    ) -> Proof:
        """Create proof and update concept status."""
        proof = Proof(
            learner_id=session.learner_id,
            concept_id=proof_data.concept_id,
            session_id=session.id,
            demonstration_type=DemoType(proof_data.demonstration_type),
            evidence=proof_data.evidence,
            confidence=proof_data.confidence,
            exchange=ProofExchange(
                prompt=proof_data.prompt,
                response=proof_data.response,
                analysis=proof_data.analysis,
            ),
        )

        proof = self.graph.create_proof_obj(proof)

        # Update concept status
        concept = self.graph.get_concept(proof_data.concept_id)
        if concept:
            concept.status = ConceptStatus.UNDERSTOOD
            concept.understood_at = datetime.utcnow()
            self.graph.update_concept(concept)

        # Create demonstrated_by edge
        edge = Edge(
            from_id=proof_data.concept_id,
            from_type="concept",
            to_id=proof.id,
            to_type="proof",
            edge_type=EdgeType.DEMONSTRATED_BY,
        )
        self.graph.create_edge(edge)

        # Update learner proof count
        learner = self.graph.get_learner(session.learner_id)
        if learner:
            learner.total_proofs += 1
            self.graph.update_learner(learner)

        # Track in session
        session.proofs_earned.append(proof.id)

        return proof

    def _handle_connection_discovered(
        self,
        session: Session,
        connection: ConnectionDiscovered,
    ) -> Edge:
        """Create relates_to edge for discovered connection."""
        edge = Edge(
            from_id=connection.from_concept_id,
            from_type="concept",
            to_id=connection.to_concept_id,
            to_type="concept",
            edge_type=EdgeType.RELATES_TO,
            metadata={
                "relationship": connection.relationship,
                "strength": connection.strength,
                "discovered_in": session.id,
                "used_in_teaching": connection.used_in_teaching,
            },
        )

        edge = self.graph.create_edge(edge)

        # Track in session
        session.connections_found.append(edge.id)

        return edge

    def _handle_application_detected(
        self,
        session: Session,
        app: ApplicationDetected,
    ) -> ApplicationEvent:
        """Create application event from detected application."""
        event = ApplicationEvent(
            learner_id=session.learner_id,
            concept_ids=app.concept_ids,
            outcome_id=session.outcome_id,
            session_id=session.id,
            context=app.context,
            planned_date=app.planned_date.date() if app.planned_date else None,
            stakes=app.stakes,
            status=ApplicationStatus.UPCOMING,
        )

        event = self.graph.create_application_event_obj(event)

        # Create applied_in edges for each concept
        for concept_id in app.concept_ids:
            edge = Edge(
                from_id=concept_id,
                from_type="concept",
                to_id=event.id,
                to_type="application_event",
                edge_type=EdgeType.APPLIED_IN,
            )
            self.graph.create_edge(edge)

        return event

    def _handle_followup_response(
        self,
        session: Session,
        response: FollowupResponse,
    ) -> ApplicationEvent:
        """Update application event with followup response."""
        event = self.graph.get_application_event(response.event_id)
        if not event:
            raise ValueError(f"Application event not found: {response.event_id}")

        # Update the event
        event.status = ApplicationStatus.COMPLETED
        event.followup_session_id = session.id
        event.followed_up_at = datetime.utcnow()
        event.outcome_result = response.outcome_result
        event.what_worked = response.what_worked
        event.what_struggled = response.what_struggled
        event.gaps_revealed = response.gaps_revealed
        event.insights = response.insights

        event = self.graph.update_application_event(event)

        # If gaps were revealed, create concepts for them
        if response.gaps_revealed:
            for gap_name in response.gaps_revealed:
                gap = GapIdentified(
                    name=gap_name.lower().replace(" ", "-"),
                    display_name=gap_name,
                    description=f"Gap revealed during {event.context}",
                    blocking_outcome_id=event.outcome_id,
                )
                concept = self._handle_gap_identified(session, gap)

                # Link to the application event
                edge = Edge(
                    from_id=concept.id,
                    from_type="concept",
                    to_id=event.id,
                    to_type="application_event",
                    edge_type=EdgeType.APPLIED_IN,
                    metadata={"revealed_by_struggle": True},
                )
                self.graph.create_edge(edge)

        return event

    def _handle_outcome_achieved(self, session: Session) -> None:
        """Mark outcome as achieved."""
        if not session.outcome_id:
            return

        outcome = self.graph.get_outcome(session.outcome_id)
        if not outcome:
            return

        outcome.status = OutcomeStatus.ACHIEVED
        outcome.achieved_at = datetime.utcnow()
        self.graph.update_outcome(outcome)

        # Clear active outcome from learner
        learner = self.graph.get_learner(session.learner_id)
        if learner:
            learner.active_outcome_id = None
            self.graph.update_learner(learner)


def persist_turn(
    graph: LearningGraph,
    session: Session,
    changes: TurnChanges,
) -> Session:
    """Convenience function to persist turn changes.

    Args:
        graph: The LearningGraph instance
        session: The current session
        changes: All changes to persist

    Returns:
        Updated session
    """
    persistence = TurnPersistence(graph)
    return persistence.persist(session, changes)
