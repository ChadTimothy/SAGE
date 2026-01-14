"""Tests for the Gap Finder module (M4)."""

import pytest
from datetime import datetime, date
from uuid import uuid4

from sage.context.snapshots import ConceptSnapshot, LearnerSnapshot, OutcomeSnapshot
from sage.dialogue.structured_output import (
    ConnectionDiscovered,
    GapIdentified,
    SAGEResponse,
)
from sage.gaps import (
    ConnectionCandidate,
    ConnectionFinder,
    GapFinder,
    GapFinderResult,
    GapStore,
    ProbingContext,
    ProbingQuestion,
    ProbingQuestionGenerator,
    ProbingStrategy,
    create_gap_finder,
    get_connection_hints_for_prompt,
    get_probing_hints_for_prompt,
)
from sage.graph.learning_graph import LearningGraph
from sage.graph.models import (
    Concept,
    ConceptStatus,
    DialogueMode,
    Edge,
    EdgeType,
    EnergyLevel,
    Learner,
    Outcome,
    Proof,
    Session,
    SessionContext,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / "test_gaps.db")


@pytest.fixture
def graph(db_path):
    """Create a test learning graph."""
    return LearningGraph(db_path)


@pytest.fixture
def learner(graph):
    """Create a test learner."""
    from sage.graph.models import LearnerProfile

    learner = Learner(
        id=str(uuid4()),
        profile=LearnerProfile(
            name="Test Learner",
            age_group="adult",
            skill_level="intermediate",
        ),
    )
    return graph.create_learner(learner)


@pytest.fixture
def outcome(graph, learner):
    """Create a test outcome."""
    outcome = Outcome(
        id=str(uuid4()),
        learner_id=learner.id,
        stated_goal="Price freelance services confidently",
        clarified_goal="Quote appropriate rates without hesitation",
        success_criteria="Handle pricing objections smoothly",
        is_active=True,
    )
    return graph.create_outcome_obj(outcome)


@pytest.fixture
def learner_snapshot(learner):
    """Create a learner snapshot."""
    return LearnerSnapshot.from_learner(learner)


@pytest.fixture
def outcome_snapshot(outcome):
    """Create an outcome snapshot."""
    return OutcomeSnapshot.from_outcome(outcome)


@pytest.fixture
def probing_context(learner_snapshot, outcome_snapshot):
    """Create a probing context."""
    return ProbingContext(
        learner=learner_snapshot,
        outcome=outcome_snapshot,
        session_context=None,
        proven_concepts=[],
        concepts_explored=[],
    )


# =============================================================================
# Probing Question Generation Tests
# =============================================================================


