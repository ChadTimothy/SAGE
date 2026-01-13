"""Pydantic models for SAGE Learning Graph.

Node Types:
- Learner: The person learning (one per user)
- Outcome: A real-world goal they want to achieve
- Concept: A unit of understanding discovered and taught
- Proof: Verified demonstration of understanding
- Session: A conversation with context and messages
- ApplicationEvent: Real-world application with follow-up tracking

Edge Types:
- requires: Outcome → Concept (gap discovered for goal)
- relates_to: Concept ↔ Concept (cross-domain connections)
- demonstrated_by: Concept → Proof (understanding verified)
- explored_in: Concept → Session (discussed in conversation)
- builds_on: Outcome → Outcome (goals that connect)
- applied_in: Concept → ApplicationEvent (real-world usage)
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, Field


def gen_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


# =============================================================================
# Enums
# =============================================================================


class OutcomeStatus(str, Enum):
    """Status of an outcome/goal."""

    ACTIVE = "active"
    ACHIEVED = "achieved"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class ConceptStatus(str, Enum):
    """Status of a concept."""

    IDENTIFIED = "identified"  # Gap found, not yet taught
    TEACHING = "teaching"  # Currently being taught
    UNDERSTOOD = "understood"  # Learner demonstrated understanding


class DemoType(str, Enum):
    """How understanding was demonstrated."""

    EXPLANATION = "explanation"  # Learner explained the concept
    APPLICATION = "application"  # Learner applied it to a scenario
    BOTH = "both"  # Both explanation and application


class EdgeType(str, Enum):
    """Types of edges in the learning graph."""

    REQUIRES = "requires"  # Outcome → Concept
    RELATES_TO = "relates_to"  # Concept ↔ Concept
    DEMONSTRATED_BY = "demonstrated_by"  # Concept → Proof
    EXPLORED_IN = "explored_in"  # Concept → Session
    BUILDS_ON = "builds_on"  # Outcome → Outcome
    APPLIED_IN = "applied_in"  # Concept → ApplicationEvent


class DialogueMode(str, Enum):
    """What mode SAGE is currently in."""

    CHECK_IN = "check_in"  # Gathering Set/Setting/Intention
    FOLLOWUP = "followup"  # Asking about past application
    OUTCOME_DISCOVERY = "outcome_discovery"  # Finding what they want to do
    FRAMING = "framing"  # Light sketch of territory
    PROBING = "probing"  # Finding the gap
    TEACHING = "teaching"  # Filling the gap
    VERIFICATION = "verification"  # Checking understanding
    OUTCOME_CHECK = "outcome_check"  # Can they do the thing?


class ExplorationDepth(str, Enum):
    """How deeply a concept was explored in a session."""

    MENTIONED = "mentioned"  # Briefly referenced
    DISCUSSED = "discussed"  # Talked through
    DEEP_DIVE = "deep_dive"  # Extensive exploration


class AgeGroup(str, Enum):
    """Learner age group - affects vocabulary, examples, tone."""

    CHILD = "child"  # Under 13
    TEEN = "teen"  # 13-17
    ADULT = "adult"  # 18+


class SkillLevel(str, Enum):
    """General learning ability - affects pace and depth."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class EnergyLevel(str, Enum):
    """Current energy level for session context."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IntentionStrength(str, Enum):
    """How urgent is the learning need."""

    CURIOUS = "curious"  # Just exploring, no pressure
    LEARNING = "learning"  # Actively trying to understand
    URGENT = "urgent"  # Need this now, high stakes


class ApplicationStatus(str, Enum):
    """Status of an application event."""

    UPCOMING = "upcoming"  # Planned, hasn't happened yet
    PENDING_FOLLOWUP = "pending_followup"  # Happened, needs follow-up
    COMPLETED = "completed"  # Followed up and recorded
    SKIPPED = "skipped"  # Didn't happen or wasn't followed up


# =============================================================================
# Learner Models
# =============================================================================


class LearnerProfile(BaseModel):
    """Basic information about the learner."""

    name: Optional[str] = None
    context: Optional[str] = None  # "freelance designer", "PM at a startup"
    background: Optional[str] = None  # Relevant experience
    age_group: Optional[AgeGroup] = None  # Affects vocabulary, examples, tone
    skill_level: Optional[SkillLevel] = None  # General learning ability


class LearnerPreferences(BaseModel):
    """How the learner prefers to learn (Setting)."""

    session_length: str = "medium"  # short, medium, long
    style: str = "mixed"  # practical, theoretical, mixed
    pace: str = "moderate"  # patient, moderate, fast


class LearnerInsights(BaseModel):
    """Patterns learned about this learner over time."""

    # WHEN do they learn best?
    best_energy_level: Optional[str] = None
    best_time_of_day: Optional[str] = None
    optimal_session_length: Optional[str] = None

    # HOW do they learn best?
    prefers_examples: bool = True
    prefers_theory_first: bool = False
    needs_frequent_checks: bool = False
    responds_to_challenge: bool = True

    # What's worked / not worked
    effective_approaches: list[str] = Field(default_factory=list)
    ineffective_approaches: list[str] = Field(default_factory=list)

    # Patterns noticed (free text observations)
    patterns: list[str] = Field(default_factory=list)


class Learner(BaseModel):
    """The root node. One per person."""

    id: str = Field(default_factory=gen_id)
    profile: LearnerProfile = Field(default_factory=LearnerProfile)
    preferences: LearnerPreferences = Field(default_factory=LearnerPreferences)
    insights: LearnerInsights = Field(default_factory=LearnerInsights)
    active_outcome_id: Optional[str] = None
    current_focus: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_session_at: Optional[datetime] = None
    total_sessions: int = 0
    total_proofs: int = 0


# =============================================================================
# Outcome Model
# =============================================================================


class Outcome(BaseModel):
    """A real-world goal. What they want to be able to DO."""

    id: str = Field(default_factory=gen_id)
    learner_id: str
    stated_goal: str  # What they said
    clarified_goal: Optional[str] = None  # What we determined they meant
    motivation: Optional[str] = None  # Why they want this
    success_criteria: Optional[str] = None  # How they'll know they got there
    status: OutcomeStatus = OutcomeStatus.ACTIVE
    territory: Optional[list[str]] = None  # Light framing, not a plan
    created_at: datetime = Field(default_factory=datetime.utcnow)
    achieved_at: Optional[datetime] = None
    last_worked_on: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Concept Model
# =============================================================================


class Concept(BaseModel):
    """A unit of understanding. Created when a gap is identified and taught."""

    id: str = Field(default_factory=gen_id)
    learner_id: str
    name: str  # "value-articulation"
    display_name: str  # "Value Articulation"
    description: Optional[str] = None  # What this concept covers
    discovered_from: Optional[str] = None  # outcome_id where gap was found
    status: ConceptStatus = ConceptStatus.IDENTIFIED
    summary: Optional[str] = None  # Brief recap for future sessions
    times_discussed: int = 0
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    understood_at: Optional[datetime] = None


# =============================================================================
# Proof Models
# =============================================================================


class ProofExchange(BaseModel):
    """The exchange that earned a proof."""

    prompt: str  # What SAGE asked
    response: str  # What the learner said
    analysis: str  # Why this demonstrates understanding


class Proof(BaseModel):
    """Verified understanding. The learner demonstrated they get it."""

    id: str = Field(default_factory=gen_id)
    learner_id: str
    concept_id: str  # What was proven
    session_id: str  # When it was earned
    demonstration_type: DemoType
    evidence: str  # Summary of how they demonstrated it
    confidence: float = 0.8  # 0.0 - 1.0
    exchange: ProofExchange
    earned_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Session Models
# =============================================================================


class SessionContext(BaseModel):
    """Set, Setting, Intention captured at session start."""

    # SET - Current mental/physical state
    energy: Optional[EnergyLevel] = None
    mindset: Optional[str] = None  # "stressed about deadline", "curious"
    time_available: Optional[str] = None  # "15 minutes", "an hour", "open-ended"

    # SETTING - Physical environment
    environment: Optional[str] = None  # "quiet office", "coffee shop", "commuting"
    can_speak: Optional[bool] = None  # Can they talk out loud?
    distraction_level: Optional[str] = None  # "focused", "some interruptions"
    device: Optional[str] = None  # "desktop", "phone"

    # INTENTION - Purpose for this session
    intention_strength: Optional[IntentionStrength] = None
    session_goal: Optional[str] = None  # What they want from THIS session


class Message(BaseModel):
    """A single exchange in the conversation."""

    role: str  # "user" or "sage"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    mode: Optional[str] = None  # Dialogue mode that produced this


class SessionEndingState(BaseModel):
    """Where we left off at end of session."""

    mode: str  # What mode we were in
    current_focus: Optional[str] = None  # What concept/gap we were on
    next_step: Optional[str] = None  # Brief note on what comes next


class Session(BaseModel):
    """A conversation. What happened, what was covered, learner's state."""

    id: str = Field(default_factory=gen_id)
    learner_id: str
    outcome_id: Optional[str] = None  # Which goal was active
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    context: Optional[SessionContext] = None  # Set/Setting/Intention
    messages: list[Message] = Field(default_factory=list)
    summary: Optional[str] = None  # "Found gap, taught, earned proof"
    concepts_explored: list[str] = Field(default_factory=list)  # concept_ids
    proofs_earned: list[str] = Field(default_factory=list)  # proof_ids
    connections_found: list[str] = Field(default_factory=list)  # edge_ids
    ending_state: Optional[SessionEndingState] = None


