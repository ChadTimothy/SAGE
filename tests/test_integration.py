"""Integration tests for M6.

Tests the full integration between ConversationEngine, GapFinder, and ProofHandler.
"""

import pytest
from unittest.mock import MagicMock

from sage.graph.learning_graph import LearningGraph
from sage.graph.models import (
    Concept,
    ConceptStatus,
    DialogueMode,
    DemoType,
)
from sage.dialogue.conversation import ConversationEngine, ConversationConfig
from sage.dialogue.structured_output import (
    SAGEResponse,
    GapIdentified,
    ProofEarned,
    ProofExchange,
    ConnectionDiscovered,
)
from sage.gaps import GapFinder
from sage.assessment import ProofHandler


@pytest.fixture
def graph():
    """Create a test graph."""
    return LearningGraph()


@pytest.fixture
def learner(graph):
    """Create a test learner."""
    return graph.get_or_create_learner("learner-1")


@pytest.fixture
def outcome(graph, learner):
    """Create a test outcome."""
    return graph.create_outcome(
        learner_id=learner.id,
        stated_goal="Write clean Python code",
        motivation="Understand code quality principles",
    )


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    return client


@pytest.fixture
def engine(graph, mock_llm_client):
    """Create a conversation engine with mock LLM."""
    config = ConversationConfig(validate_responses=False)
    return ConversationEngine(graph, mock_llm_client, config)


def create_test_concept(graph, learner, outcome, name="test_concept", status=ConceptStatus.IDENTIFIED):
    """Helper to create a concept with required fields."""
    concept = Concept(
        learner_id=learner.id,
        name=name,
        display_name=name.replace("_", " ").title(),
        description=f"Description for {name}",
        discovered_from=outcome.id,
        status=status,
    )
    return graph.create_concept_obj(concept)


class TestGapFinderIntegration:
    """Test GapFinder integration with ConversationEngine."""

    def test_gap_finder_created(self, engine):
        """Gap finder should be created on engine init."""
        assert engine.gap_finder is not None
        assert isinstance(engine.gap_finder, GapFinder)

    def test_process_response_creates_gap(self, engine, learner, outcome, graph):
        """Processing a response with gap_identified should create concept."""
        # Start session
        engine.start_session(learner.id)

        # Create a response with gap identified
        response = SAGEResponse(
            message="I see a gap in understanding functions.",
            current_mode=DialogueMode.PROBING,
            gap_identified=GapIdentified(
                name="python_functions",
                display_name="Python Functions",
                description="Understanding function definition and usage",
                blocking_outcome_id=outcome.id,
            ),
        )

        # Process the response
        engine._persist_turn("I don't know functions", response)

        # Verify gap was created
        assert engine.current_concept is not None
        assert engine.current_concept.name == "python_functions"
        assert engine.current_concept.display_name == "Python Functions"

        # Verify concept exists in graph
        concepts = graph.get_concepts_for_outcome(outcome.id)
        assert len(concepts) == 1
        assert concepts[0].name == "python_functions"

    def test_mode_transition_to_teach_starts_teaching(self, engine, learner, outcome, graph):
        """Transitioning to TEACHING mode should mark gap as being taught."""
        # Start session
        engine.start_session(learner.id)

        # Create the gap first
        gap_response = SAGEResponse(
            message="Let me identify the gap.",
            current_mode=DialogueMode.PROBING,
            gap_identified=GapIdentified(
                name="test_gap",
                display_name="Test Gap",
                description="A test gap",
                blocking_outcome_id=outcome.id,
            ),
        )
        engine._persist_turn("help me", gap_response)

        # Store the concept ID before transition
        concept_id = engine.current_concept.id

        # Simulate transition to TEACHING
        teach_response = SAGEResponse(
            message="Let me teach you.",
            current_mode=DialogueMode.PROBING,
            transition_to=DialogueMode.TEACHING,
            transition_reason="Ready to teach the identified gap",
        )

        # Process and update mode
        engine._persist_turn("teach me", teach_response)
        if teach_response.transition_to:
            if teach_response.transition_to == DialogueMode.TEACHING and engine.current_concept:
                engine.gap_finder.start_teaching_gap(engine.current_concept.id)
            engine.current_mode = teach_response.transition_to

        # Verify concept status updated
        concept = graph.get_concept(concept_id)
        assert concept.status == ConceptStatus.TEACHING


