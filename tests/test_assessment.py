"""Tests for the assessment module.

Tests verification question generation, confidence scoring,
and proof handling.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from sage.assessment import (
    ConfidenceFactors,
    ConfidenceScorer,
    ProofHandler,
    VerificationContext,
    VerificationQuestion,
    VerificationQuestionGenerator,
    VerificationStrategy,
    calculate_confidence,
    create_proof_handler,
    get_verification_hints_for_prompt,
)
from sage.context.snapshots import ConceptSnapshot, LearnerSnapshot, OutcomeSnapshot
from sage.graph.models import (
    Concept,
    ConceptStatus,
    DemoType,
    Learner,
    Proof,
    ProofExchange,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def learner_snapshot():
    """Create a test learner snapshot."""
    return LearnerSnapshot(
        id="learner-1",
        name="Test Learner",
        age_group="adult",
        skill_level="intermediate",
        context="software developer",
        total_sessions=5,
        total_proofs=3,
        active_outcome_id="outcome-1",
    )


@pytest.fixture
def child_learner_snapshot():
    """Create a child learner snapshot."""
    return LearnerSnapshot(
        id="learner-2",
        name="Young Learner",
        age_group="child",
        skill_level="beginner",
        context=None,
        total_sessions=2,
        total_proofs=0,
        active_outcome_id=None,
    )


@pytest.fixture
def concept_snapshot():
    """Create a test concept snapshot."""
    return ConceptSnapshot(
        id="concept-1",
        name="test-concept",
        display_name="Test Concept",
        description="A test concept",
        summary="This is a test concept for verification",
        status="teaching",
    )


@pytest.fixture
def outcome_snapshot():
    """Create a test outcome snapshot."""
    return OutcomeSnapshot(
        id="outcome-1",
        stated_goal="Learn to test software",
        clarified_goal="Write unit tests for Python code",
        status="active",
    )


@pytest.fixture
def related_concept():
    """Create a related concept snapshot."""
    return ConceptSnapshot(
        id="concept-2",
        name="related-concept",
        display_name="Related Concept",
        description="A related concept",
        summary="Summary of related concept",
        status="understood",
        proof_confidence=0.9,
    )


@pytest.fixture
def proof_exchange():
    """Create a test proof exchange."""
    return ProofExchange(
        prompt="Can you explain the test concept in your own words?",
        response="The test concept is about verifying that code works correctly "
        "by writing automated checks. I use it to make sure my functions "
        "return the expected outputs and handle edge cases properly.",
        analysis="The learner demonstrated clear understanding using their own words. "
        "They correctly explained the purpose and showed good application knowledge.",
    )


@pytest.fixture
def mock_graph():
    """Create a mock learning graph."""
    graph = MagicMock()
    graph.get_concept.return_value = Concept(
        id="concept-1",
        learner_id="learner-1",
        name="test-concept",
        display_name="Test Concept",
        status=ConceptStatus.TEACHING,
    )
    graph.get_learner.return_value = Learner(
        id="learner-1",
        total_proofs=5,
    )
    return graph


# =============================================================================
# VerificationStrategy Tests
# =============================================================================


class TestVerificationStrategy:
    """Tests for VerificationStrategy enum."""

    def test_strategy_values(self):
        """Test strategy enum values."""
        assert VerificationStrategy.EXPLAIN_BACK == "explain_back"
        assert VerificationStrategy.NEW_SCENARIO == "new_scenario"
        assert VerificationStrategy.TEST_BOUNDARIES == "test_boundaries"
        assert VerificationStrategy.FIND_CONNECTIONS == "find_connections"


# =============================================================================
# VerificationQuestionGenerator Tests
# =============================================================================


class TestVerificationQuestionGenerator:
    """Tests for verification question generation."""

    def test_generate_for_adult_intermediate(
        self, learner_snapshot, concept_snapshot
    ):
        """Test generation for adult intermediate learner."""
        context = VerificationContext(
            learner=learner_snapshot,
            concept=concept_snapshot,
        )
        generator = VerificationQuestionGenerator()
        question = generator.generate_verification(context)

        assert isinstance(question, VerificationQuestion)
        assert question.concept_id == "concept-1"
        assert question.concept_name == "Test Concept"
        # Without related concepts, adult intermediate gets NEW_SCENARIO
        assert question.strategy == VerificationStrategy.NEW_SCENARIO

    def test_generate_for_child(
        self, child_learner_snapshot, concept_snapshot
    ):
        """Test generation adapts for child learner."""
        context = VerificationContext(
            learner=child_learner_snapshot,
            concept=concept_snapshot,
        )
        generator = VerificationQuestionGenerator()
        question = generator.generate_verification(context)

        assert question.strategy == VerificationStrategy.EXPLAIN_BACK
        # Check for child-friendly or beginner-friendly in any adaptation
        has_adaptation = any(
            "child-friendly" in a or "beginner-friendly" in a
            for a in question.adaptations
        )
        assert has_adaptation

    def test_generate_with_related_concepts(
        self, learner_snapshot, concept_snapshot, related_concept
    ):
        """Test generation leverages related concepts."""
        context = VerificationContext(
            learner=learner_snapshot,
            concept=concept_snapshot,
            related_concepts=[related_concept],
        )
        generator = VerificationQuestionGenerator()
        question = generator.generate_verification(context)

        assert question.strategy == VerificationStrategy.FIND_CONNECTIONS
        assert "connecting concepts" in question.adaptations
        assert related_concept.display_name in question.question

    def test_generate_for_advanced_learner(
        self, concept_snapshot
    ):
        """Test generation uses boundaries for advanced learner."""
        advanced_learner = LearnerSnapshot(
            id="learner-3",
            name="Advanced Learner",
            age_group="adult",
            skill_level="advanced",
            context="senior engineer",
            total_sessions=20,
            total_proofs=15,
            active_outcome_id="outcome-1",
        )
        context = VerificationContext(
            learner=advanced_learner,
            concept=concept_snapshot,
        )
        generator = VerificationQuestionGenerator()
        question = generator.generate_verification(context)

        assert question.strategy == VerificationStrategy.TEST_BOUNDARIES
        assert "testing boundaries" in question.adaptations

    def test_generate_followup_partial(
        self, learner_snapshot, concept_snapshot
    ):
        """Test followup generation for partial understanding."""
        context = VerificationContext(
            learner=learner_snapshot,
            concept=concept_snapshot,
        )
        generator = VerificationQuestionGenerator()
        question = generator.generate_followup_verification(
            context,
            previous_answer="I think it's about testing...",
            understanding_level="partial",
        )

        assert "probing specific gap" in question.adaptations
        assert question.strategy == VerificationStrategy.NEW_SCENARIO

    def test_generate_followup_not_there(
        self, learner_snapshot, concept_snapshot
    ):
        """Test followup generation when learner isn't getting it."""
        context = VerificationContext(
            learner=learner_snapshot,
            concept=concept_snapshot,
        )
        generator = VerificationQuestionGenerator()
        question = generator.generate_followup_verification(
            context,
            previous_answer="I don't know...",
            understanding_level="not_there",
        )

        assert "simplified for gaps" in question.adaptations
        assert question.strategy == VerificationStrategy.EXPLAIN_BACK