class TestProbingQuestionGenerator:
    """Tests for ProbingQuestionGenerator."""

    def test_generate_initial_probe_with_outcome(self, probing_context):
        """Test generating initial probe with outcome."""
        generator = ProbingQuestionGenerator()
        question = generator.generate_initial_probe(probing_context)

        assert isinstance(question, ProbingQuestion)
        assert question.question
        assert question.strategy in [
            ProbingStrategy.DIRECT,
            ProbingStrategy.SCENARIO,
        ]

    def test_generate_initial_probe_without_outcome(self, learner_snapshot):
        """Test generating initial probe without outcome."""
        context = ProbingContext(
            learner=learner_snapshot,
            outcome=None,
            session_context=None,
            proven_concepts=[],
            concepts_explored=[],
        )
        generator = ProbingQuestionGenerator()
        question = generator.generate_initial_probe(context)

        assert "blocking" in question.question.lower()
        assert question.strategy == ProbingStrategy.DIRECT

    def test_generate_low_energy_probe(self, learner_snapshot, outcome_snapshot):
        """Test generating probe for low energy state."""
        context = ProbingContext(
            learner=learner_snapshot,
            outcome=outcome_snapshot,
            session_context=SessionContext(energy=EnergyLevel.LOW),
            proven_concepts=[],
            concepts_explored=[],
        )
        generator = ProbingQuestionGenerator()
        question = generator.generate_initial_probe(context)

        # Low energy should produce shorter, focused probe
        assert "quick" in question.question.lower() or len(question.question) < 100
        assert question.strategy == ProbingStrategy.DIRECT

    def test_generate_followup_probe(self, probing_context):
        """Test generating follow-up probe."""
        generator = ProbingQuestionGenerator()
        question = generator.generate_followup_probe(
            probing_context,
            previous_response="I'm not sure how to respond to that",
        )

        assert isinstance(question, ProbingQuestion)
        assert question.strategy == ProbingStrategy.INDIRECT

    def test_generate_targeted_probe(self, probing_context):
        """Test generating targeted probe with gap hint."""
        generator = ProbingQuestionGenerator()
        question = generator.generate_followup_probe(
            probing_context,
            previous_response="It's hard to talk about money",
            gap_hint="pricing conversations",
        )

        assert "pricing conversations" in question.question

    def test_generate_misconception_check(self, probing_context):
        """Test generating misconception check."""
        generator = ProbingQuestionGenerator()
        question = generator.generate_misconception_check(
            probing_context, "hourly vs value pricing"
        )

        assert question.strategy == ProbingStrategy.MISCONCEPTION
        assert "hourly vs value pricing" in question.question

    def test_child_adaptation(self, outcome_snapshot):
        """Test question adaptation for children."""
        child_learner = LearnerSnapshot(
            id="child-1",
            name="Young Learner",
            age_group="child",
            skill_level="beginner",
            context=None,
            total_sessions=0,
            total_proofs=0,
            active_outcome_id=None,
        )
        context = ProbingContext(
            learner=child_learner,
            outcome=outcome_snapshot,
            session_context=None,
            proven_concepts=[],
            concepts_explored=[],
        )
        generator = ProbingQuestionGenerator()
        question = generator.generate_initial_probe(context)

        # Child should get direct probing, simpler language
        assert question.strategy == ProbingStrategy.DIRECT


class TestProbingPromptHints:
    """Tests for probing prompt hint generation."""

    def test_get_probing_hints_basic(self, probing_context):
        """Test basic probing hints generation."""
        hints = get_probing_hints_for_prompt(probing_context)

        assert "Probing Guidance" in hints
        assert "Age adaptation" in hints
        # Note: Skill level is only shown for beginner/advanced, not intermediate
        assert "Their goal" in hints

    def test_get_probing_hints_with_proven_concepts(self, learner_snapshot, outcome_snapshot):
        """Test probing hints include proven concepts."""
        proven = [
            ConceptSnapshot(
                id="c1",
                name="basic-pricing",
                display_name="Basic Pricing",
                description="Understanding basic pricing concepts",
                summary="Knows about pricing basics",
                status="understood",
                proof_confidence=0.85,
            )
        ]
        context = ProbingContext(
            learner=learner_snapshot,
            outcome=outcome_snapshot,
            session_context=None,
            proven_concepts=proven,
            concepts_explored=[],
        )
        hints = get_probing_hints_for_prompt(context)

        assert "What they've proven" in hints
        assert "Basic Pricing" in hints

    def test_get_probing_hints_low_energy(self, learner_snapshot, outcome_snapshot):
        """Test probing hints adapt for low energy."""
        context = ProbingContext(
            learner=learner_snapshot,
            outcome=outcome_snapshot,
            session_context=SessionContext(energy=EnergyLevel.LOW),
            proven_concepts=[],
            concepts_explored=[],
        )
        hints = get_probing_hints_for_prompt(context)

        assert "Low energy" in hints


# =============================================================================
# Gap Store Tests
# =============================================================================