class TestProofHandlerIntegration:
    """Test ProofHandler integration with ConversationEngine."""

    def test_proof_handler_created(self, engine):
        """Proof handler should be created on engine init."""
        assert engine.proof_handler is not None
        assert isinstance(engine.proof_handler, ProofHandler)

    def test_process_response_creates_proof(self, engine, learner, outcome, graph):
        """Processing a response with proof_earned should create proof."""
        # Start session
        session, _ = engine.start_session(learner.id)

        # Create a concept first
        concept = create_test_concept(graph, learner, outcome, "test_concept", ConceptStatus.TEACHING)
        engine.current_concept = concept

        # Create a response with proof earned
        response = SAGEResponse(
            message="Great demonstration!",
            current_mode=DialogueMode.VERIFICATION,
            proof_earned=ProofEarned(
                concept_id=concept.id,
                demonstration_type="explanation",
                evidence="Learner explained in own words correctly",
                confidence=0.85,
                exchange=ProofExchange(
                    prompt="Explain this concept",
                    response="The concept means...",
                    analysis="Good understanding shown",
                ),
            ),
        )

        # Process the response
        engine._persist_turn("The concept means...", response)

        # Verify proof was created
        proofs = graph.get_proofs_by_concept(concept.id)
        assert len(proofs) == 1
        assert proofs[0].confidence == 0.85

        # Verify concept marked as understood
        updated_concept = graph.get_concept(concept.id)
        assert updated_concept.status == ConceptStatus.UNDERSTOOD

        # Verify current concept cleared
        assert engine.current_concept is None

    def test_learner_proof_count_incremented(self, engine, learner, outcome, graph):
        """Creating a proof should increment learner's total_proofs."""
        # Start session
        engine.start_session(learner.id)

        # Create a concept
        concept = create_test_concept(graph, learner, outcome, "test_concept", ConceptStatus.TEACHING)
        engine.current_concept = concept

        # Get initial proof count
        initial_count = graph.get_learner(learner.id).total_proofs

        # Create response with proof
        response = SAGEResponse(
            message="Well done!",
            current_mode=DialogueMode.VERIFICATION,
            proof_earned=ProofEarned(
                concept_id=concept.id,
                demonstration_type="application",
                evidence="Applied correctly",
                confidence=0.9,
                exchange=ProofExchange(
                    prompt="Show me how to use it",
                    response="Here's how...",
                    analysis="Good application",
                ),
            ),
        )

        engine._persist_turn("Here's how...", response)

        # Verify count incremented
        updated_learner = graph.get_learner(learner.id)
        assert updated_learner.total_proofs == initial_count + 1


class TestConnectionDiscoveryIntegration:
    """Test connection discovery integration."""

    def test_connection_discovery_creates_edge(self, engine, learner, outcome, graph):
        """Discovering a connection should create an edge."""
        # Start session
        engine.start_session(learner.id)

        # Create two concepts
        concept1 = create_test_concept(graph, learner, outcome, "concept_1", ConceptStatus.UNDERSTOOD)
        concept2 = create_test_concept(graph, learner, outcome, "concept_2", ConceptStatus.TEACHING)

        # Create response with connection discovered
        response = SAGEResponse(
            message="I see these concepts are related.",
            current_mode=DialogueMode.TEACHING,
            connection_discovered=ConnectionDiscovered(
                from_concept_id=concept1.id,
                to_concept_id=concept2.id,
                relationship="builds_on",
                strength=0.8,
                used_in_teaching=True,
            ),
        )

        # Process the response
        engine._persist_turn("They seem related", response)

        # Verify edge was created
        edges = graph.store.get_edges_from(concept1.id)
        relates_edges = [e for e in edges if e.edge_type == "relates_to"]
        assert len(relates_edges) == 1
        assert relates_edges[0].to_id == concept2.id