# =============================================================================
# ConfidenceScorer Tests
# =============================================================================


class TestConfidenceScorer:
    """Tests for confidence scoring."""

    def test_base_scores(self):
        """Test base scores by demonstration type."""
        scorer = ConfidenceScorer()

        explanation_factors = ConfidenceFactors(
            demonstration_type=DemoType.EXPLANATION,
            exchange_quality=0.5,
        )
        application_factors = ConfidenceFactors(
            demonstration_type=DemoType.APPLICATION,
            exchange_quality=0.5,
        )
        both_factors = ConfidenceFactors(
            demonstration_type=DemoType.BOTH,
            exchange_quality=0.5,
        )

        explanation_score = scorer.score(explanation_factors)
        application_score = scorer.score(application_factors)
        both_score = scorer.score(both_factors)

        # Both should have highest base score
        assert both_score > application_score > explanation_score

    def test_quality_bonuses(self):
        """Test that quality factors increase score."""
        scorer = ConfidenceScorer()

        basic_factors = ConfidenceFactors(
            demonstration_type=DemoType.EXPLANATION,
            exchange_quality=0.5,
            used_own_words=0.5,
            applied_correctly=0.5,
        )
        high_quality_factors = ConfidenceFactors(
            demonstration_type=DemoType.EXPLANATION,
            exchange_quality=1.0,
            used_own_words=1.0,
            applied_correctly=1.0,
            showed_boundary_awareness=1.0,
            made_connections=1.0,
        )

        basic_score = scorer.score(basic_factors)
        high_quality_score = scorer.score(high_quality_factors)

        assert high_quality_score > basic_score

    def test_parrot_penalty(self):
        """Test that parroting reduces score."""
        scorer = ConfidenceScorer()

        normal_factors = ConfidenceFactors(
            demonstration_type=DemoType.EXPLANATION,
            exchange_quality=0.7,
        )
        parroting_factors = ConfidenceFactors(
            demonstration_type=DemoType.EXPLANATION,
            exchange_quality=0.7,
            just_parroted=True,
        )

        normal_score = scorer.score(normal_factors)
        parroting_score = scorer.score(parroting_factors)

        assert parroting_score < normal_score
        assert normal_score - parroting_score == pytest.approx(0.3, abs=0.01)

    def test_misconception_penalty(self):
        """Test that misconceptions reduce score."""
        scorer = ConfidenceScorer()

        normal_factors = ConfidenceFactors(
            demonstration_type=DemoType.EXPLANATION,
            exchange_quality=0.7,
        )
        misconception_factors = ConfidenceFactors(
            demonstration_type=DemoType.EXPLANATION,
            exchange_quality=0.7,
            had_misconceptions=True,
        )

        normal_score = scorer.score(normal_factors)
        misconception_score = scorer.score(misconception_factors)

        assert misconception_score < normal_score

    def test_score_clamped_to_range(self):
        """Test that scores are clamped between 0 and 1."""
        scorer = ConfidenceScorer()

        # Maximum possible factors
        max_factors = ConfidenceFactors(
            demonstration_type=DemoType.BOTH,
            exchange_quality=1.0,
            used_own_words=1.0,
            applied_correctly=1.0,
            showed_boundary_awareness=1.0,
            made_connections=1.0,
        )
        # Minimum with penalties
        min_factors = ConfidenceFactors(
            demonstration_type=DemoType.EXPLANATION,
            exchange_quality=0.0,
            used_own_words=0.0,
            applied_correctly=0.0,
            just_parroted=True,
            had_misconceptions=True,
        )

        max_score = scorer.score(max_factors)
        min_score = scorer.score(min_factors)

        assert 0.0 <= max_score <= 1.0
        assert 0.0 <= min_score <= 1.0

    def test_score_from_exchange(self, proof_exchange):
        """Test scoring from a proof exchange."""
        scorer = ConfidenceScorer()
        score = scorer.score_from_exchange(proof_exchange, DemoType.EXPLANATION)

        assert 0.0 <= score <= 1.0
        # Good exchange should have decent score
        assert score > 0.5

    def test_analyze_exchange_detects_own_words(self):
        """Test that analysis detects 'own words' indicators."""
        scorer = ConfidenceScorer()
        exchange = ProofExchange(
            prompt="Explain this concept",
            response="I think of it as...",
            analysis="The learner used their own words to describe the concept, "
            "showing original understanding.",
        )
        factors = scorer.analyze_exchange(exchange, DemoType.EXPLANATION)

        assert factors.used_own_words > 0.5

    def test_analyze_exchange_detects_parroting(self):
        """Test that analysis detects parroting."""
        scorer = ConfidenceScorer()
        exchange = ProofExchange(
            prompt="Explain this concept",
            response="The concept is...",
            analysis="The learner just parroted back the explanation "
            "without showing real understanding.",
        )
        factors = scorer.analyze_exchange(exchange, DemoType.EXPLANATION)

        assert factors.just_parroted is True