class TestGapStore:
    """Tests for GapStore."""

    def test_create_concept_from_gap(self, graph, learner, outcome):
        """Test creating concept from identified gap."""
        store = GapStore(graph)
        gap = GapIdentified(
            name="handling-objections",
            display_name="Handling Objections",
            description="How to respond when clients push back on price",
            blocking_outcome_id=outcome.id,
        )

        concept = store.create_concept_from_gap(gap, learner.id, outcome.id)

        assert concept.id
        assert concept.name == "handling-objections"
        assert concept.display_name == "Handling Objections"
        assert concept.learner_id == learner.id
        assert concept.status == ConceptStatus.IDENTIFIED

    def test_link_gap_to_outcome(self, graph, learner, outcome):
        """Test linking gap concept to outcome."""
        store = GapStore(graph)
        gap = GapIdentified(
            name="value-pricing",
            display_name="Value Pricing",
            description="Pricing based on value delivered",
        )

        concept = store.create_concept_from_gap(gap, learner.id, outcome.id)

        # Verify edge was created
        edges = graph.get_edges_to(concept.id, edge_type=EdgeType.REQUIRES)
        assert len(edges) == 1
        assert edges[0].from_id == outcome.id

    def test_update_gap_status(self, graph, learner, outcome):
        """Test updating gap status."""
        store = GapStore(graph)
        gap = GapIdentified(
            name="test-gap",
            display_name="Test Gap",
            description="A test gap",
        )

        concept = store.create_concept_from_gap(gap, learner.id)
        assert concept.status == ConceptStatus.IDENTIFIED

        updated = store.mark_teaching_started(concept.id)
        assert updated.status == ConceptStatus.TEACHING

        understood = store.mark_understood(concept.id)
        assert understood.status == ConceptStatus.UNDERSTOOD

    def test_get_unresolved_gaps(self, graph, learner, outcome):
        """Test getting unresolved gaps."""
        store = GapStore(graph)

        # Create two gaps
        gap1 = GapIdentified(
            name="gap-1",
            display_name="Gap 1",
            description="First gap",
        )
        gap2 = GapIdentified(
            name="gap-2",
            display_name="Gap 2",
            description="Second gap",
        )

        c1 = store.create_concept_from_gap(gap1, learner.id, outcome.id)
        c2 = store.create_concept_from_gap(gap2, learner.id, outcome.id)

        # Mark one as understood
        store.mark_understood(c1.id)

        unresolved = store.get_unresolved_gaps(outcome.id)
        assert len(unresolved) == 1
        assert unresolved[0].id == c2.id

    def test_find_existing_gap(self, graph, learner):
        """Test finding existing gap by name."""
        store = GapStore(graph)
        gap = GapIdentified(
            name="unique-gap",
            display_name="Unique Gap",
            description="A unique gap",
        )

        store.create_concept_from_gap(gap, learner.id)

        # Should find existing
        found = store.find_existing_gap("unique-gap", learner.id)
        assert found is not None
        assert found.name == "unique-gap"

        # Should not find non-existent
        not_found = store.find_existing_gap("other-gap", learner.id)
        assert not_found is None

    def test_create_or_update_gap(self, graph, learner, outcome):
        """Test create or update gap logic."""
        store = GapStore(graph)
        gap = GapIdentified(
            name="dedup-gap",
            display_name="Dedup Gap",
            description="Test deduplication",
        )

        # First create
        c1 = store.create_or_update_gap(gap, learner.id, outcome.id)
        assert c1.id

        # Second create should return same concept
        c2 = store.create_or_update_gap(gap, learner.id, outcome.id)
        assert c2.id == c1.id


# =============================================================================
# Connection Finder Tests
# =============================================================================


