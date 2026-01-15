"""SQLite store for SAGE Learning Graph.

Provides persistent storage for all graph nodes and edges with JSON field support.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Optional, TypeVar

from pydantic import BaseModel

from .models import (
    ApplicationEvent,
    ApplicationStatus,
    Concept,
    ConceptStatus,
    DemoType,
    Edge,
    EdgeType,
    Learner,
    LearnerInsights,
    LearnerPreferences,
    LearnerProfile,
    Message,
    Outcome,
    OutcomeStatus,
    PracticeFeedback,
    PracticeScenario,
    Proof,
    ProofExchange,
    Session,
    SessionContext,
    SessionEndingState,
    SessionType,
)

T = TypeVar("T", bound=BaseModel)


# =============================================================================
# Schema Definition
# =============================================================================

SCHEMA = """
-- Learners table
CREATE TABLE IF NOT EXISTS learners (
    id TEXT PRIMARY KEY,
    profile JSON,
    preferences JSON,
    insights JSON,
    active_outcome_id TEXT,
    current_focus TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_session_at DATETIME,
    total_sessions INTEGER DEFAULT 0,
    total_proofs INTEGER DEFAULT 0
);

-- Outcomes table
CREATE TABLE IF NOT EXISTS outcomes (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    stated_goal TEXT NOT NULL,
    clarified_goal TEXT,
    motivation TEXT,
    success_criteria TEXT,
    status TEXT DEFAULT 'active',
    territory JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    achieved_at DATETIME,
    last_worked_on DATETIME,
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);

-- Concepts table
CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    discovered_from TEXT,
    status TEXT DEFAULT 'identified',
    summary TEXT,
    times_discussed INTEGER DEFAULT 0,
    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    understood_at DATETIME,
    FOREIGN KEY (learner_id) REFERENCES learners(id),
    FOREIGN KEY (discovered_from) REFERENCES outcomes(id)
);

