"""LearningGraph - High-level interface for the SAGE learning graph.

Provides a clean API for all graph operations, wrapping the lower-level
store and query classes.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import (
    ApplicationEvent,
    ApplicationStatus,
    Concept,
    ConceptStatus,
    DemoType,
    Edge,
    EdgeType,
    Learner,
    LearnerProfile,
    Message,
    Outcome,
    OutcomeStatus,
    Proof,
    ProofExchange,
    Session,
    SessionContext,
    SessionEndingState,
    gen_id,
)
from .queries import GraphQueries, LearnerState, PastApplication, RelatedConcept
from .store import GraphStore


class LearningGraph:
    """High-level interface for the SAGE learning graph.

    This is the main class for interacting with the learning graph.
    It provides clean methods for all graph operations.

    Example:
        graph = LearningGraph("./data/sage.db")
        learner = graph.get_or_create_learner()
        outcome = graph.create_outcome(learner.id, "Learn to price services")
        session = graph.start_session(learner.id, outcome.id)
    """

    def __init__(self, db_path: str | Path = ":memory:"):
        """Initialize the learning graph.

        Args:
            db_path: Path to SQLite database, or ":memory:" for in-memory.
        """
        self._store = GraphStore(db_path)
        self._queries = GraphQueries(self._store)

    @property
    def store(self) -> GraphStore:
        """Access the underlying graph store."""
        return self._store

    # =========================================================================
    # Learner Operations
    # =========================================================================

    def get_or_create_learner(
        self,
        learner_id: Optional[str] = None,
        profile: Optional[LearnerProfile] = None,
    ) -> Learner:
        """Get an existing learner or create a new one.

        Args:
            learner_id: Optional ID to look up. If None, creates new learner.
            profile: Optional profile for new learner.

        Returns:
            The learner (existing or newly created).
        """
        if learner_id:
            learner = self._store.get_learner(learner_id)
            if learner:
                return learner

        # Create new learner
        learner = Learner(
            id=learner_id or gen_id(),
            profile=profile or LearnerProfile(),
        )
        self._store.create_learner(learner)
        return learner

    def get_learner(self, learner_id: str) -> Optional[Learner]:
        """Get a learner by ID."""
        return self._store.get_learner(learner_id)

    def update_learner(self, learner: Learner) -> None:
        """Update an existing learner."""
        self._store.update_learner(learner)

    def get_learner_state(self, learner_id: str) -> Optional[LearnerState]:
        """Get complete learner state for session continuity.

        Returns everything needed to resume a learning session.
        """
        return self._queries.get_learner_state(learner_id)

    # =========================================================================
    # Outcome Operations
    # =========================================================================

    def create_outcome(
        self,
        learner_id: str,
        stated_goal: str,
        motivation: Optional[str] = None,
        set_active: bool = True,
    ) -> Outcome:
        """Create a new outcome (goal) for a learner.

        Args:
            learner_id: The learner pursuing this goal.
            stated_goal: What they said they want to do.
            motivation: Why they want this (optional).
            set_active: If True, sets this as the learner's active outcome.

        Returns:
            The created outcome.
        """
        outcome = Outcome(
            learner_id=learner_id,
            stated_goal=stated_goal,
            motivation=motivation,
        )
        self._store.create_outcome(outcome)

        if set_active:
            learner = self._store.get_learner(learner_id)
            if learner:
                learner.active_outcome_id = outcome.id
                self._store.update_learner(learner)

        return outcome

    def get_outcome(self, outcome_id: str) -> Optional[Outcome]:
        """Get an outcome by ID."""
        return self._store.get_outcome(outcome_id)

    def get_active_outcome(self, learner_id: str) -> Optional[Outcome]:
        """Get the learner's currently active outcome."""
        learner = self._store.get_learner(learner_id)
        if learner and learner.active_outcome_id:
            return self._store.get_outcome(learner.active_outcome_id)
        return None

    def update_outcome(self, outcome: Outcome) -> None:
        """Update an existing outcome."""
        self._store.update_outcome(outcome)

    def mark_achieved(self, outcome_id: str) -> None:
        """Mark an outcome as achieved."""
        outcome = self._store.get_outcome(outcome_id)
        if outcome:
            outcome.status = OutcomeStatus.ACHIEVED
            outcome.achieved_at = datetime.utcnow()
            self._store.update_outcome(outcome)

    def get_outcome_progress(self, outcome_id: str) -> dict:
        """Get progress on an outcome including concepts and proofs."""
        return self._queries.get_outcome_progress(outcome_id)

    # =========================================================================
    # Concept Operations
    # =========================================================================

    def create_concept(
        self,
        learner_id: str,
        name: str,
        display_name: str,
        discovered_from: str,
        description: Optional[str] = None,
    ) -> Concept:
        """Create a new concept (gap discovered).

        Args:
            learner_id: The learner this concept is for.
            name: Machine-readable name (e.g., "value-articulation").
            display_name: Human-readable name (e.g., "Value Articulation").
            discovered_from: The outcome_id where this gap was found.
            description: Optional description of what the concept covers.

        Returns:
            The created concept.
        """
        concept = Concept(
            learner_id=learner_id,
            name=name,
            display_name=display_name,
            discovered_from=discovered_from,
            description=description,
        )
        self._store.create_concept(concept)

        # Create requires edge from outcome to concept
        edge = Edge(
            from_id=discovered_from,
            from_type="outcome",
            to_id=concept.id,
            to_type="concept",
            edge_type=EdgeType.REQUIRES,
        )
        self._store.create_edge(edge)

        return concept

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Get a concept by ID."""
        return self._store.get_concept(concept_id)

    def get_concepts_for_outcome(self, outcome_id: str) -> list[Concept]:
        """Get all concepts discovered for an outcome."""
        return self._store.get_concepts_by_outcome(outcome_id)

    def update_concept(self, concept: Concept) -> None:
        """Update an existing concept."""
        self._store.update_concept(concept)

    def mark_concept_teaching(self, concept_id: str) -> None:
        """Mark a concept as currently being taught."""
        concept = self._store.get_concept(concept_id)
        if concept:
            concept.status = ConceptStatus.TEACHING
            self._store.update_concept(concept)

    def mark_concept_understood(self, concept_id: str) -> None:
        """Mark a concept as understood."""
        concept = self._store.get_concept(concept_id)
        if concept:
            concept.status = ConceptStatus.UNDERSTOOD
            concept.understood_at = datetime.utcnow()
            self._store.update_concept(concept)

    # =========================================================================
    # Proof Operations
    # =========================================================================

    def create_proof(
        self,
        learner_id: str,
        concept_id: str,
        session_id: str,
        demonstration_type: DemoType,
        evidence: str,
        exchange: ProofExchange,
        confidence: float = 0.8,
    ) -> Proof:
        """Create a proof (verified understanding).

        Args:
            learner_id: The learner who earned this proof.
            concept_id: The concept that was proven.
            session_id: The session where the proof was earned.
            demonstration_type: How they demonstrated understanding.
            evidence: Summary of the demonstration.
            exchange: The prompt/response/analysis exchange.
            confidence: Confidence score (0.0-1.0).

        Returns:
            The created proof.
        """
        proof = Proof(
            learner_id=learner_id,
            concept_id=concept_id,
            session_id=session_id,
            demonstration_type=demonstration_type,
            evidence=evidence,
            exchange=exchange,
            confidence=confidence,
        )
        self._store.create_proof(proof)

        # Create demonstrated_by edge
        edge = Edge(
            from_id=concept_id,
            from_type="concept",
            to_id=proof.id,
            to_type="proof",
            edge_type=EdgeType.DEMONSTRATED_BY,
        )
        self._store.create_edge(edge)

        # Mark concept as understood
        self.mark_concept_understood(concept_id)

        # Update learner stats
        learner = self._store.get_learner(learner_id)
        if learner:
            learner.total_proofs += 1
            self._store.update_learner(learner)

        return proof

    def get_proven_concepts(self, learner_id: str) -> list[tuple[Concept, Proof]]:
        """Get all concepts the learner has proven with their proofs."""
        return self._queries.get_proven_concepts(learner_id)

    def has_proof(self, concept_id: str) -> bool:
        """Check if a concept has any proofs."""
        return bool(self._store.get_proofs_by_concept(concept_id))

    def get_proofs_by_concept(self, concept_id: str) -> list[Proof]:
        """Get all proofs for a specific concept."""
        return self._store.get_proofs_by_concept(concept_id)

    # =========================================================================
    # Session Operations
    # =========================================================================

    def start_session(
        self,
        learner_id: str,
        outcome_id: Optional[str] = None,
        context: Optional[SessionContext] = None,
    ) -> Session:
        """Start a new learning session.

        Args:
            learner_id: The learner for this session.
            outcome_id: Optional outcome being worked on.
            context: Optional session context (Set/Setting/Intention).

        Returns:
            The created session.
        """
        session = Session(
            learner_id=learner_id,
            outcome_id=outcome_id,
            context=context,
        )
        self._store.create_session(session)

        # Update learner stats
        learner = self._store.get_learner(learner_id)
        if learner:
            learner.total_sessions += 1
            learner.last_session_at = session.started_at
            self._store.update_learner(learner)

        return session

    def end_session(
        self,
        session: Session,
        summary: Optional[str] = None,
        ending_state: Optional[SessionEndingState] = None,
    ) -> None:
        """End a learning session.

        Args:
            session: The session to end.
            summary: Optional summary of what happened.
            ending_state: Optional state for continuity.
        """
        session.ended_at = datetime.utcnow()
        session.summary = summary
        session.ending_state = ending_state
        self._store.update_session(session)

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return self._store.get_session(session_id)

    def get_last_session(self, learner_id: str) -> Optional[Session]:
        """Get the most recent session for a learner."""
        return self._store.get_last_session(learner_id)

    def add_message(self, session: Session, message: Message) -> None:
        """Add a message to a session."""
        session.messages.append(message)
        self._store.update_session(session)

    def get_learning_history(self, learner_id: str, limit: int = 10) -> list[dict]:
        """Get recent learning history with sessions and achievements."""
        return self._queries.get_learning_history(learner_id, limit)

    # =========================================================================
    # Edge Operations
    # =========================================================================

    def add_concept_relation(
        self,
        from_concept_id: str,
        to_concept_id: str,
        relationship: str,
        strength: float,
        session_id: str,
    ) -> Edge:
        """Add a relates_to edge between concepts.

        Args:
            from_concept_id: Source concept ID.
            to_concept_id: Target concept ID.
            relationship: How they connect.
            strength: Connection strength (0.0-1.0).
            session_id: Session where discovered.

        Returns:
            The created edge.
        """
        edge = Edge(
            from_id=from_concept_id,
            from_type="concept",
            to_id=to_concept_id,
            to_type="concept",
            edge_type=EdgeType.RELATES_TO,
            metadata={
                "relationship": relationship,
                "strength": strength,
                "discovered_in": session_id,
            },
        )
        self._store.create_edge(edge)
        return edge

    def find_related_concepts(
        self, concept_id: str, learner_id: str
    ) -> list[RelatedConcept]:
        """Find concepts related to the given concept."""
        return self._queries.find_related_concepts(concept_id, learner_id)

    def find_connections_to_known(
        self, concept_name: str, learner_id: str
    ) -> list[RelatedConcept]:
        """Find connections from a new concept to proven concepts."""
        return self._queries.find_connections_to_known(concept_name, learner_id)

    # =========================================================================
    # Application Event Operations
    # =========================================================================

    def create_application_event(
        self,
        learner_id: str,
        session_id: str,
        concept_ids: list[str],
        context: str,
        planned_date=None,
        stakes: Optional[str] = None,
        outcome_id: Optional[str] = None,
    ) -> ApplicationEvent:
        """Create an application event (planned real-world usage).

        Args:
            learner_id: The learner.
            session_id: Session where mentioned.
            concept_ids: Concepts being applied.
            context: Description (e.g., "pricing call tomorrow").
            planned_date: When they'll apply it.
            stakes: How important ("high", "medium", "low").
            outcome_id: Related outcome if any.

        Returns:
            The created application event.
        """
        event = ApplicationEvent(
            learner_id=learner_id,
            session_id=session_id,
            concept_ids=concept_ids,
            context=context,
            planned_date=planned_date,
            stakes=stakes,
            outcome_id=outcome_id,
        )
        self._store.create_application_event(event)

        # Create applied_in edges
        for concept_id in concept_ids:
            edge = Edge(
                from_id=concept_id,
                from_type="concept",
                to_id=event.id,
                to_type="application_event",
                edge_type=EdgeType.APPLIED_IN,
            )
            self._store.create_edge(edge)

        return event

    def get_pending_followups(self, learner_id: str) -> list[ApplicationEvent]:
        """Get application events that need follow-up."""
        return self._store.get_pending_followups(learner_id)

    def record_followup(
        self,
        event_id: str,
        session_id: str,
        outcome_result: str,
        what_worked: Optional[str] = None,
        what_struggled: Optional[str] = None,
        gaps_revealed: Optional[list[str]] = None,
        insights: Optional[str] = None,
    ) -> ApplicationEvent:
        """Record follow-up for an application event.

        Args:
            event_id: The application event ID.
            session_id: Session where follow-up happened.
            outcome_result: How it went ("went well", "struggled", "mixed").
            what_worked: What they did well.
            what_struggled: Where they had trouble.
            gaps_revealed: New gaps discovered.
            insights: Their reflection.

        Returns:
            The updated application event.
        """
        event = self._store.get_application_event(event_id)
        if event:
            event.status = ApplicationStatus.COMPLETED
            event.followup_session_id = session_id
            event.followed_up_at = datetime.utcnow()
            event.outcome_result = outcome_result
            event.what_worked = what_worked
            event.what_struggled = what_struggled
            event.gaps_revealed = gaps_revealed
            event.insights = insights
            self._store.update_application_event(event)
        return event

    def get_applications_for_concept(
        self, concept_id: str, learner_id: str
    ) -> list[PastApplication]:
        """Get past applications of a concept for teaching context."""
        return self._queries.get_applications_for_concept(concept_id, learner_id)

    # =========================================================================
    # Direct Object Methods (for context module)
    # =========================================================================

    def create_learner(self, learner: Learner) -> Learner:
        """Create a learner from a full Learner object."""
        self._store.create_learner(learner)
        return learner

    def create_outcome_obj(self, outcome: Outcome) -> Outcome:
        """Create an outcome from a full Outcome object."""
        self._store.create_outcome(outcome)
        return outcome

    def create_concept_obj(self, concept: Concept) -> Concept:
        """Create a concept from a full Concept object."""
        self._store.create_concept(concept)
        return concept

    def create_proof_obj(self, proof: Proof) -> Proof:
        """Create a proof from a full Proof object."""
        self._store.create_proof(proof)
        return proof

    def get_proof(self, proof_id: str) -> Optional[Proof]:
        """Get a proof by ID."""
        return self._store.get_proof(proof_id)

    def create_session(self, session: Session) -> Session:
        """Create a session from a full Session object."""
        self._store.create_session(session)
        return session

    def update_session(self, session: Session) -> None:
        """Update an existing session."""
        self._store.update_session(session)

    def get_sessions_by_learner(self, learner_id: str) -> list[Session]:
        """Get all sessions for a learner."""
        return self._store.get_sessions_by_learner(learner_id)

    def create_application_event_obj(self, event: ApplicationEvent) -> ApplicationEvent:
        """Create an application event from a full object."""
        self._store.create_application_event(event)
        return event

    def get_application_event(self, event_id: str) -> Optional[ApplicationEvent]:
        """Get an application event by ID."""
        return self._store.get_application_event(event_id)

    def get_application_events_by_learner(self, learner_id: str) -> list[ApplicationEvent]:
        """Get all application events for a learner."""
        return self._store.get_application_events_by_learner(learner_id)

    def update_application_event(self, event: ApplicationEvent) -> ApplicationEvent:
        """Update an existing application event."""
        self._store.update_application_event(event)
        return event

    def get_concepts_by_learner(self, learner_id: str) -> list[Concept]:
        """Get all concepts for a learner."""
        return self._store.get_concepts_by_learner(learner_id)

    def get_proofs_by_learner(self, learner_id: str) -> list[Proof]:
        """Get all proofs for a learner."""
        return self._store.get_proofs_by_learner(learner_id)

    def get_edges_from(self, from_id: str, edge_type: Optional[EdgeType] = None) -> list[Edge]:
        """Get all edges from a node."""
        return self._store.get_edges_from(from_id, edge_type.value if edge_type else None)

    def get_edges_to(self, to_id: str, edge_type: Optional[EdgeType] = None) -> list[Edge]:
        """Get all edges to a node."""
        return self._store.get_edges_to(to_id, edge_type.value if edge_type else None)

    def create_edge(self, edge: Edge) -> Edge:
        """Create an edge from a full Edge object."""
        self._store.create_edge(edge)
        return edge

    def update_edge(self, edge: Edge) -> Edge:
        """Update an existing edge."""
        self._store.update_edge(edge)
        return edge
