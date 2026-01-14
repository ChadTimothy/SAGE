"""Main Gap Finder module.

Coordinates probing, gap storage, and connection discovery
to find and fill learning gaps.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from sage.context.full_context import FullContext
from sage.context.snapshots import ConceptSnapshot
from sage.dialogue.structured_output import (
    ConnectionDiscovered,
    GapIdentified,
    SAGEResponse,
)
from sage.graph.learning_graph import LearningGraph
from sage.graph.models import Concept, ConceptStatus, Edge
from sage.graph.queries import GraphQueries

from .connections import ConnectionCandidate, ConnectionFinder, get_connection_hints_for_prompt
from .gap_store import GapStore
from .probing import (
    ProbingContext,
    ProbingQuestion,
    ProbingQuestionGenerator,
    get_probing_hints_for_prompt,
)


logger = logging.getLogger(__name__)


@dataclass
class GapFinderResult:
    """Result of processing a SAGEResponse for gaps."""

    gap_created: Optional[Concept] = None
    connection_created: Optional[Edge] = None
    concept_updated: Optional[Concept] = None
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class GapFinder:
    """Coordinates gap finding, storage, and connection discovery.

    Main interface for the gap finder module. Integrates with
    ConversationEngine to:
    - Generate probing guidance
    - Process identified gaps from SAGEResponse
    - Persist connections discovered during teaching
    - Track gap status through the learning cycle
    """

    def __init__(
        self,
        graph: LearningGraph,
        queries: Optional[GraphQueries] = None,
    ):
        """Initialize the gap finder.

        Args:
            graph: The learning graph
            queries: Optional GraphQueries instance
        """
        self.graph = graph
        self.queries = queries or GraphQueries(graph.store)

        self.gap_store = GapStore(graph)
        self.connection_finder = ConnectionFinder(graph, self.queries)
        self.probing_generator = ProbingQuestionGenerator()

    def build_probing_context(self, full_context: FullContext) -> ProbingContext:
        """Build probing context from full context.

        Args:
            full_context: The loaded full context

        Returns:
            ProbingContext for question generation
        """
        # Get proven concepts
        proven = []
        for proof in full_context.proven_concepts:
            concept = self.graph.get_concept(proof.concept_id)
            if concept:
                proven.append(
                    ConceptSnapshot(
                        id=concept.id,
                        name=concept.name,
                        display_name=concept.display_name,
                        description=concept.description,
                        summary=concept.summary,
                        status=concept.status.value,
                        proof_confidence=proof.confidence,
                    )
                )

        # Get concepts already explored in current session
        explored = []
        if full_context.last_session:
            explored = full_context.last_session.concepts_explored or []

        return ProbingContext(
            learner=full_context.learner_snapshot,
            outcome=full_context.active_outcome,
            session_context=None,  # Filled in at turn level
            proven_concepts=proven,
            concepts_explored=explored,
        )

    def generate_probing_question(
        self, probing_context: ProbingContext
    ) -> ProbingQuestion:
        """Generate an initial probing question.

        Args:
            probing_context: The probing context

        Returns:
            A probing question to start with
        """
        return self.probing_generator.generate_initial_probe(probing_context)

    def generate_followup_probe(
        self,
        probing_context: ProbingContext,
        previous_response: str,
        gap_hint: Optional[str] = None,
    ) -> ProbingQuestion:
        """Generate a follow-up probing question.

        Args:
            probing_context: The probing context
            previous_response: What the learner said
            gap_hint: Optional hint about where gap might be

        Returns:
            A follow-up probing question
        """
        return self.probing_generator.generate_followup_probe(
            probing_context, previous_response, gap_hint
        )

    def get_probing_prompt_hints(self, probing_context: ProbingContext) -> str:
        """Get probing hints to include in LLM prompt.

        Args:
            probing_context: The probing context

        Returns:
            Markdown hints for the prompt
        """
        return get_probing_hints_for_prompt(probing_context)

    def find_teaching_connections(
        self,
        concept_id: str,
        learner_id: str,
        max_connections: int = 5,
    ) -> list[ConnectionCandidate]:
        """Find connections for teaching a concept.

        Args:
            concept_id: The concept being taught
            learner_id: The learner
            max_connections: Max connections to return

        Returns:
            Connection candidates for teaching
        """
        return self.connection_finder.find_connections_for_teaching(
            concept_id, learner_id, max_connections
        )

    def get_connection_prompt_hints(
        self, candidates: list[ConnectionCandidate]
    ) -> str:
        """Get connection hints for LLM prompt.

        Args:
            candidates: Connection candidates found

        Returns:
            Markdown hints for the prompt
        """
        return get_connection_hints_for_prompt(candidates)

    def process_response(
        self,
        response: SAGEResponse,
        learner_id: str,
        outcome_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> GapFinderResult:
        """Process a SAGEResponse for gaps and connections.

        Extracts and persists:
        - gap_identified -> Creates concept linked to outcome
        - connection_discovered -> Creates relates_to edge

        Args:
            response: The SAGEResponse from the LLM
            learner_id: The learner ID
            outcome_id: Current outcome ID (optional)
            session_id: Current session ID (optional)

        Returns:
            Result with created/updated entities
        """
        result = GapFinderResult()

        # Process gap if identified
        if response.gap_identified:
            try:
                concept = self.gap_store.create_or_update_gap(
                    gap=response.gap_identified,
                    learner_id=learner_id,
                    outcome_id=outcome_id or response.gap_identified.blocking_outcome_id,
                    session_id=session_id,
                )
                result.gap_created = concept
                logger.info(f"Processed gap: {concept.display_name}")
            except Exception as e:
                error_msg = f"Failed to create gap: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        # Process connection if discovered
        if response.connection_discovered:
            try:
                edge = self.connection_finder.create_or_update_connection(
                    response.connection_discovered
                )
                result.connection_created = edge
                logger.info(
                    f"Processed connection: {response.connection_discovered.relationship}"
                )
            except Exception as e:
                error_msg = f"Failed to create connection: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        return result

    def start_teaching_gap(self, concept_id: str) -> Optional[Concept]:
        """Mark a gap as being taught.

        Called when transitioning from PROBING to TEACHING.

        Args:
            concept_id: The concept to start teaching

        Returns:
            The updated concept
        """
        return self.gap_store.mark_teaching_started(concept_id)

    def mark_gap_understood(self, concept_id: str) -> Optional[Concept]:
        """Mark a gap as understood.

        Called when a proof is earned for this concept.

        Args:
            concept_id: The concept that's now understood

        Returns:
            The updated concept
        """
        return self.gap_store.mark_understood(concept_id)

    def get_current_gap(self, outcome_id: str) -> Optional[Concept]:
        """Get the concept currently being taught.

        Args:
            outcome_id: The outcome ID

        Returns:
            Concept in TEACHING status, or None
        """
        return self.gap_store.get_current_gap(outcome_id)

    def get_unresolved_gaps(self, outcome_id: str) -> list[Concept]:
        """Get gaps not yet resolved for an outcome.

        Args:
            outcome_id: The outcome ID

        Returns:
            List of unresolved gaps
        """
        return self.gap_store.get_unresolved_gaps(outcome_id)

    def has_more_gaps(self, outcome_id: str) -> bool:
        """Check if there are more gaps to resolve.

        Args:
            outcome_id: The outcome ID

        Returns:
            True if unresolved gaps exist
        """
        return len(self.get_unresolved_gaps(outcome_id)) > 0


def create_gap_finder(graph: LearningGraph) -> GapFinder:
    """Factory function to create a GapFinder.

    Args:
        graph: The learning graph

    Returns:
        Configured GapFinder instance
    """
    return GapFinder(graph)
