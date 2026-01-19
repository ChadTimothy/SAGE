"""Practice/roleplay MCP tools for SAGE.

These tools enable interactive practice scenarios.
"""

import logging
from typing import Any

from sage.core.config import get_settings
from sage.graph.learning_graph import LearningGraph
from sage.graph.models import PracticeScenario, SessionType

logger = logging.getLogger(__name__)


def _get_default_graph() -> LearningGraph:
    """Get default learning graph instance."""
    settings = get_settings()
    return LearningGraph(settings.db_path)


async def sage_practice_start(
    session_id: str,
    concept_id: str | None = None,
    scenario_type: str = "realistic",
    graph: LearningGraph | None = None,
) -> dict[str, Any]:
    """Start a practice/roleplay session.

    Practice mode lets you apply what you've learned in
    realistic scenarios with feedback.

    Args:
        session_id: Current session ID
        concept_id: Optional specific concept to practice
        scenario_type: Type of scenario - "realistic" (default), "challenging", or "gentle"
        graph: Optional LearningGraph instance (uses default if not provided)

    Returns:
        dict with:
            - practice_id: ID of the practice session
            - scenario: The practice scenario description
            - your_role: Your role in the scenario
            - objective: What you need to accomplish
    """
    if graph is None:
        graph = _get_default_graph()
    session = graph.get_session(session_id)

    if not session:
        return {"error": "Session not found"}

    # Get learner for context
    learner = graph.get_learner(session.learner_id)
    if not learner:
        return {"error": "Learner not found"}

    # If no concept specified, find a recent one
    target_concept = None
    if concept_id:
        target_concept = graph.get_concept(concept_id)
    else:
        concepts = graph.get_concepts_by_learner(session.learner_id)
        if concepts:
            target_concept = concepts[0]

    if not target_concept:
        return {
            "error": "No concept found to practice",
            "suggestion": "Learn something first, then come back to practice!",
        }

    # Generate practice scenario (simplified - full implementation uses LLM)
    import uuid
    practice_id = f"practice_{uuid.uuid4().hex[:8]}"

    # Store practice state using proper PracticeScenario model
    session.session_type = SessionType.PRACTICE
    session.practice_scenario = PracticeScenario(
        scenario_id=practice_id,
        title=f"Practice: {target_concept.display_name}",
        description=f"Apply your understanding of {target_concept.display_name}",
        sage_role="Coach providing feedback",
        user_role="Learner demonstrating understanding",
        related_concepts=[target_concept.id],
    )
    graph.update_session(session)

    return {
        "practice_id": practice_id,
        "concept": target_concept.display_name,
        "scenario": f"Let's practice applying {target_concept.display_name}. I'll set up a realistic situation and you tell me how you'd handle it.",
        "your_role": "You",
        "objective": f"Demonstrate your understanding of {target_concept.display_name}",
        "tips": [
            "Think through the situation before responding",
            "Apply what you learned",
            "I'll give you feedback after",
        ],
    }


async def sage_practice_scenario(
    session_id: str,
    practice_id: str,
    response: str,
    graph: LearningGraph | None = None,
) -> dict[str, Any]:
    """Respond to a practice scenario.

    Submit your response to the current practice scenario
    to receive feedback and potentially a new challenge.

    Args:
        session_id: Current session ID
        practice_id: The practice session ID
        response: Your response to the scenario
        graph: Optional LearningGraph instance (uses default if not provided)

    Returns:
        dict with:
            - feedback: Feedback on your response
            - score: How well you did (0-100)
            - areas_good: What you did well
            - areas_improve: What could be better
            - next_challenge: Optional follow-up challenge
    """
    if graph is None:
        graph = _get_default_graph()
    session = graph.get_session(session_id)

    if not session:
        return {"error": "Session not found"}

    # Verify practice session
    if not session.practice_scenario or session.practice_scenario.scenario_id != practice_id:
        return {"error": "Practice session not found or expired"}

    # Simplified feedback (full implementation uses LLM)
    # Basic analysis of response length and keywords
    response_length = len(response.split())

    areas_good = []
    areas_improve = []
    score = 70  # Base score

    if response_length > 20:
        areas_good.append("Thorough response with good detail")
        score += 10
    elif response_length < 5:
        areas_improve.append("Try to provide more detail in your response")
        score -= 10

    if "?" in response:
        areas_good.append("Good use of questions to clarify")
        score += 5

    # Cap score
    score = max(0, min(100, score))

    return {
        "feedback": "Nice effort! Here's what I noticed about your response.",
        "score": score,
        "areas_good": areas_good if areas_good else ["Solid attempt"],
        "areas_improve": areas_improve if areas_improve else ["Keep practicing!"],
    }


async def sage_practice_feedback(
    session_id: str,
    practice_id: str,
    self_assessment: str | None = None,
    graph: LearningGraph | None = None,
) -> dict[str, Any]:
    """Complete a practice session and get final feedback.

    End the practice session and receive comprehensive
    feedback on your performance.

    Args:
        session_id: Current session ID
        practice_id: The practice session ID
        self_assessment: Optional self-reflection on how you did
        graph: Optional LearningGraph instance (uses default if not provided)

    Returns:
        dict with:
            - summary: Overall summary of performance
            - key_learnings: Main takeaways
            - next_steps: Suggested next steps
            - practice_complete: Whether practice is complete
    """
    if graph is None:
        graph = _get_default_graph()
    session = graph.get_session(session_id)

    if not session:
        return {"error": "Session not found"}

    # Verify practice session
    if not session.practice_scenario or session.practice_scenario.scenario_id != practice_id:
        return {"error": "Practice session not found"}

    # Get concept for feedback
    concept_name = "the concept"
    if session.practice_scenario.related_concepts:
        concept = graph.get_concept(session.practice_scenario.related_concepts[0])
        if concept:
            concept_name = concept.display_name

    # Clear practice state
    session.practice_scenario = None
    session.session_type = SessionType.LEARNING
    graph.update_session(session)

    return {
        "summary": f"Great work practicing {concept_name}!",
        "key_learnings": [
            f"You've reinforced your understanding of {concept_name}",
            "Practice builds confidence for real-world application",
        ],
        "next_steps": [
            "Try applying this in a real situation",
            "Come back to practice again to reinforce",
            "Move on to learn something new that builds on this",
        ],
        "practice_complete": True,
        "self_assessment_received": self_assessment is not None,
    }
