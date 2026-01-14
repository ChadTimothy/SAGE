"""LearnerInsights tracking - learns patterns about learners over time.

This module tracks what works for each learner and updates insights
based on session outcomes.
"""

from collections import defaultdict
from datetime import datetime
from typing import Optional

from sage.graph.learning_graph import LearningGraph
from sage.graph.models import (
    EnergyLevel,
    Learner,
    LearnerInsights,
    Session,
)


class InsightsTracker:
    """Tracks and updates learner insights over time."""

    def __init__(self, graph: LearningGraph):
        """Initialize with a LearningGraph instance."""
        self.graph = graph

    def update_after_session(
        self,
        learner: Learner,
        session: Session,
    ) -> LearnerInsights:
        """Update insights based on session results.

        Args:
            learner: The learner
            session: The completed session

        Returns:
            Updated LearnerInsights
        """
        insights = learner.insights

        # Track what conditions led to good learning
        if session.proofs_earned:
            insights = self._track_successful_conditions(insights, session)

        # Track confusion patterns
        confusion_count = self._count_confusion_signals(session)
        if confusion_count > 2:
            insights = self._track_struggle_conditions(insights, session)

        # Track session length patterns
        insights = self._track_session_length(insights, session)

        # Track effective approaches from proofs
        insights = self._track_teaching_approaches(insights, session)

        # Save updated insights
        learner.insights = insights
        self.graph.update_learner(learner)

        return insights

    def _track_successful_conditions(
        self,
        insights: LearnerInsights,
        session: Session,
    ) -> LearnerInsights:
        """Track conditions that led to proofs being earned."""
        if not session.context:
            return insights

        ctx = session.context

        # Track energy level success
        if ctx.energy == EnergyLevel.HIGH:
            if "Productive when high energy" not in insights.patterns:
                insights.patterns.append("Productive when high energy")

        # Track time availability
        if ctx.time_available:
            time_lower = ctx.time_available.lower()
            if "open" in time_lower or "hour" in time_lower:
                if "Deep work possible with open time" not in insights.patterns:
                    insights.patterns.append("Deep work possible with open time")

        # Infer best energy level
        if ctx.energy and len(session.proofs_earned) > 0:
            # Update best energy level if this session was productive
            if not insights.best_energy_level:
                insights.best_energy_level = ctx.energy.value
            elif len(session.proofs_earned) >= 2:
                # Multiple proofs = likely good energy state
                insights.best_energy_level = ctx.energy.value

        return insights

    def _track_struggle_conditions(
        self,
        insights: LearnerInsights,
        session: Session,
    ) -> LearnerInsights:
        """Track conditions that led to struggles."""
        if not session.context:
            return insights

        ctx = session.context

        # Track low energy struggles
        if ctx.energy == EnergyLevel.LOW:
            pattern = "Struggles when low energy—keep it light"
            if pattern not in insights.patterns:
                insights.patterns.append(pattern)

        # Track time pressure struggles
        if ctx.time_available:
            time_lower = ctx.time_available.lower()
            if any(t in time_lower for t in ["15", "short", "quick"]):
                pattern = "Time pressure leads to confusion"
                if pattern not in insights.patterns:
                    insights.patterns.append(pattern)

        return insights

    def _track_session_length(
        self,
        insights: LearnerInsights,
        session: Session,
    ) -> LearnerInsights:
        """Track optimal session length patterns."""
        if not session.ended_at:
            return insights

        duration_minutes = (session.ended_at - session.started_at).total_seconds() / 60

        # Track if productive sessions have a pattern
        if session.proofs_earned and len(session.proofs_earned) >= 1:
            # Simple heuristic for optimal length
            if 30 <= duration_minutes <= 60:
                insights.optimal_session_length = "30-60 minutes"
            elif duration_minutes < 30:
                if not insights.optimal_session_length:
                    insights.optimal_session_length = "Quick sessions (<30 min)"
            else:
                if not insights.optimal_session_length:
                    insights.optimal_session_length = "Longer sessions (60+ min)"

        return insights

    def _track_teaching_approaches(
        self,
        insights: LearnerInsights,
        session: Session,
    ) -> LearnerInsights:
        """Track which teaching approaches led to proofs."""
        if not session.proofs_earned:
            return insights

        # Get proofs from this session
        for proof_id in session.proofs_earned:
            proof = self.graph.get_proof(proof_id)
            if proof and proof.exchange:
                # Infer approach from the exchange
                approach = self._infer_approach(proof.exchange.prompt)
                if approach and approach not in insights.effective_approaches:
                    insights.effective_approaches.append(approach)

        return insights

    def _infer_approach(self, prompt: str) -> Optional[str]:
        """Infer teaching approach from verification prompt."""
        prompt_lower = prompt.lower()

        if "scenario" in prompt_lower or "imagine" in prompt_lower:
            return "Scenario-based questions"
        if "explain" in prompt_lower and "why" in prompt_lower:
            return "Explanation-focused"
        if "example" in prompt_lower:
            return "Example-driven"
        if "apply" in prompt_lower or "how would you" in prompt_lower:
            return "Application-focused"

        return None

    def _count_confusion_signals(self, session: Session) -> int:
        """Count confusion signals in a session.

        Looks for patterns in messages that indicate confusion.
        """
        confusion_count = 0
        confusion_indicators = [
            "i don't understand",
            "i'm confused",
            "what do you mean",
            "can you repeat",
            "i'm not sure",
            "that doesn't make sense",
            "wait, what",
            "huh?",
            "lost me",
        ]

        for msg in session.messages:
            if msg.role == "user":
                msg_lower = msg.content.lower()
                if any(ind in msg_lower for ind in confusion_indicators):
                    confusion_count += 1

        return confusion_count

    def add_pattern(
        self,
        learner_id: str,
        pattern: str,
    ) -> None:
        """Add a pattern observation about a learner.

        Args:
            learner_id: The learner's ID
            pattern: The pattern to add (e.g., "Responds well to analogies")
        """
        learner = self.graph.get_learner(learner_id)
        if not learner:
            raise ValueError(f"Learner not found: {learner_id}")

        if pattern not in learner.insights.patterns:
            learner.insights.patterns.append(pattern)
            self.graph.update_learner(learner)

    def add_effective_approach(
        self,
        learner_id: str,
        approach: str,
    ) -> None:
        """Add an effective teaching approach for a learner.

        Args:
            learner_id: The learner's ID
            approach: The approach (e.g., "Socratic questioning")
        """
        learner = self.graph.get_learner(learner_id)
        if not learner:
            raise ValueError(f"Learner not found: {learner_id}")

        if approach not in learner.insights.effective_approaches:
            learner.insights.effective_approaches.append(approach)
            self.graph.update_learner(learner)

    def add_ineffective_approach(
        self,
        learner_id: str,
        approach: str,
    ) -> None:
        """Mark a teaching approach as ineffective for a learner.

        Args:
            learner_id: The learner's ID
            approach: The approach that didn't work
        """
        learner = self.graph.get_learner(learner_id)
        if not learner:
            raise ValueError(f"Learner not found: {learner_id}")

        if approach not in learner.insights.ineffective_approaches:
            learner.insights.ineffective_approaches.append(approach)
            self.graph.update_learner(learner)

    def update_preferences(
        self,
        learner_id: str,
        prefers_examples: Optional[bool] = None,
        prefers_theory_first: Optional[bool] = None,
        needs_frequent_checks: Optional[bool] = None,
        responds_to_challenge: Optional[bool] = None,
    ) -> LearnerInsights:
        """Update learner preferences based on observations.

        Args:
            learner_id: The learner's ID
            prefers_examples: Whether they prefer concrete examples
            prefers_theory_first: Whether they want theory before how-to
            needs_frequent_checks: Whether they need more verification
            responds_to_challenge: Whether they rise to challenges

        Returns:
            Updated LearnerInsights
        """
        learner = self.graph.get_learner(learner_id)
        if not learner:
            raise ValueError(f"Learner not found: {learner_id}")

        insights = learner.insights

        if prefers_examples is not None:
            insights.prefers_examples = prefers_examples
        if prefers_theory_first is not None:
            insights.prefers_theory_first = prefers_theory_first
        if needs_frequent_checks is not None:
            insights.needs_frequent_checks = needs_frequent_checks
        if responds_to_challenge is not None:
            insights.responds_to_challenge = responds_to_challenge

        learner.insights = insights
        self.graph.update_learner(learner)

        return insights


def detect_application_patterns(
    graph: LearningGraph,
    learner_id: str,
) -> list[str]:
    """Find recurring struggles or successes in applications.

    Args:
        graph: The LearningGraph instance
        learner_id: The learner's ID

    Returns:
        List of detected patterns
    """
    from sage.graph.models import ApplicationStatus

    apps = graph.get_application_events_by_learner(learner_id)
    completed = [a for a in apps if a.status == ApplicationStatus.COMPLETED]

    # Group by struggle type
    struggles: dict[str, list] = defaultdict(list)
    successes: dict[str, list] = defaultdict(list)

    for app in completed:
        if app.what_struggled:
            struggles[app.what_struggled].append(app)
        if app.what_worked:
            successes[app.what_worked].append(app)

    patterns = []

    # Find recurring struggles
    for struggle, apps_list in struggles.items():
        if len(apps_list) >= 2:
            patterns.append(
                f"Recurring struggle: '{struggle}' in {len(apps_list)} situations"
            )

    # Find consistent successes
    for success, apps_list in successes.items():
        if len(apps_list) >= 2:
            patterns.append(
                f"Consistent success: '{success}' in {len(apps_list)} situations"
            )

    return patterns