class TestCalculateConfidence:
    """Tests for the convenience function."""

    def test_calculate_confidence(self, proof_exchange):
        """Test the convenience function works."""
        score = calculate_confidence(DemoType.EXPLANATION, proof_exchange)

        assert 0.0 <= score <= 1.0


# =============================================================================
# ProofHandler Tests
# =============================================================================


class TestProofHandler:
    """Tests for proof handling."""

    def test_create_proof(self, mock_graph, proof_exchange):
        """Test proof creation."""
        mock_graph.create_proof_obj.return_value = Proof(
            id="proof-1",
            concept_id="concept-1",
            learner_id="learner-1",
            session_id="session-1",
            demonstration_type=DemoType.EXPLANATION,
            evidence="Test evidence",
            confidence=0.8,
            exchange=proof_exchange,
        )

        handler = ProofHandler(mock_graph)
        proof = handler.create_proof(
            concept_id="concept-1",
            learner_id="learner-1",
            session_id="session-1",
            demonstration_type=DemoType.EXPLANATION,
            evidence="Test evidence",
            confidence=0.8,
            exchange=proof_exchange,
        )

        assert proof.concept_id == "concept-1"
        assert proof.confidence == 0.8
        mock_graph.create_proof_obj.assert_called_once()

    def test_mark_concept_understood(self, mock_graph):
        """Test marking concept as understood."""
        mock_graph.update_concept.return_value = Concept(
            id="concept-1",
            learner_id="learner-1",
            name="test-concept",
            display_name="Test Concept",
            status=ConceptStatus.UNDERSTOOD,
        )

        handler = ProofHandler(mock_graph)
        updated = handler.mark_concept_understood("concept-1")

        assert updated.status == ConceptStatus.UNDERSTOOD
        mock_graph.update_concept.assert_called_once()

    def test_mark_concept_understood_not_found(self, mock_graph):
        """Test handling of missing concept."""
        mock_graph.get_concept.return_value = None

        handler = ProofHandler(mock_graph)
        result = handler.mark_concept_understood("missing-concept")

        assert result is None

    def test_increment_learner_proofs(self, mock_graph):
        """Test incrementing learner proof count."""
        handler = ProofHandler(mock_graph)
        handler.increment_learner_proofs("learner-1")

        mock_graph.get_learner.assert_called_once_with("learner-1")
        mock_graph.update_learner.assert_called_once()

    def test_parse_demo_type_explanation(self, mock_graph):
        """Test parsing explanation demo type."""
        handler = ProofHandler(mock_graph)

        assert handler._parse_demo_type("explanation") == DemoType.EXPLANATION
        assert handler._parse_demo_type("EXPLANATION") == DemoType.EXPLANATION
        assert handler._parse_demo_type("explain") == DemoType.EXPLANATION

    def test_parse_demo_type_application(self, mock_graph):
        """Test parsing application demo type."""
        handler = ProofHandler(mock_graph)

        assert handler._parse_demo_type("application") == DemoType.APPLICATION
        assert handler._parse_demo_type("apply") == DemoType.APPLICATION
        assert handler._parse_demo_type("APPLICATION") == DemoType.APPLICATION

    def test_parse_demo_type_both(self, mock_graph):
        """Test parsing both demo type."""
        handler = ProofHandler(mock_graph)

        assert handler._parse_demo_type("both") == DemoType.BOTH
        assert handler._parse_demo_type("synthesis") == DemoType.BOTH
        assert handler._parse_demo_type("BOTH") == DemoType.BOTH

    def test_has_proof(self, mock_graph):
        """Test checking if proof exists."""
        mock_graph.has_proof.return_value = True

        handler = ProofHandler(mock_graph)
        result = handler.has_proof("concept-1", "learner-1")

        assert result is True
        mock_graph.has_proof.assert_called_once_with("concept-1", "learner-1")

    def test_create_proof_handler_factory(self, mock_graph):
        """Test the factory function."""
        handler = create_proof_handler(mock_graph)

        assert isinstance(handler, ProofHandler)


