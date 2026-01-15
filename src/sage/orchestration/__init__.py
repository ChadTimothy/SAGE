"""SAGE Orchestration Layer.

This module handles input normalization, intent extraction,
UI generation, and orchestration of the voice/UI parity system.
"""

from sage.orchestration.intent_extractor import (
    ExtractedIntent,
    INTENT_SCHEMAS,
    SemanticIntentExtractor,
)
from sage.orchestration.models import (
    UIGenerationHint,
    UIGenerationRequest,
    UITreeSpec,
)
from sage.orchestration.normalizer import (
    InputModality,
    InputNormalizer,
    NormalizedInput,
)
from sage.orchestration.orchestrator import (
    OrchestratorDecision,
    OutputStrategy,
    SAGEOrchestrator,
)
from sage.orchestration.ui_agent import (
    UIGenerationAgent,
    create_ui_agent,
)

__all__ = [
    # Normalizer
    "InputModality",
    "InputNormalizer",
    "NormalizedInput",
    # Intent Extractor
    "ExtractedIntent",
    "INTENT_SCHEMAS",
    "SemanticIntentExtractor",
    # UI Generation
    "UIGenerationAgent",
    "UIGenerationHint",
    "UIGenerationRequest",
    "UITreeSpec",
    "create_ui_agent",
    # Orchestrator
    "OrchestratorDecision",
    "OutputStrategy",
    "SAGEOrchestrator",
]