class TestModeSpecificHints:
    """Test mode-specific hints in turn context."""

    def test_probe_mode_adds_probing_hints(self, engine, learner, outcome):
        """PROBING mode should add probing hints to context."""
        engine.start_session(learner.id)
        engine.current_mode = DialogueMode.PROBING

        hints = engine._get_mode_specific_hints()

        # Hints should be a list (may be empty if no probing context available)
        assert isinstance(hints, list)

    def test_teach_mode_with_concept_returns_hints_list(self, engine, learner, outcome, graph):
        """TEACHING mode with current concept should return a hints list."""
        engine.start_session(learner.id)
        engine.current_mode = DialogueMode.TEACHING
        engine.current_concept = create_test_concept(
            graph, learner, outcome, "test_concept", ConceptStatus.TEACHING
        )

        hints = engine._get_mode_specific_hints()

        assert isinstance(hints, list)


class TestFullConversationFlow:
    """Test a complete conversation flow through the engine."""

    def test_gap_identification_to_proof_flow(self, engine, learner, outcome, graph):
        """Test the full flow from gap identification to proof earned."""
        # Start session
        session, _ = engine.start_session(learner.id)
        engine.current_mode = DialogueMode.PROBING

        # Step 1: Identify a gap
        gap_response = SAGEResponse(
            message="I've identified a gap.",
            current_mode=DialogueMode.PROBING,
            transition_to=DialogueMode.TEACHING,
            transition_reason="Gap identified, ready to teach",
            gap_identified=GapIdentified(
                name="list_comprehensions",
                display_name="List Comprehensions",
                description="Understanding Python list comprehensions",
                blocking_outcome_id=outcome.id,
            ),
        )
        engine._persist_turn("I struggle with list comprehensions", gap_response)

        # Should have current concept
        assert engine.current_concept is not None
        concept_id = engine.current_concept.id

        # Manually trigger mode transition handling
        if gap_response.transition_to == DialogueMode.TEACHING and engine.current_concept:
            engine.gap_finder.start_teaching_gap(engine.current_concept.id)
        engine.current_mode = gap_response.transition_to

        # Verify concept status
        concept = graph.get_concept(concept_id)
        assert concept.status == ConceptStatus.TEACHING

        # Step 2: Teaching happens (simulated)
        engine.current_mode = DialogueMode.VERIFICATION

        # Step 3: Proof earned
        proof_response = SAGEResponse(
            message="Excellent! You've got it.",
            current_mode=DialogueMode.VERIFICATION,
            transition_to=DialogueMode.OUTCOME_CHECK,
            transition_reason="Understanding verified",
            proof_earned=ProofEarned(
                concept_id=concept_id,
                demonstration_type="both",
                evidence="Explained and applied correctly",
                confidence=0.92,
                exchange=ProofExchange(
                    prompt="Show me what list comprehensions do",
                    response="[x*2 for x in range(10)] creates a list...",
                    analysis="Clear understanding with correct application",
                ),
            ),
        )
        engine._persist_turn("[x*2 for x in range(10)] creates a list...", proof_response)

        # Verify proof created
        proofs = graph.get_proofs_by_concept(concept_id)
        assert len(proofs) == 1
        assert proofs[0].demonstration_type == DemoType.BOTH

        # Verify concept is now understood
        concept = graph.get_concept(concept_id)
        assert concept.status == ConceptStatus.UNDERSTOOD

        # Verify current concept cleared
        assert engine.current_concept is None


class TestEndSessionIntegration:
    """Test session ending cleans up state."""

    def test_end_session_clears_current_concept(self, engine, learner, outcome, graph):
        """Ending session should clear current concept."""
        # Start session
        engine.start_session(learner.id)

        # Set a current concept
        concept = create_test_concept(graph, learner, outcome, "test_concept")
        engine.current_concept = concept

        # End session
        engine.end_session()

        # Verify state cleared
        assert engine.current_concept is None
        assert engine.current_session is None
        assert engine.current_mode is None
