"""Assessment module for verification and proof handling.

Provides verification question generation, confidence scoring,
and proof creation/management.
"""

from .confidence import (
    ConfidenceFactors,
    ConfidenceScorer,
    calculate_confidence,
)
from .proof_handler import (
    ProofHandler,
    create_proof_handler,
)
from .verification import (
    VerificationContext,
    VerificationQuestion,
    VerificationQuestionGenerator,
    VerificationStrategy,
    get_verification_hints_for_prompt,
)

__all__ = [
    # Verification
    "VerificationStrategy",
    "VerificationQuestion",
    "VerificationContext",
    "VerificationQuestionGenerator",
    "get_verification_hints_for_prompt",
    # Confidence
    "ConfidenceFactors",
    "ConfidenceScorer",
    "calculate_confidence",
    # Proof handling
    "ProofHandler",
    "create_proof_handler",
]
