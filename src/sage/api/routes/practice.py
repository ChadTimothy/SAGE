"""Practice mode API routes."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from openai import OpenAI

from sage.core.config import get_settings
from sage.graph.learning_graph import LearningGraph
from sage.graph.models import (
    Message,
    PracticeFeedback,
    PracticeScenario,
    Session,
    SessionType,
)
from sage.api.schemas import (
    PracticeFeedbackResponse,
    PracticeHintResponse,
    PracticeMessageRequest,
    PracticeMessageResponse,
    PracticeStartRequest,
    PracticeStartResponse,
)
from fastapi import Depends

from ..auth import CurrentUser, get_current_user
from ..guards import OwnershipVerifier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/practice", tags=["practice"])

# Load prompt templates
PROMPTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "prompts"


def _load_prompt(name: str) -> str:
    """Load a prompt template."""
    path = PROMPTS_DIR / f"{name}.md"
    if path.exists():
        return path.read_text()
    raise FileNotFoundError(f"Prompt template not found: {name}")


def _get_llm_client() -> OpenAI:
    """Get configured LLM client."""
    settings = get_settings()
    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )


def _get_graph() -> LearningGraph:
    """Get configured learning graph."""
    settings = get_settings()
    return LearningGraph(settings.database_url)


def _build_character_prompt(
    scenario: PracticeScenario,
    messages: list[Message],
) -> str:
    """Build the character prompt for practice."""
    template = _load_prompt("practice_character")

    # Simple template substitution
    prompt = template.replace("{{scenario_title}}", scenario.title)
    prompt = prompt.replace("{{sage_role}}", scenario.sage_role)
    prompt = prompt.replace("{{user_role}}", scenario.user_role)

    if scenario.description:
        prompt = prompt.replace(
            "{{#if scenario_description}}\n**Context:** {{scenario_description}}\n{{/if}}",
            f"**Context:** {scenario.description}",
        )
    else:
        prompt = prompt.replace(
            "{{#if scenario_description}}\n**Context:** {{scenario_description}}\n{{/if}}",
            "",
        )

    # Build messages section
    messages_text = ""
    for msg in messages:
        if msg.role == "user":
            messages_text += f"**Them:** {msg.content}\n"
        else:
            messages_text += f"**You ({scenario.sage_role}):** {msg.content}\n"

    # Replace the messages block
    prompt = prompt.split("{{#each messages}}")[0]
    prompt += messages_text
    prompt += f"\n## Your Response\n\nRespond as {scenario.sage_role}. Stay in character. Be realistic and appropriately challenging."

    return prompt


def _build_feedback_prompt(
    scenario: PracticeScenario,
    messages: list[Message],
) -> str:
    """Build the feedback prompt."""
    template = _load_prompt("practice_feedback")

    prompt = template.replace("{{scenario_title}}", scenario.title)
    prompt = prompt.replace("{{sage_role}}", scenario.sage_role)
    prompt = prompt.replace("{{user_role}}", scenario.user_role)

    # Build messages section
    messages_text = ""
    for msg in messages:
        if msg.role == "user":
            messages_text += f"**{scenario.user_role}:** {msg.content}\n"
        else:
            messages_text += f"**{scenario.sage_role}:** {msg.content}\n"

    # Replace the messages block
    parts = prompt.split("{{#each messages}}")
    prompt = parts[0] + messages_text
    if len(parts) > 1:
        # Get everything after {{/each}}
        after_each = parts[1].split("{{/each}}")
        if len(after_each) > 1:
            prompt += after_each[1]

    return prompt


def _build_hint_prompt(
    scenario: PracticeScenario,
    recent_messages: list[Message],
) -> str:
    """Build the hint prompt."""
    template = _load_prompt("practice_hint")

    prompt = template.replace("{{scenario_title}}", scenario.title)
    prompt = prompt.replace("{{sage_role}}", scenario.sage_role)
    prompt = prompt.replace("{{user_role}}", scenario.user_role)

    # Build recent messages (last 4)
    messages_text = ""
    for msg in recent_messages[-4:]:
        if msg.role == "user":
            messages_text += f"**Them:** {msg.content}\n"
        else:
            messages_text += f"**{scenario.sage_role}:** {msg.content}\n"

    parts = prompt.split("{{#each recent_messages}}")
    prompt = parts[0] + messages_text
    if len(parts) > 1:
        after_each = parts[1].split("{{/each}}")
        if len(after_each) > 1:
            prompt += after_each[1]

    return prompt


def _generate_initial_message(client: OpenAI, scenario: PracticeScenario) -> str:
    """Generate the opening message from the character."""
    settings = get_settings()

    system_prompt = f"""You are playing {scenario.sage_role} in a practice scenario called "{scenario.title}".

Generate a realistic opening line to start the conversation. Be natural and in character.
Keep it to 1-2 sentences. Don't be overly formal unless the scenario calls for it."""

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "system", "content": system_prompt}],
        max_tokens=150,
    )

    return response.choices[0].message.content or "Hello, let's begin."


