"""SAGE Gap Finder Module.

This module implements gap discovery and management:
- Probing question generation
- Gap identification and persistence
- Connection discovery between concepts

Usage:
    from sage.gaps import GapFinder, create_gap_finder

    # Create gap finder
    gap_finder = create_gap_finder(graph)

    # Build probing context
    probing_context = gap_finder.build_probing_context(full_context)

    # Generate probing question
    question = gap_finder.generate_probing_question(probing_context)

    # Process SAGEResponse for gaps
    result = gap_finder.process_response(response, learner_id, outcome_id)

    # Find connections for teaching
    connections = gap_finder.find_teaching_connections(concept_id, learner_id)
"""

from sage.gaps.connections import (
    ConnectionCandidate,
    ConnectionFinder,
    get_connection_hints_for_prompt,
)
from sage.gaps.gap_finder import (
    GapFinder,
    GapFinderResult,
    create_gap_finder,
)
from sage.gaps.gap_store import GapStore
from sage.gaps.probing import (
    ProbingContext,
    ProbingQuestion,
    ProbingQuestionGenerator,
    ProbingStrategy,
    get_probing_hints_for_prompt,
)


__all__ = [
    # Main interface
    "GapFinder",
    "GapFinderResult",
    "create_gap_finder",
    # Gap storage
    "GapStore",
    # Probing
    "ProbingContext",
    "ProbingQuestion",
    "ProbingQuestionGenerator",
    "ProbingStrategy",
    "get_probing_hints_for_prompt",
    # Connections
    "ConnectionCandidate",
    "ConnectionFinder",
    "get_connection_hints_for_prompt",
]