class TestConnectionFinder:
    """Tests for ConnectionFinder."""

    def test_persist_discovered_connection(self, graph, learner):
        """Test persisting a discovered connection."""
        finder = ConnectionFinder(graph)

        # Create two concepts
        c1 = graph.create_concept_obj(
            Concept(
                id=str(uuid4()),
                name="concept-1",
                display_name="Concept 1",
                description="First concept",
                learner_id=learner.id,
                status=ConceptStatus.UNDERSTOOD,
            )
        )
        c2 = graph.create_concept_obj(
            Concept(
                id=str(uuid4()),
                name="concept-2",
                display_name="Concept 2",
                description="Second concept",
                learner_id=learner.id,
                status=ConceptStatus.IDENTIFIED,
            )
        )

        connection = ConnectionDiscovered(
            from_concept_id=c1.id,
            to_concept_id=c2.id,
            relationship="builds_on",
            strength=0.8,
            used_in_teaching=True,
        )

        edge = finder.persist_discovered_connection(connection)

        assert edge.id
        assert edge.edge_type == "relates_to"
        assert edge.metadata["relationship"] == "builds_on"
        assert edge.metadata["strength"] == 0.8

    def test_connection_exists(self, graph, learner):
        """Test checking if connection exists."""
        finder = ConnectionFinder(graph)

        # Create concepts
        c1 = graph.create_concept_obj(
            Concept(
                id=str(uuid4()),
                name="c1",
                display_name="C1",
                description="Concept 1",
                learner_id=learner.id,
            )
        )
        c2 = graph.create_concept_obj(
            Concept(
                id=str(uuid4()),
                name="c2",
                display_name="C2",
                description="Concept 2",
                learner_id=learner.id,
            )
        )

        # No connection yet
        assert not finder.connection_exists(c1.id, c2.id)

        # Create connection
        connection = ConnectionDiscovered(
            from_concept_id=c1.id,
            to_concept_id=c2.id,
            relationship="similar_to",
            strength=0.7,
        )
        finder.persist_discovered_connection(connection)

        # Should now exist
        assert finder.connection_exists(c1.id, c2.id)
        # Should also work in reverse
        assert finder.connection_exists(c2.id, c1.id)

    def test_create_or_update_connection(self, graph, learner):
        """Test create or update connection logic."""
        finder = ConnectionFinder(graph)

        c1 = graph.create_concept_obj(
            Concept(
                id=str(uuid4()),
                name="conn-c1",
                display_name="Conn C1",
                description="Connection concept 1",
                learner_id=learner.id,
            )
        )
        c2 = graph.create_concept_obj(
            Concept(
                id=str(uuid4()),
                name="conn-c2",
                display_name="Conn C2",
                description="Connection concept 2",
                learner_id=learner.id,
            )
        )

        # First connection
        conn1 = ConnectionDiscovered(
            from_concept_id=c1.id,
            to_concept_id=c2.id,
            relationship="builds_on",
            strength=0.5,
            used_in_teaching=False,
        )
        edge1 = finder.create_or_update_connection(conn1)

        # Second connection with same concepts but higher strength
        conn2 = ConnectionDiscovered(
            from_concept_id=c1.id,
            to_concept_id=c2.id,
            relationship="builds_on",
            strength=0.9,
            used_in_teaching=True,
        )
        edge2 = finder.create_or_update_connection(conn2)

        # Should be same edge but updated
        assert edge2.id == edge1.id
        assert edge2.metadata["strength"] == 0.9
        assert edge2.metadata["used_in_teaching"] is True


class TestConnectionPromptHints:
    """Tests for connection prompt hint generation."""

    def test_get_connection_hints_empty(self):
        """Test hints with no connections."""
        hints = get_connection_hints_for_prompt([])
        assert hints == ""

    def test_get_connection_hints_with_candidates(self):
        """Test hints with connection candidates."""
        candidates = [
            ConnectionCandidate(
                concept_id="c1",
                concept_name="basic-pricing",
                display_name="Basic Pricing",
                relationship="builds_on",
                strength=0.8,
                has_proof=True,
                teaching_hook="This builds on Basic Pricing, which you already understand.",
            ),
            ConnectionCandidate(
                concept_id="c2",
                concept_name="negotiation",
                display_name="Negotiation",
                relationship="similar_to",
                strength=0.6,
                has_proof=False,
                teaching_hook="This relates to Negotiation.",
            ),
        ]
        hints = get_connection_hints_for_prompt(candidates)

        assert "Connections to Leverage" in hints
        assert "Basic Pricing" in hints
        assert "proven" in hints
        assert "Teaching hook" in hints


# =============================================================================
# Gap Finder Integration Tests
# =============================================================================


