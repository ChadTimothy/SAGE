"""Confidence scoring for proofs.

Evaluates the quality of demonstrations to assign confidence scores.
Higher scores for explanations in own words, correct application,
and awareness of boundaries.
"""

from dataclasses import dataclass
from typing import Optional

from sage.graph.models import DemoType, ProofExchange


@dataclass
class ConfidenceFactors:
    """Factors that influence confidence scoring."""

    # Base factors
    demonstration_type: DemoType
    exchange_quality: float  # 0.0-1.0 based on exchange analysis

    # Quality indicators (each 0.0-1.0)
    used_own_words: float = 0.5
    applied_correctly: float = 0.5
    showed_boundary_awareness: float = 0.0
    made_connections: float = 0.0

    # Negative indicators
    just_parroted: bool = False
    had_misconceptions: bool = False


class ConfidenceScorer:
    """Scores confidence in proof demonstrations.

    Considers:
    - Demonstration type (explanation vs application vs both)
    - Quality of the verification exchange
    - Evidence of real understanding vs memorization
    """

    # Base scores by demonstration type
    BASE_SCORES = {
        DemoType.EXPLANATION: 0.7,
        DemoType.APPLICATION: 0.75,
        DemoType.BOTH: 0.85,  # Both explanation and application
    }

    # Weight factors for scoring
    WEIGHTS = {
        "own_words": 0.2,
        "applied_correctly": 0.2,
        "boundary_awareness": 0.1,
        "connections": 0.1,
        "exchange_quality": 0.2,
    }

    # Penalties
    PARROT_PENALTY = 0.3
    MISCONCEPTION_PENALTY = 0.2

    def score(self, factors: ConfidenceFactors) -> float:
        """Calculate confidence score from factors."""
        base = self.BASE_SCORES.get(factors.demonstration_type, 0.7)

        quality_bonus = (
            self.WEIGHTS["own_words"] * factors.used_own_words
            + self.WEIGHTS["applied_correctly"] * factors.applied_correctly
            + self.WEIGHTS["boundary_awareness"] * factors.showed_boundary_awareness
            + self.WEIGHTS["connections"] * factors.made_connections
            + self.WEIGHTS["exchange_quality"] * factors.exchange_quality
        )

        score = base * 0.6 + quality_bonus * 0.4

        if factors.just_parroted:
            score -= self.PARROT_PENALTY
        if factors.had_misconceptions:
            score -= self.MISCONCEPTION_PENALTY

        return max(0.0, min(1.0, score))

    def score_from_exchange(
        self,
        exchange: ProofExchange,
        demonstration_type: DemoType,
    ) -> float:
        """Score confidence based on verification exchange."""
        return self.score(self.analyze_exchange(exchange, demonstration_type))

    def analyze_exchange(
        self,
        exchange: ProofExchange,
        demonstration_type: DemoType,
    ) -> ConfidenceFactors:
        """Analyze an exchange to extract confidence factors."""
        analysis_lower = exchange.analysis.lower()

        return ConfidenceFactors(
            demonstration_type=demonstration_type,
            exchange_quality=self._assess_exchange_quality(exchange),
            used_own_words=self._detect_own_words(analysis_lower),
            applied_correctly=self._detect_correct_application(analysis_lower),
            showed_boundary_awareness=self._detect_boundary_awareness(analysis_lower),
            made_connections=self._detect_connections(analysis_lower),
            just_parroted=self._detect_parroting(analysis_lower),
            had_misconceptions=self._detect_misconceptions(analysis_lower),
        )

    def _score_indicators(
        self,
        analysis: str,
        positive: list[str],
        negative: list[str],
        base: float,
        pos_weight: float,
        neg_weight: float,
    ) -> float:
        """Score based on positive and negative indicators."""
        score = base
        for indicator in positive:
            if indicator in analysis:
                score += pos_weight
        for indicator in negative:
            if indicator in analysis:
                score -= neg_weight
        return max(0.0, min(1.0, score))

    def _detect_own_words(self, analysis: str) -> float:
        """Detect if learner used their own words."""
        return self._score_indicators(
            analysis,
            positive=["own words", "their own", "original", "unique", "personal", "rephrased"],
            negative=["repeated", "parroted", "copied", "memorized"],
            base=0.5,
            pos_weight=0.1,
            neg_weight=0.2,
        )

    def _detect_correct_application(self, analysis: str) -> float:
        """Detect if learner applied concept correctly."""
        return self._score_indicators(
            analysis,
            positive=["correctly", "accurate", "proper", "appropriate", "well applied", "good application"],
            negative=["incorrect", "wrong", "misapplied", "confused"],
            base=0.5,
            pos_weight=0.15,
            neg_weight=0.2,
        )

    def _detect_boundary_awareness(self, analysis: str) -> float:
        """Detect if learner showed awareness of concept boundaries."""
        indicators = ["boundary", "limit", "edge case", "when not to", "doesn't apply", "exception"]
        return min(1.0, sum(0.3 for ind in indicators if ind in analysis))

    def _detect_connections(self, analysis: str) -> float:
        """Detect if learner made connections to other concepts."""
        indicators = ["connect", "relate", "link", "similar to", "builds on", "integrated"]
        return min(1.0, sum(0.25 for ind in indicators if ind in analysis))

    def _detect_parroting(self, analysis: str) -> bool:
        """Detect if learner just parroted back the explanation."""
        indicators = ["parrot", "repeated back", "just said", "memorized", "recited"]
        return any(ind in analysis for ind in indicators)

    def _detect_misconceptions(self, analysis: str) -> bool:
        """Detect if learner showed misconceptions."""
        indicators = ["misconception", "misunderstand", "confused", "incorrect", "wrong", "gap"]
        return any(ind in analysis for ind in indicators)

    def _assess_exchange_quality(self, exchange: ProofExchange) -> float:
        """Assess overall quality of the exchange."""
        response_length = len(exchange.response)
        if response_length < 50:
            length_score = 0.3
        elif response_length < 150:
            length_score = 0.5
        elif response_length < 300:
            length_score = 0.7
        else:
            length_score = 0.9

        sentiment = self._score_indicators(
            exchange.analysis.lower(),
            positive=["clear", "solid", "strong", "excellent", "well", "good"],
            negative=["weak", "unclear", "partial", "incomplete", "lacking"],
            base=0.5,
            pos_weight=0.1,
            neg_weight=0.1,
        )

        return (length_score + sentiment) / 2


def calculate_confidence(demonstration_type: DemoType, exchange: ProofExchange) -> float:
    """Convenience function to calculate confidence score."""
    return ConfidenceScorer().score_from_exchange(exchange, demonstration_type)
