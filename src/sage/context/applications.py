"""Application event lifecycle management.

This module handles the full lifecycle of application events:
- Detection of upcoming applications
- Follow-up tracking
- Processing outcomes
- Pattern recognition
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from sage.graph.learning_graph import LearningGraph
from sage.graph.models import (
    ApplicationEvent,
    ApplicationStatus,
    Concept,
    ConceptStatus,
    Edge,
    EdgeType,
)


@dataclass
class UpcomingApplication:
    """An application detected from conversation."""

    context: str  # "pricing call tomorrow"
    concept_ids: list[str]
    outcome_id: Optional[str]
    planned_date: Optional[date]
    stakes: Optional[str]  # high, medium, low


@dataclass
class FollowupResult:
    """Result from following up on an application."""

    outcome_result: str  # went_well, struggled, mixed
    what_worked: Optional[str]
    what_struggled: Optional[str]
    gaps_revealed: list[str]  # Names of new gaps identified
    learner_insight: Optional[str]  # Their own reflection


class ApplicationLifecycle:
    """Manages the lifecycle of application events."""

    def __init__(self, graph: LearningGraph):
        """Initialize with a LearningGraph instance."""
        self.graph = graph

    def create_application(
        self,
        learner_id: str,
        session_id: str,
        application: UpcomingApplication,
    ) -> ApplicationEvent:
        """Create a new application event.

        Args:
            learner_id: The learner's ID
            session_id: The session where this was detected
            application: The application details

        Returns:
            Created ApplicationEvent
        """
        event = ApplicationEvent(
            learner_id=learner_id,
            concept_ids=application.concept_ids,
            outcome_id=application.outcome_id,
            session_id=session_id,
            context=application.context,
            planned_date=application.planned_date,
            stakes=application.stakes,
            status=ApplicationStatus.UPCOMING,
        )

        event = self.graph.create_application_event_obj(event)

        # Create applied_in edges for each concept
        for concept_id in application.concept_ids:
            edge = Edge(
                from_id=concept_id,
                from_type="concept",
                to_id=event.id,
                to_type="application_event",
                edge_type=EdgeType.APPLIED_IN,
            )
            self.graph.create_edge(edge)

        return event

    def get_pending_followups(
        self,
        learner_id: str,
        as_of: Optional[date] = None,
    ) -> list[ApplicationEvent]:
        """Get applications that need follow-up.

        Args:
            learner_id: The learner's ID
            as_of: Date to check against (defaults to today)

        Returns:
            List of applications needing follow-up, sorted by urgency
        """
        check_date = as_of or date.today()
        all_apps = self.graph.get_application_events_by_learner(learner_id)

        pending = []
        for app in all_apps:
            # Already marked for followup
            if app.status == ApplicationStatus.PENDING_FOLLOWUP:
                pending.append(app)
            # Upcoming but planned date has passed
            elif app.status == ApplicationStatus.UPCOMING:
                if app.planned_date and app.planned_date <= check_date:
                    # Update status to pending followup
                    app.status = ApplicationStatus.PENDING_FOLLOWUP
                    self.graph.update_application_event(app)
                    pending.append(app)

        # Sort by planned_date (oldest first - most urgent)
        pending.sort(key=lambda a: a.planned_date or date.max)
        return pending

    def mark_for_followup(self, event_id: str) -> ApplicationEvent:
        """Mark an application event as needing follow-up.

        Args:
            event_id: The application event ID

        Returns:
            Updated ApplicationEvent
        """
        event = self.graph.get_application_event(event_id)
        if not event:
            raise ValueError(f"Application event not found: {event_id}")

        event.status = ApplicationStatus.PENDING_FOLLOWUP
        return self.graph.update_application_event(event)

    def complete_followup(
        self,
        event_id: str,
        session_id: str,
        result: FollowupResult,
    ) -> tuple[ApplicationEvent, list[Concept]]:
        """Complete a follow-up conversation.

        Args:
            event_id: The application event ID
            session_id: The session where follow-up happened
            result: The result of the follow-up

        Returns:
            Tuple of (updated ApplicationEvent, list of new Concepts from gaps)
        """
        event = self.graph.get_application_event(event_id)
        if not event:
            raise ValueError(f"Application event not found: {event_id}")

        # Update the event
        event.status = ApplicationStatus.COMPLETED
        event.followup_session_id = session_id
        event.followed_up_at = datetime.utcnow()
        event.outcome_result = result.outcome_result
        event.what_worked = result.what_worked
        event.what_struggled = result.what_struggled
        event.gaps_revealed = result.gaps_revealed
        event.insights = result.learner_insight

        event = self.graph.update_application_event(event)

        # Create concepts for revealed gaps
        new_concepts = []
        for gap_name in result.gaps_revealed:
            concept = Concept(
                learner_id=event.learner_id,
                name=gap_name.lower().replace(" ", "-"),
                display_name=gap_name,
                description=f"Gap revealed during: {event.context}",
                discovered_from=event.outcome_id,
                status=ConceptStatus.IDENTIFIED,
            )
            concept = self.graph.create_concept_obj(concept)
            new_concepts.append(concept)

            # Link to the application event
            edge = Edge(
                from_id=concept.id,
                from_type="concept",
                to_id=event.id,
                to_type="application_event",
                edge_type=EdgeType.APPLIED_IN,
                metadata={"revealed_by_struggle": True},
            )
            self.graph.create_edge(edge)

            # Link to outcome if specified
            if event.outcome_id:
                outcome_edge = Edge(
                    from_id=event.outcome_id,
                    from_type="outcome",
                    to_id=concept.id,
                    to_type="concept",
                    edge_type=EdgeType.REQUIRES,
                )
                self.graph.create_edge(outcome_edge)

        return event, new_concepts

    def skip_followup(
        self,
        event_id: str,
        reason: Optional[str] = None,
    ) -> ApplicationEvent:
        """Skip a follow-up (application didn't happen or not relevant).

        Args:
            event_id: The application event ID
            reason: Optional reason for skipping

        Returns:
            Updated ApplicationEvent
        """
        event = self.graph.get_application_event(event_id)
        if not event:
            raise ValueError(f"Application event not found: {event_id}")

        event.status = ApplicationStatus.SKIPPED
        if reason:
            event.insights = f"Skipped: {reason}"

        return self.graph.update_application_event(event)

    def get_applications_for_concept(
        self,
        concept_id: str,
    ) -> list[ApplicationEvent]:
        """Get all applications involving a concept.

        Args:
            concept_id: The concept ID

        Returns:
            List of applications using this concept
        """
        # Get the concept to find the learner
        concept = self.graph.get_concept(concept_id)
        if not concept:
            return []

        all_apps = self.graph.get_application_events_by_learner(concept.learner_id)
        return [app for app in all_apps if concept_id in app.concept_ids]

    def get_relevant_applications_for_teaching(
        self,
        concept_id: str,
        limit: int = 3,
    ) -> list[ApplicationEvent]:
        """Get completed applications relevant for teaching context.

        Args:
            concept_id: The concept being taught
            limit: Maximum number to return

        Returns:
            Most recent relevant completed applications
        """
        apps = self.get_applications_for_concept(concept_id)
        completed = [
            app for app in apps
            if app.status == ApplicationStatus.COMPLETED
        ]

        # Sort by most recent first
        completed.sort(
            key=lambda a: a.followed_up_at or a.created_at,
            reverse=True
        )

        return completed[:limit]


def generate_followup_prompt(event: ApplicationEvent) -> str:
    """Generate a natural follow-up prompt for an application.

    Args:
        event: The application event to follow up on

    Returns:
        Natural language prompt for SAGE to use
    """
    # Calculate how long ago the planned date was
    days_ago = ""
    if event.planned_date:
        delta = date.today() - event.planned_date
        if delta.days == 0:
            days_ago = "today"
        elif delta.days == 1:
            days_ago = "yesterday"
        elif delta.days < 7:
            days_ago = f"{delta.days} days ago"
        elif delta.days < 14:
            days_ago = "last week"
        else:
            days_ago = f"about {delta.days // 7} weeks ago"
    else:
        days_ago = "recently"

    # Build the prompt
    if event.stakes == "high":
        return f"Before we continue—you had that {event.context} {days_ago}. That sounded important. How did it go?"
    else:
        return f"Before we dive in—you mentioned you had a {event.context} {days_ago}. How did it go?"


def detect_application_in_message(
    message: str,
    current_concepts: list[str],
) -> Optional[UpcomingApplication]:
    """Detect if a message mentions an upcoming application.

    This is a simple keyword-based detection. The actual detection
    would be done by the LLM in practice.

    Args:
        message: The user's message
        current_concepts: IDs of concepts being discussed

    Returns:
        UpcomingApplication if detected, None otherwise
    """
    # Keywords suggesting upcoming application
    application_keywords = [
        "tomorrow",
        "next week",
        "on monday",
        "on tuesday",
        "on wednesday",
        "on thursday",
        "on friday",
        "meeting with",
        "call with",
        "presenting",
        "interview",
        "negotiation",
        "client call",
        "pitch",
    ]

    message_lower = message.lower()

    # Check for application keywords
    for keyword in application_keywords:
        if keyword in message_lower:
            # Extract context (simple heuristic - in practice LLM does this)
            # Just return the whole message as context for now
            return UpcomingApplication(
                context=message[:100],  # Truncate for storage
                concept_ids=current_concepts,
                outcome_id=None,  # Would be filled in by caller
                planned_date=None,  # Would be extracted by LLM
                stakes=None,
            )

    return None