-- Proofs table
CREATE TABLE IF NOT EXISTS proofs (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    demonstration_type TEXT,
    evidence TEXT,
    confidence REAL,
    exchange JSON,
    earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (learner_id) REFERENCES learners(id),
    FOREIGN KEY (concept_id) REFERENCES concepts(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    outcome_id TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    context JSON,
    messages JSON,
    summary TEXT,
    concepts_explored JSON,
    proofs_earned JSON,
    connections_found JSON,
    ending_state JSON,
    session_type TEXT DEFAULT 'learning',
    practice_scenario JSON,
    practice_feedback JSON,
    FOREIGN KEY (learner_id) REFERENCES learners(id),
    FOREIGN KEY (outcome_id) REFERENCES outcomes(id)
);

-- Application events table
CREATE TABLE IF NOT EXISTS application_events (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    concept_ids JSON NOT NULL,
    outcome_id TEXT,
    session_id TEXT NOT NULL,
    context TEXT NOT NULL,
    planned_date DATE,
    stakes TEXT,
    status TEXT DEFAULT 'upcoming',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    followup_session_id TEXT,
    followed_up_at DATETIME,
    outcome_result TEXT,
    what_worked TEXT,
    what_struggled TEXT,
    gaps_revealed JSON,
    insights TEXT,
    FOREIGN KEY (learner_id) REFERENCES learners(id),
    FOREIGN KEY (outcome_id) REFERENCES outcomes(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Edges table
CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    from_id TEXT NOT NULL,
    from_type TEXT NOT NULL,
    to_id TEXT NOT NULL,
    to_type TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_outcomes_learner ON outcomes(learner_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_status ON outcomes(status);
CREATE INDEX IF NOT EXISTS idx_concepts_learner ON concepts(learner_id);
CREATE INDEX IF NOT EXISTS idx_concepts_outcome ON concepts(discovered_from);
CREATE INDEX IF NOT EXISTS idx_proofs_learner ON proofs(learner_id);
CREATE INDEX IF NOT EXISTS idx_proofs_concept ON proofs(concept_id);
CREATE INDEX IF NOT EXISTS idx_sessions_learner ON sessions(learner_id);
CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id, from_type);
CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id, to_type);
CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type);
CREATE INDEX IF NOT EXISTS idx_applications_learner ON application_events(learner_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON application_events(status);
CREATE INDEX IF NOT EXISTS idx_applications_followup ON application_events(status, planned_date);
"""


# =============================================================================
# JSON Serialization Helpers
# =============================================================================


def _deserialize_json(value: Optional[str]) -> Optional[dict | list]:
    """Deserialize a JSON string from SQLite."""
    if value is None:
        return None
    return json.loads(value)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse a datetime string from SQLite."""
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _parse_date(value: Optional[str]) -> Optional[date]:
    """Parse a date string from SQLite."""
    if value is None:
        return None
    return date.fromisoformat(value)


# =============================================================================
# GraphStore Class
# =============================================================================


class GraphStore:
    """SQLite-based storage for SAGE Learning Graph."""

    def __init__(self, db_path: str | Path = ":memory:"):
        """Initialize the store.

        Args:
            db_path: Path to SQLite database file, or ":memory:" for in-memory.
        """
        self.db_path = str(db_path)
        self._is_memory = self.db_path == ":memory:"
        self._persistent_conn: Optional[sqlite3.Connection] = None

        # For in-memory DBs, create persistent connection immediately
        if self._is_memory:
            self._persistent_conn = sqlite3.connect(":memory:")
            self._persistent_conn.row_factory = sqlite3.Row

        self._init_db()

    def _init_db(self) -> None:
        """Initialize database with schema."""
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connection(self):
        """Get a database connection with proper cleanup.

        For in-memory databases, returns the persistent connection.
        For file-based databases, creates a new connection each time.
        """
        if self._is_memory:
            # In-memory: use persistent connection, don't close it
            yield self._persistent_conn
            self._persistent_conn.commit()
        else:
            # File-based: create new connection each time
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # =========================================================================
    # Learner Operations
    # =========================================================================

    def create_learner(self, learner: Learner) -> Learner:
        """Create a new learner."""
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO learners (
                    id, profile, preferences, insights, active_outcome_id,
                    current_focus, created_at, last_session_at,
                    total_sessions, total_proofs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    learner.id,
                    learner.profile.model_dump_json(),
                    learner.preferences.model_dump_json(),
                    learner.insights.model_dump_json(),
                    learner.active_outcome_id,
                    learner.current_focus,
                    learner.created_at.isoformat(),
                    learner.last_session_at.isoformat() if learner.last_session_at else None,
                    learner.total_sessions,
                    learner.total_proofs,
                ),
            )
        return learner

    def get_learner(self, learner_id: str) -> Optional[Learner]:
        """Get a learner by ID."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM learners WHERE id = ?", (learner_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_learner(row)

    def update_learner(self, learner: Learner) -> None:
        """Update an existing learner."""
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE learners SET
                    profile = ?,
                    preferences = ?,
                    insights = ?,
                    active_outcome_id = ?,
                    current_focus = ?,
                    last_session_at = ?,
                    total_sessions = ?,
                    total_proofs = ?
                WHERE id = ?
                """,
                (
                    learner.profile.model_dump_json(),
                    learner.preferences.model_dump_json(),
                    learner.insights.model_dump_json(),
                    learner.active_outcome_id,
                    learner.current_focus,
                    learner.last_session_at.isoformat() if learner.last_session_at else None,
                    learner.total_sessions,
                    learner.total_proofs,
                    learner.id,
                ),
            )

    def _row_to_learner(self, row: sqlite3.Row) -> Learner:
        """Convert a database row to a Learner model."""
        return Learner(
            id=row["id"],
            profile=LearnerProfile.model_validate_json(row["profile"]),
            preferences=LearnerPreferences.model_validate_json(row["preferences"]),
            insights=LearnerInsights.model_validate_json(row["insights"]),
            active_outcome_id=row["active_outcome_id"],
            current_focus=row["current_focus"],
            created_at=_parse_datetime(row["created_at"]),
            last_session_at=_parse_datetime(row["last_session_at"]),
            total_sessions=row["total_sessions"],
            total_proofs=row["total_proofs"],
        )

    # =========================================================================
    # Outcome Operations
    # =========================================================================

    def create_outcome(self, outcome: Outcome) -> Outcome:
        """Create a new outcome."""
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO outcomes (
                    id, learner_id, stated_goal, clarified_goal, motivation,
                    success_criteria, status, territory, created_at,
                    achieved_at, last_worked_on
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outcome.id,
                    outcome.learner_id,
                    outcome.stated_goal,
                    outcome.clarified_goal,
                    outcome.motivation,
                    outcome.success_criteria,
                    outcome.status.value,
                    json.dumps(outcome.territory) if outcome.territory else None,
                    outcome.created_at.isoformat(),
                    outcome.achieved_at.isoformat() if outcome.achieved_at else None,
                    outcome.last_worked_on.isoformat(),
                ),
            )
        return outcome

    def get_outcome(self, outcome_id: str) -> Optional[Outcome]:
        """Get an outcome by ID."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM outcomes WHERE id = ?", (outcome_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_outcome(row)

    def get_outcomes_by_learner(
        self, learner_id: str, status: Optional[str] = None
    ) -> list[Outcome]:
        """Get all outcomes for a learner, optionally filtered by status."""
        with self.connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM outcomes WHERE learner_id = ? AND status = ? ORDER BY created_at DESC",
                    (learner_id, status),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM outcomes WHERE learner_id = ? ORDER BY created_at DESC",
                    (learner_id,),
                ).fetchall()
            return [self._row_to_outcome(row) for row in rows]

    def update_outcome(self, outcome: Outcome) -> None:
        """Update an existing outcome."""
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE outcomes SET
                    stated_goal = ?,
                    clarified_goal = ?,
                    motivation = ?,
                    success_criteria = ?,
                    status = ?,
                    territory = ?,
                    achieved_at = ?,
                    last_worked_on = ?
                WHERE id = ?
                """,
                (
                    outcome.stated_goal,
                    outcome.clarified_goal,
                    outcome.motivation,
                    outcome.success_criteria,
                    outcome.status.value,
                    json.dumps(outcome.territory) if outcome.territory else None,
                    outcome.achieved_at.isoformat() if outcome.achieved_at else None,
                    outcome.last_worked_on.isoformat(),
                    outcome.id,
                ),
            )

    def _row_to_outcome(self, row: sqlite3.Row) -> Outcome:
        """Convert a database row to an Outcome model."""
        return Outcome(
            id=row["id"],
            learner_id=row["learner_id"],
            stated_goal=row["stated_goal"],
            clarified_goal=row["clarified_goal"],
            motivation=row["motivation"],
            success_criteria=row["success_criteria"],
            status=OutcomeStatus(row["status"]),
            territory=_deserialize_json(row["territory"]),
            created_at=_parse_datetime(row["created_at"]),
            achieved_at=_parse_datetime(row["achieved_at"]),
            last_worked_on=_parse_datetime(row["last_worked_on"]),
        )

    # =========================================================================
    # Concept Operations
    # =========================================================================

    def create_concept(self, concept: Concept) -> Concept:
        """Create a new concept."""
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO concepts (
                    id, learner_id, name, display_name, description,
                    discovered_from, status, summary, times_discussed,
                    discovered_at, understood_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    concept.id,
                    concept.learner_id,
                    concept.name,
                    concept.display_name,
                    concept.description,
                    concept.discovered_from,
                    concept.status.value,
                    concept.summary,
                    concept.times_discussed,
                    concept.discovered_at.isoformat(),
                    concept.understood_at.isoformat() if concept.understood_at else None,
                ),
            )
        return concept

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Get a concept by ID."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM concepts WHERE id = ?", (concept_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_concept(row)

    def get_concepts_by_learner(self, learner_id: str) -> list[Concept]:
        """Get all concepts for a learner."""
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM concepts WHERE learner_id = ? ORDER BY discovered_at DESC",
                (learner_id,),
            ).fetchall()
            return [self._row_to_concept(row) for row in rows]

    def get_concepts_by_outcome(self, outcome_id: str) -> list[Concept]:
        """Get all concepts discovered from an outcome."""
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM concepts WHERE discovered_from = ? ORDER BY discovered_at",
                (outcome_id,),
            ).fetchall()
            return [self._row_to_concept(row) for row in rows]

    def update_concept(self, concept: Concept) -> None:
        """Update an existing concept."""
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE concepts SET
                    name = ?,
                    display_name = ?,
                    description = ?,
                    status = ?,
                    summary = ?,
                    times_discussed = ?,
                    understood_at = ?
                WHERE id = ?
                """,
                (
                    concept.name,
                    concept.display_name,
                    concept.description,
                    concept.status.value,
                    concept.summary,
                    concept.times_discussed,
                    concept.understood_at.isoformat() if concept.understood_at else None,
                    concept.id,
                ),
            )

    def _row_to_concept(self, row: sqlite3.Row) -> Concept:
        """Convert a database row to a Concept model."""
        return Concept(
            id=row["id"],
            learner_id=row["learner_id"],
            name=row["name"],
            display_name=row["display_name"],
            description=row["description"],
            discovered_from=row["discovered_from"],
            status=ConceptStatus(row["status"]),
            summary=row["summary"],
            times_discussed=row["times_discussed"],
            discovered_at=_parse_datetime(row["discovered_at"]),
            understood_at=_parse_datetime(row["understood_at"]),
        )

    # =========================================================================
    # Proof Operations
    # =========================================================================

    def create_proof(self, proof: Proof) -> Proof:
        """Create a new proof."""
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO proofs (
                    id, learner_id, concept_id, session_id,
                    demonstration_type, evidence, confidence, exchange, earned_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proof.id,
                    proof.learner_id,
                    proof.concept_id,
                    proof.session_id,
                    proof.demonstration_type.value,
                    proof.evidence,
                    proof.confidence,
                    proof.exchange.model_dump_json(),
                    proof.earned_at.isoformat(),
                ),
            )
        return proof

    def get_proof(self, proof_id: str) -> Optional[Proof]:
        """Get a proof by ID."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM proofs WHERE id = ?", (proof_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_proof(row)

    def get_proofs_by_learner(self, learner_id: str) -> list[Proof]:
        """Get all proofs for a learner."""
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM proofs WHERE learner_id = ? ORDER BY earned_at DESC",
                (learner_id,),
            ).fetchall()
            return [self._row_to_proof(row) for row in rows]

    def get_proofs_by_concept(self, concept_id: str) -> list[Proof]:
        """Get all proofs for a concept."""
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM proofs WHERE concept_id = ? ORDER BY earned_at DESC",
                (concept_id,),
            ).fetchall()
            return [self._row_to_proof(row) for row in rows]

    def _row_to_proof(self, row: sqlite3.Row) -> Proof:
        """Convert a database row to a Proof model."""
        return Proof(
            id=row["id"],
            learner_id=row["learner_id"],
            concept_id=row["concept_id"],
            session_id=row["session_id"],
            demonstration_type=DemoType(row["demonstration_type"]),
            evidence=row["evidence"],
            confidence=row["confidence"],
            exchange=ProofExchange.model_validate_json(row["exchange"]),
            earned_at=_parse_datetime(row["earned_at"]),
        )

    # =========================================================================
    # Session Operations
    # =========================================================================

    def create_session(self, session: Session) -> Session:
        """Create a new session."""
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    id, learner_id, outcome_id, started_at, ended_at,
                    context, messages, summary, concepts_explored,
                    proofs_earned, connections_found, ending_state,
                    session_type, practice_scenario, practice_feedback
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.learner_id,
                    session.outcome_id,
                    session.started_at.isoformat(),
                    session.ended_at.isoformat() if session.ended_at else None,
                    session.context.model_dump_json() if session.context else None,
                    json.dumps([m.model_dump() for m in session.messages], default=str),
                    session.summary,
                    json.dumps(session.concepts_explored),
                    json.dumps(session.proofs_earned),
                    json.dumps(session.connections_found),
                    session.ending_state.model_dump_json() if session.ending_state else None,
                    session.session_type.value,
                    session.practice_scenario.model_dump_json() if session.practice_scenario else None,
                    session.practice_feedback.model_dump_json() if session.practice_feedback else None,
                ),
            )
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_session(row)

    def get_sessions_by_learner(
        self, learner_id: str, limit: Optional[int] = None
    ) -> list[Session]:
        """Get sessions for a learner, most recent first."""
        with self.connection() as conn:
            query = "SELECT * FROM sessions WHERE learner_id = ? ORDER BY started_at DESC"
            if limit:
                query += f" LIMIT {limit}"
            rows = conn.execute(query, (learner_id,)).fetchall()
            return [self._row_to_session(row) for row in rows]

    def get_last_session(self, learner_id: str) -> Optional[Session]:
        """Get the most recent session for a learner."""
        sessions = self.get_sessions_by_learner(learner_id, limit=1)
        return sessions[0] if sessions else None

    def update_session(self, session: Session) -> None:
        """Update an existing session."""
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE sessions SET
                    ended_at = ?,
                    context = ?,
                    messages = ?,
                    summary = ?,
                    concepts_explored = ?,
                    proofs_earned = ?,
                    connections_found = ?,
                    ending_state = ?,
                    session_type = ?,
                    practice_scenario = ?,
                    practice_feedback = ?
                WHERE id = ?
                """,
                (
                    session.ended_at.isoformat() if session.ended_at else None,
                    session.context.model_dump_json() if session.context else None,
                    json.dumps([m.model_dump() for m in session.messages], default=str),
                    session.summary,
                    json.dumps(session.concepts_explored),
                    json.dumps(session.proofs_earned),
                    json.dumps(session.connections_found),
                    session.ending_state.model_dump_json() if session.ending_state else None,
                    session.session_type.value,
                    session.practice_scenario.model_dump_json() if session.practice_scenario else None,
                    session.practice_feedback.model_dump_json() if session.practice_feedback else None,
                    session.id,
                ),
            )

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        """Convert a database row to a Session model."""
        messages_data = _deserialize_json(row["messages"]) or []
        messages = [Message.model_validate(m) for m in messages_data]

        context = (
            SessionContext.model_validate_json(row["context"])
            if row["context"]
            else None
        )
        ending_state = (
            SessionEndingState.model_validate_json(row["ending_state"])
            if row["ending_state"]
            else None
        )
        practice_scenario = (
            PracticeScenario.model_validate_json(row["practice_scenario"])
            if row["practice_scenario"]
            else None
        )
        practice_feedback = (
            PracticeFeedback.model_validate_json(row["practice_feedback"])
            if row["practice_feedback"]
            else None
        )

        return Session(
            id=row["id"],
            learner_id=row["learner_id"],
            outcome_id=row["outcome_id"],
            started_at=_parse_datetime(row["started_at"]),
            ended_at=_parse_datetime(row["ended_at"]),
            context=context,
            messages=messages,
            summary=row["summary"],
            concepts_explored=_deserialize_json(row["concepts_explored"]) or [],
            proofs_earned=_deserialize_json(row["proofs_earned"]) or [],
            connections_found=_deserialize_json(row["connections_found"]) or [],
            ending_state=ending_state,
            session_type=SessionType(row["session_type"]) if row["session_type"] else SessionType.LEARNING,
            practice_scenario=practice_scenario,
            practice_feedback=practice_feedback,
        )

    # =========================================================================
    # ApplicationEvent Operations
    # =========================================================================

    def create_application_event(self, event: ApplicationEvent) -> ApplicationEvent:
        """Create a new application event."""
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO application_events (
                    id, learner_id, concept_ids, outcome_id, session_id,
                    context, planned_date, stakes, status, created_at,
                    followup_session_id, followed_up_at, outcome_result,
                    what_worked, what_struggled, gaps_revealed, insights
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.learner_id,
                    json.dumps(event.concept_ids),
                    event.outcome_id,
                    event.session_id,
                    event.context,
                    event.planned_date.isoformat() if event.planned_date else None,
                    event.stakes,
                    event.status.value,
                    event.created_at.isoformat(),
                    event.followup_session_id,
                    event.followed_up_at.isoformat() if event.followed_up_at else None,
                    event.outcome_result,
                    event.what_worked,
                    event.what_struggled,
                    json.dumps(event.gaps_revealed) if event.gaps_revealed else None,
                    event.insights,
                ),
            )
        return event

    def get_application_event(self, event_id: str) -> Optional[ApplicationEvent]:
        """Get an application event by ID."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM application_events WHERE id = ?", (event_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_application_event(row)

    def get_pending_followups(self, learner_id: str) -> list[ApplicationEvent]:
        """Get applications that need follow-up."""
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM application_events
                WHERE learner_id = ?
                  AND status IN ('upcoming', 'pending_followup')
                  AND (
                    planned_date <= date('now')
                    OR status = 'pending_followup'
                  )
                ORDER BY planned_date ASC, created_at ASC
                """,
                (learner_id,),
            ).fetchall()
            return [self._row_to_application_event(row) for row in rows]

    def get_application_events_by_learner(self, learner_id: str) -> list[ApplicationEvent]:
        """Get all application events for a learner."""
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM application_events
                WHERE learner_id = ?
                ORDER BY created_at DESC
                """,
                (learner_id,),
            ).fetchall()
            return [self._row_to_application_event(row) for row in rows]

    def update_application_event(self, event: ApplicationEvent) -> None:
        """Update an existing application event."""
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE application_events SET
                    status = ?,
                    followup_session_id = ?,
                    followed_up_at = ?,
                    outcome_result = ?,
                    what_worked = ?,
                    what_struggled = ?,
                    gaps_revealed = ?,
                    insights = ?
                WHERE id = ?
                """,
                (
                    event.status.value,
                    event.followup_session_id,
                    event.followed_up_at.isoformat() if event.followed_up_at else None,
                    event.outcome_result,
                    event.what_worked,
                    event.what_struggled,
                    json.dumps(event.gaps_revealed) if event.gaps_revealed else None,
                    event.insights,
                    event.id,
                ),
            )

    def _row_to_application_event(self, row: sqlite3.Row) -> ApplicationEvent:
        """Convert a database row to an ApplicationEvent model."""
        return ApplicationEvent(
            id=row["id"],
            learner_id=row["learner_id"],
            concept_ids=_deserialize_json(row["concept_ids"]) or [],
            outcome_id=row["outcome_id"],
            session_id=row["session_id"],
            context=row["context"],
            planned_date=_parse_date(row["planned_date"]),
            stakes=row["stakes"],
            status=ApplicationStatus(row["status"]),
            created_at=_parse_datetime(row["created_at"]),
            followup_session_id=row["followup_session_id"],
            followed_up_at=_parse_datetime(row["followed_up_at"]),
            outcome_result=row["outcome_result"],
            what_worked=row["what_worked"],
            what_struggled=row["what_struggled"],
            gaps_revealed=_deserialize_json(row["gaps_revealed"]),
            insights=row["insights"],
        )

    # =========================================================================
    # Edge Operations
    # =========================================================================

    def create_edge(self, edge: Edge) -> Edge:
        """Create a new edge."""
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO edges (
                    id, from_id, from_type, to_id, to_type,
                    edge_type, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge.id,
                    edge.from_id,
                    edge.from_type,
                    edge.to_id,
                    edge.to_type,
                    edge.edge_type.value,
                    json.dumps(edge.metadata),
                    edge.created_at.isoformat(),
                ),
            )
        return edge

    def update_edge(self, edge: Edge) -> Edge:
        """Update an existing edge's metadata."""
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE edges SET metadata = ? WHERE id = ?
                """,
                (json.dumps(edge.metadata), edge.id),
            )
        return edge

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        """Get an edge by ID."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM edges WHERE id = ?", (edge_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_edge(row)

    def get_edges_from(
        self, from_id: str, edge_type: Optional[str] = None
    ) -> list[Edge]:
        """Get all edges from a node."""
        return self._get_edges("from_id", from_id, edge_type)

    def get_edges_to(self, to_id: str, edge_type: Optional[str] = None) -> list[Edge]:
        """Get all edges to a node."""
        return self._get_edges("to_id", to_id, edge_type)

    def _get_edges(
        self, id_column: str, id_value: str, edge_type: Optional[str] = None
    ) -> list[Edge]:
        """Get edges by ID column with optional edge type filter."""
        with self.connection() as conn:
            query = f"SELECT * FROM edges WHERE {id_column} = ?"
            params: tuple = (id_value,)
            if edge_type:
                query += " AND edge_type = ?"
                params = (id_value, edge_type)
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_edge(row) for row in rows]

    def _row_to_edge(self, row: sqlite3.Row) -> Edge:
        """Convert a database row to an Edge model."""
        return Edge(
            id=row["id"],
            from_id=row["from_id"],
            from_type=row["from_type"],
            to_id=row["to_id"],
            to_type=row["to_type"],
            edge_type=EdgeType(row["edge_type"]),
            metadata=_deserialize_json(row["metadata"]) or {},
            created_at=_parse_datetime(row["created_at"]),
        )