# =============================================================================
# Application Event Model
# =============================================================================


class ApplicationEvent(BaseModel):
    """Real-world application of learning, with follow-up tracking."""

    id: str = Field(default_factory=gen_id)
    learner_id: str
    concept_ids: list[str]  # Concepts being applied
    outcome_id: Optional[str] = None
    session_id: str  # Where it was mentioned

    # What's planned
    context: str  # "pricing call tomorrow"
    planned_date: Optional[date] = None
    stakes: Optional[str] = None  # "high", "medium", "low"

    # Status
    status: ApplicationStatus = ApplicationStatus.UPCOMING
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Follow-up
    followup_session_id: Optional[str] = None
    followed_up_at: Optional[datetime] = None

    # What happened (filled after follow-up)
    outcome_result: Optional[str] = None  # "went well", "struggled", "mixed"
    what_worked: Optional[str] = None
    what_struggled: Optional[str] = None
    gaps_revealed: Optional[list[str]] = None
    insights: Optional[str] = None


# =============================================================================
# Edge Model
# =============================================================================


class Edge(BaseModel):
    """A connection between nodes in the learning graph."""

    id: str = Field(default_factory=gen_id)
    from_id: str
    from_type: str  # "outcome", "concept", etc.
    to_id: str
    to_type: str
    edge_type: EdgeType
    metadata: dict = Field(default_factory=dict)  # Additional edge data
    created_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Edge Metadata Models (for specific edge types)
# =============================================================================


class RelatesToMetadata(BaseModel):
    """Metadata for relates_to edges between concepts."""

    relationship: str  # How they connect
    strength: float  # 0.0 - 1.0
    discovered_in: str  # session_id


class ExploredInMetadata(BaseModel):
    """Metadata for explored_in edges."""

    depth: ExplorationDepth


class BuildsOnMetadata(BaseModel):
    """Metadata for builds_on edges between outcomes."""

    relationship: str  # How the outcomes connect