@router.post("/start", response_model=PracticeStartResponse)
async def start_practice(
    request: PracticeStartRequest,
    user: CurrentUser = Depends(get_current_user),
) -> PracticeStartResponse:
    """Start a new practice session."""
    graph = _get_graph()
    client = _get_llm_client()
    verifier = OwnershipVerifier(graph)

    # Use the authenticated user's learner_id
    learner_id = user.learner_id

    # Create practice scenario
    scenario = PracticeScenario(
        scenario_id=request.scenario_id,
        title=request.title,
        description=request.description,
        sage_role=request.sage_role,
        user_role=request.user_role,
    )

    # Generate initial message
    initial_message = _generate_initial_message(client, scenario)

    # Create session
    session = Session(
        learner_id=learner_id,
        session_type=SessionType.PRACTICE,
        practice_scenario=scenario,
        messages=[
            Message(role="sage", content=initial_message, mode="practice")
        ],
    )

    # Save session
    graph.create_session(session)

    return PracticeStartResponse(
        session_id=session.id,
        initial_message=initial_message,
    )


@router.post("/{session_id}/message", response_model=PracticeMessageResponse)
async def send_practice_message(
    session_id: str,
    request: PracticeMessageRequest,
    user: CurrentUser = Depends(get_current_user),
) -> PracticeMessageResponse:
    """Send a message in practice mode and get character response."""
    graph = _get_graph()
    client = _get_llm_client()
    settings = get_settings()
    verifier = OwnershipVerifier(graph)

    # Verify ownership and get session
    verifier.verify_session(user, session_id)
    session = graph.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.session_type != SessionType.PRACTICE:
        raise HTTPException(status_code=400, detail="Not a practice session")

    if not session.practice_scenario:
        raise HTTPException(status_code=400, detail="No practice scenario configured")

    # Add user message
    user_message = Message(role="user", content=request.content, mode="practice")
    session.messages.append(user_message)

    # Build prompt and get response
    prompt = _build_character_prompt(session.practice_scenario, session.messages)

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
    )

    character_response = response.choices[0].message.content or ""

    # Add character response
    sage_message = Message(role="sage", content=character_response, mode="practice")
    session.messages.append(sage_message)

    # Update session
    graph.update_session(session)

    return PracticeMessageResponse(message=character_response)


@router.post("/{session_id}/hint", response_model=PracticeHintResponse)
async def get_practice_hint(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> PracticeHintResponse:
    """Get a hint from SAGE during practice."""
    graph = _get_graph()
    client = _get_llm_client()
    settings = get_settings()
    verifier = OwnershipVerifier(graph)

    verifier.verify_session(user, session_id)
    session = graph.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.practice_scenario:
        raise HTTPException(status_code=400, detail="No practice scenario")

    prompt = _build_hint_prompt(session.practice_scenario, session.messages)

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
    )

    hint = response.choices[0].message.content or "Take a moment to think about your response."

    # Add hint as a special message (won't appear in character conversation)
    hint_message = Message(role="sage", content=f"[HINT] {hint}", mode="practice_hint")
    session.messages.append(hint_message)
    graph.update_session(session)

    return PracticeHintResponse(hint=hint)


@router.post("/{session_id}/end", response_model=PracticeFeedbackResponse)
async def end_practice(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> PracticeFeedbackResponse:
    """End practice session and get feedback."""
    graph = _get_graph()
    client = _get_llm_client()
    settings = get_settings()
    verifier = OwnershipVerifier(graph)

    verifier.verify_session(user, session_id)
    session = graph.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.practice_scenario:
        raise HTTPException(status_code=400, detail="No practice scenario")

    # Filter out hint messages for feedback
    practice_messages = [m for m in session.messages if m.mode != "practice_hint"]

    prompt = _build_feedback_prompt(session.practice_scenario, practice_messages)

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )

    # Parse JSON response
    feedback_text = response.choices[0].message.content or "{}"

    try:
        # Extract JSON from response (might have markdown code blocks)
        if "```json" in feedback_text:
            feedback_text = feedback_text.split("```json")[1].split("```")[0]
        elif "```" in feedback_text:
            feedback_text = feedback_text.split("```")[1].split("```")[0]

        feedback_data = json.loads(feedback_text.strip())
    except (json.JSONDecodeError, IndexError):
        # Fallback if parsing fails
        feedback_data = {
            "positives": ["You completed the practice session"],
            "improvements": ["Try to be more specific in your responses"],
            "summary": "Practice session completed. Review the conversation for learning opportunities.",
            "revealed_gaps": [],
        }

    # Create feedback object
    feedback = PracticeFeedback(
        positives=feedback_data.get("positives", []),
        improvements=feedback_data.get("improvements", []),
        summary=feedback_data.get("summary", ""),
        revealed_gaps=feedback_data.get("revealed_gaps", []),
    )

    # Update session with feedback and end it
    session.practice_feedback = feedback
    from datetime import datetime
    session.ended_at = datetime.utcnow()
    graph.update_session(session)

    return PracticeFeedbackResponse(
        positives=feedback.positives,
        improvements=feedback.improvements,
        summary=feedback.summary,
        revealed_gaps=feedback.revealed_gaps,
    )