class TestGapFinder:
    """Integration tests for GapFinder."""

    def test_create_gap_finder(self, graph):
        """Test creating a gap finder."""
        finder = create_gap_finder(graph)

        assert isinstance(finder, GapFinder)
        assert finder.gap_store is not None
        assert finder.connection_finder is not None
        assert finder.probing_generator is not None

    def test_process_response_with_gap(self, graph, learner, outcome):
        """Test processing response with gap identified."""
        finder = GapFinder(graph)

        response = SAGEResponse(
            message="I see the gap - you're struggling with objection handling.",
            current_mode=DialogueMode.PROBING,
            gap_identified=GapIdentified(
                name="objection-handling",
                display_name="Objection Handling",
                description="Responding to pricing objections",
                blocking_outcome_id=outcome.id,
            ),
        )

        result = finder.process_response(response, learner.id, outcome.id)

        assert result.gap_created is not None
        assert result.gap_created.name == "objection-handling"
        assert len(result.errors) == 0

    def test_process_response_with_connection(self, graph, learner):
        """Test processing response with connection discovered."""
        finder = GapFinder(graph)

        # Create concepts first
        c1 = graph.create_concept_obj(
            Concept(
                id=str(uuid4()),
                name="concept-a",
                display_name="Concept A",
                description="First concept",
                learner_id=learner.id,
            )
        )
        c2 = graph.create_concept_obj(
            Concept(
                id=str(uuid4()),
                name="concept-b",
                display_name="Concept B",
                description="Second concept",
                learner_id=learner.id,
            )
        )

        response = SAGEResponse(
            message="This connects to what you learned about Concept A.",
            current_mode=DialogueMode.TEACHING,
            connection_discovered=ConnectionDiscovered(
                from_concept_id=c1.id,
                to_concept_id=c2.id,
                relationship="builds_on",
                strength=0.75,
                used_in_teaching=True,
            ),
        )

        result = finder.process_response(response, learner.id)

        assert result.connection_created is not None
        assert len(result.errors) == 0

    def test_process_response_with_both(self, graph, learner, outcome):
        """Test processing response with gap and connection."""
        finder = GapFinder(graph)

        # Create a concept to connect to
        existing = graph.create_concept_obj(
            Concept(
                id=str(uuid4()),
                name="existing-concept",
                display_name="Existing Concept",
                description="Something they know",
                learner_id=learner.id,
                status=ConceptStatus.UNDERSTOOD,
            )
        )

        gap = GapIdentified(
            name="new-gap",
            display_name="New Gap",
            description="A new gap",
        )

        # First process gap
        response1 = SAGEResponse(
            message="Found a gap",
            current_mode=DialogueMode.PROBING,
            gap_identified=gap,
        )
        result1 = finder.process_response(response1, learner.id, outcome.id)
        new_concept = result1.gap_created

        # Then process connection
        response2 = SAGEResponse(
            message="This connects to what you know",
            current_mode=DialogueMode.TEACHING,
            connection_discovered=ConnectionDiscovered(
                from_concept_id=existing.id,
                to_concept_id=new_concept.id,
                relationship="builds_on",
                strength=0.8,
                used_in_teaching=True,
            ),
        )
        result2 = finder.process_response(response2, learner.id)

        assert result1.gap_created is not None
        assert result2.connection_created is not None

    def test_start_and_complete_teaching(self, graph, learner, outcome):
        """Test the teaching lifecycle for a gap."""
        finder = GapFinder(graph)

        # Create gap
        gap = GapIdentified(
            name="lifecycle-gap",
            display_name="Lifecycle Gap",
            description="Testing the lifecycle",
        )
        response = SAGEResponse(
            message="Found gap",
            current_mode=DialogueMode.PROBING,
            gap_identified=gap,
        )
        result = finder.process_response(response, learner.id, outcome.id)
        concept = result.gap_created

        assert concept.status == ConceptStatus.IDENTIFIED

        # Start teaching
        teaching = finder.start_teaching_gap(concept.id)
        assert teaching.status == ConceptStatus.TEACHING

        # Should be current gap
        current = finder.get_current_gap(outcome.id)
        assert current.id == concept.id

        # Mark understood
        understood = finder.mark_gap_understood(concept.id)
        assert understood.status == ConceptStatus.UNDERSTOOD

        # No more current gap
        current = finder.get_current_gap(outcome.id)
        assert current is None

    def test_has_more_gaps(self, graph, learner, outcome):
        """Test checking for more gaps."""
        finder = GapFinder(graph)

        # Initially no gaps
        assert not finder.has_more_gaps(outcome.id)

        # Add a gap
        gap = GapIdentified(
            name="more-gaps-test",
            display_name="More Gaps Test",
            description="Testing has_more_gaps",
        )
        response = SAGEResponse(
            message="Found gap",
            current_mode=DialogueMode.PROBING,
            gap_identified=gap,
        )
        result = finder.process_response(response, learner.id, outcome.id)

        # Now has gaps
        assert finder.has_more_gaps(outcome.id)

        # Mark understood
        finder.mark_gap_understood(result.gap_created.id)

        # No more gaps
        assert not finder.has_more_gaps(outcome.id)

    def test_get_probing_prompt_hints(self, graph, probing_context):
        """Test getting probing prompt hints."""
        finder = GapFinder(graph)
        hints = finder.get_probing_prompt_hints(probing_context)

        assert "Probing Guidance" in hints

    def test_find_teaching_connections(self, graph, learner):
        """Test finding connections for teaching."""
        finder = GapFinder(graph)

        # Create concepts with connection
        c1 = graph.create_concept_obj(
            Concept(
                id=str(uuid4()),
                name="known-concept",
                display_name="Known Concept",
                description="Something they know",
                learner_id=learner.id,
                status=ConceptStatus.UNDERSTOOD,
            )
        )
        c2 = graph.create_concept_obj(
            Concept(
                id=str(uuid4()),
                name="teaching-concept",
                display_name="Teaching Concept",
                description="What we're teaching",
                learner_id=learner.id,
                status=ConceptStatus.TEACHING,
            )
        )

        # Create proof for c1
        from sage.graph.models import DemoType, ProofExchange
        proof = Proof(
            id=str(uuid4()),
            concept_id=c1.id,
            learner_id=learner.id,
            session_id=str(uuid4()),
            demonstration_type=DemoType.EXPLANATION,
            evidence="Explained it well",
            confidence=0.85,
            exchange=ProofExchange(
                prompt="What is concept 1?",
                response="It's the first concept.",
                analysis="Learner demonstrated understanding."
            ),
        )
        graph.create_proof_obj(proof)

        # Create connection
        edge = Edge(
            id=str(uuid4()),
            from_id=c1.id,
            from_type="concept",
            to_id=c2.id,
            to_type="concept",
            edge_type="relates_to",
            metadata={"relationship": "builds_on", "strength": 0.8},
        )
        graph.create_edge(edge)

        # Find connections
        connections = finder.find_teaching_connections(c2.id, learner.id)

        assert len(connections) == 1
        assert connections[0].concept_id == c1.id
        assert connections[0].has_proof is True


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestGapFinderErrors:
    """Tests for error handling."""

    def test_process_response_handles_invalid_concept_id(self, graph, learner):
        """Test handling invalid concept ID in connection."""
        finder = GapFinder(graph)

        response = SAGEResponse(
            message="Connection to non-existent concept",
            current_mode=DialogueMode.TEACHING,
            connection_discovered=ConnectionDiscovered(
                from_concept_id="non-existent-1",
                to_concept_id="non-existent-2",
                relationship="builds_on",
                strength=0.5,
            ),
        )

        # Should handle gracefully, not crash
        result = finder.process_response(response, learner.id)
        # Connection should still be created (edge storage doesn't validate IDs)
        # But this isn't ideal - future improvement could add validation
        assert result.connection_created is not None or len(result.errors) > 0

    def test_update_nonexistent_gap(self, graph):
        """Test updating a gap that doesn't exist."""
        store = GapStore(graph)

        result = store.update_gap_status("nonexistent-id", ConceptStatus.TEACHING)
        assert result is None
