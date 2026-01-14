"""Context management for SAGE.

This module provides:
- Snapshot models for token-efficient prompts
- FullContext loading at session start
- TurnContext building for each LLM call
- State persistence after each turn
- LearnerInsights tracking over time
- Application event lifecycle management
"""

from .applications import (
    ApplicationLifecycle,
    FollowupResult,
    UpcomingApplication,
    detect_application_in_message,
    generate_followup_prompt,
)
from .full_context import (
    FullContext,
    FullContextLoader,
)
from .insights import (
    InsightsTracker,
    detect_application_patterns,
)
from .persistence import (
    ApplicationDetected,
    ConnectionDiscovered,
    FollowupResponse,
    GapIdentified,
    ProofEarned,
    StateChange,
    TurnChanges,
    TurnPersistence,
    persist_turn,
)
from .snapshots import (
    ApplicationSnapshot,
    ConceptSnapshot,
    LearnerSnapshot,
    OutcomeProgress,
    OutcomeSnapshot,
    ProofSnapshot,
    RelatedConcept,
)
from .turn_context import (
    TurnContext,
    TurnContextBuilder,
    build_turn_context,
)

__all__ = [
    # Snapshots
    "ApplicationSnapshot",
    "ConceptSnapshot",
    "LearnerSnapshot",
    "OutcomeProgress",
    "OutcomeSnapshot",
    "ProofSnapshot",
    "RelatedConcept",
    # Full Context
    "FullContext",
    "FullContextLoader",
    # Turn Context
    "TurnContext",
    "TurnContextBuilder",
    "build_turn_context",
    # Persistence
    "ApplicationDetected",
    "ConnectionDiscovered",
    "FollowupResponse",
    "GapIdentified",
    "ProofEarned",
    "StateChange",
    "TurnChanges",
    "TurnPersistence",
    "persist_turn",
    # Insights
    "InsightsTracker",
    "detect_application_patterns",
    # Applications
    "ApplicationLifecycle",
    "FollowupResult",
    "UpcomingApplication",
    "detect_application_in_message",
    "generate_followup_prompt",
]
