"""SAGE Orchestration Layer.

This module handles input normalization, intent extraction, and
orchestration of the voice/UI parity system.
"""

from sage.orchestration.normalizer import (
    InputModality,
    InputNormalizer,
    NormalizedInput,
)

__all__ = [
    "InputModality",
    "InputNormalizer",
    "NormalizedInput",
]
