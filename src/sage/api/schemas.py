"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# Learner schemas
class LearnerCreate(BaseModel):
    """Request to create a new learner."""

    name: str
    age_group: str = "adult"  # child, teen, adult
    skill_level: str = "beginner"  # beginner, intermediate, advanced


class LearnerResponse(BaseModel):
    """Learner response."""

    id: str
    name: str
    age_group: str
    skill_level: str
    active_outcome_id: Optional[str] = None
    total_sessions: int = 0
    total_proofs: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class LearnerStateResponse(BaseModel):
    """Full learner state for UI."""

    learner: LearnerResponse
    active_outcome: Optional[dict] = None
    recent_concepts: list[dict] = Field(default_factory=list)
    recent_proofs: list[dict] = Field(default_factory=list)
    pending_followups: list[dict] = Field(default_factory=list)


# Session schemas
class SessionCreate(BaseModel):
    """Request to start a new session."""

    learner_id: str
    outcome_id: Optional[str] = None


class SessionResponse(BaseModel):
    """Session response."""

    id: str
    learner_id: str
    outcome_id: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    message_count: int = 0

    model_config = {"from_attributes": True}


class SessionEndRequest(BaseModel):
    """Request to end a session."""

    notes: Optional[str] = None


# Chat schemas
class ChatMessage(BaseModel):
    """WebSocket chat message from client."""

    type: str = "message"  # message, voice
    content: str = ""
    audio: Optional[str] = None  # base64 encoded audio for voice


class ChatChunk(BaseModel):
    """WebSocket streaming chunk to client."""

    type: str = "chunk"
    content: str


class ChatComplete(BaseModel):
    """WebSocket complete response to client."""

    type: str = "complete"
    response: dict


class ChatError(BaseModel):
    """WebSocket error to client."""

    type: str = "error"
    message: str


# Outcome schemas
class OutcomeResponse(BaseModel):
    """Outcome response."""

    id: str
    learner_id: str
    description: str
    status: str
    created_at: datetime
    achieved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# Proof schemas
class ProofResponse(BaseModel):
    """Proof response."""

    id: str
    concept_id: str
    learner_id: str
    demonstration_type: str
    confidence: float
    earned_at: datetime

    model_config = {"from_attributes": True}


# Graph schemas
class GraphNodeResponse(BaseModel):
    """Graph node for visualization."""

    id: str
    type: str  # learner, outcome, concept, proof, session
    label: str
    data: dict = Field(default_factory=dict)


class GraphEdgeResponse(BaseModel):
    """Graph edge for visualization."""

    id: str
    from_id: str
    to_id: str
    edge_type: str


class GraphResponse(BaseModel):
    """Knowledge graph data for visualization."""

    nodes: list[GraphNodeResponse] = Field(default_factory=list)
    edges: list[GraphEdgeResponse] = Field(default_factory=list)