# =============================================================================
# Verification Hints Tests
# =============================================================================


class TestVerificationHints:
    """Tests for verification hint generation."""

    def test_get_verification_hints_basic(
        self, learner_snapshot, concept_snapshot
    ):
        """Test basic hint generation."""
        context = VerificationContext(
            learner=learner_snapshot,
            concept=concept_snapshot,
        )
        hints = get_verification_hints_for_prompt(context)

        assert "Verification Guidance" in hints
        assert "Test Concept" in hints
        assert "adult" in hints
        assert "intermediate" in hints

    def test_get_verification_hints_with_related(
        self, learner_snapshot, concept_snapshot, related_concept
    ):
        """Test hints include related concepts."""
        context = VerificationContext(
            learner=learner_snapshot,
            concept=concept_snapshot,
            related_concepts=[related_concept],
        )
        hints = get_verification_hints_for_prompt(context)

        assert "Connected concepts" in hints
        assert related_concept.display_name in hints

    def test_hints_include_reminders(
        self, learner_snapshot, concept_snapshot
    ):
        """Test that hints include verification reminders."""
        context = VerificationContext(
            learner=learner_snapshot,
            concept=concept_snapshot,
        )
        hints = get_verification_hints_for_prompt(context)

        assert "real understanding" in hints.lower()
        assert "their words" in hints.lower() or "THEIR words" in hints
