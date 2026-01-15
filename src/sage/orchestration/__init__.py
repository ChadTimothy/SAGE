"""SAGE Orchestration Layer.

This module handles input normalization, intent extraction, and
orchestration of the voice/UI parity system.
"""

from sage.orchestration.intent_extractor import (
    ExtractedIntent,
    INTENT_SCHEMAS,
    SemanticIntentExtractor,
)
from sage.orchestration.normalizer import (
    InputModality,
    InputNormalizer,
    NormalizedInput,
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
]
