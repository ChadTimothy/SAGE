# SAGE Context Management

**How SAGE Knows What It Knows — Runtime Context Strategy**

---

## The Core Problem

Every time the LLM generates a response, it needs context to make good decisions:

| Decision | Question | Data Needed |
|----------|----------|-------------|
| Mode | What mode should I be in? | Session state, messages, outcome status |
| Content | What should I teach/ask? | Current gap, proven knowledge, what's been tried |
| Connections | Does this relate to something they know? | All proven concepts, explicit relations |
| Adaptation | How do I adjust for their state? | Set/Setting/Intention, energy, time |
| Depth | Light or heavy content? | Mental state, urgency, engagement |
| Progress | Ready to move on? | Verification results, outcome criteria |

---

## Context Loading Strategy

### At Session Start (Eager Load)

Load everything we'll likely need into memory:

```python
class FullContext:
    """Everything loaded at session start"""

    # WHO
    learner: Learner
    insights: LearnerInsights  # Patterns learned over time

    # KNOWLEDGE (what they've proven)
    proven_concepts: list[Concept]

    # CURRENT GOAL
    active_outcome: Outcome | None
    outcome_concepts: list[Concept]  # Concepts found for this outcome

    # CONTINUITY
    last_session: Session | None

    # CONNECTIONS (for fast lookup)
    concept_relations: dict[str, list[Edge]]  # concept_id -> related edges

    # PENDING FOLLOW-UPS (checked before check-in)
    pending_followups: list[ApplicationEvent]  # Applications that need follow-up

    # PAST APPLICATIONS (for teaching context)
    completed_applications: list[ApplicationEvent]  # What they've applied
```

**Why eager load?**
- Avoids database queries on every turn
- Everything needed is in memory
- Session typically touches all this data anyway

### On Each Turn (Build Prompt Context)

Assemble what the LLM needs for THIS specific turn:

```python
class TurnContext:
    """Context assembled for this turn's LLM call"""

    # CURRENT STATE
    mode: DialogueMode
    session_context: SessionContext  # Set/Setting/Intention
    current_concept: Concept | None

    # CONVERSATION
    recent_messages: list[Message]  # Last 15-20
    session_summary: str  # What's happened so far

    # RELEVANT KNOWLEDGE
    proven_concepts: list[ConceptSnapshot]  # Lightweight summaries
    related_concepts: list[ConceptSnapshot]  # Potential connections

    # ADAPTATION
    learner_insights: LearnerInsights
    adaptation_hints: list[str]  # "Go lighter", "Can challenge more"

    # APPLICATIONS (real-world context)
    pending_followup: ApplicationEvent | None  # If we need to ask about an application
    relevant_applications: list[ApplicationSnapshot]  # Past applications for current topic
```

---

## Assessing Set/Setting/Intention

### Initial Check-in (Session Start)

Direct but conversational:
```
SAGE: "Before we dive in—how are you showing up today?
       Quick check: how's your energy, and how much time do you have?"
```

### Continuous Assessment (During Session)

The LLM monitors for state changes through:

**Explicit signals:**
- "I'm getting tired"
- "I have to go in 10 minutes"
- "This is stressing me out"
- "I'm lost"

**Implicit signals:**
- Response length decreasing → fatigue
- Longer pauses → distraction or confusion
- More errors than usual → cognitive overload
- Asking to repeat → not landing
- Disengaged answers → losing interest

**Detection instruction in prompt:**
```markdown
## Monitor for State Changes

Watch for signs the learner's state has shifted:
- Fatigue: shorter responses, less engagement, asking to repeat
- Confusion: hesitation, contradictions, "I think..." hedging
- Stress: rushed responses, frustration signals
- Time pressure: mentions of leaving, checking time
- Disengagement: minimal responses, topic changes

If detected, acknowledge and adapt:
- "You seem like you're hitting a wall. Want to wrap up with a quick win?"
- "Let me try explaining this a different way."
```

---

## Adaptation Strategies

### How Context Changes Behavior

| State | Adaptation |
|-------|------------|
| **Low energy** | Shorter chunks, practical focus, quick wins, more encouragement |
| **High energy** | Can go deeper, explore tangents, make connections, challenge more |
| **Time pressure** | Most critical gap only, skip nice-to-haves, note what's deferred |
| **Confusion** | Slow down, different angle, more analogies, check understanding frequently |
| **Stress** | Smaller steps, acknowledgment, offer to pause, gentler pace |
| **High engagement** | Introduce nuance, go deeper, connect to other concepts |

### Light vs Heavy Content Decision

The LLM decides depth based on:

```python
# Factors pushing toward LIGHTER content:
- energy == "low"
- time_available in ["15 minutes", "short"]
- mindset contains "tired" or "stressed"
- intention_strength == "curious"  # Just exploring

# Factors pushing toward DEEPER content:
- energy == "high"
- time_available in ["open-ended", "hours"]
- intention_strength in ["learning", "urgent"]
- concept.is_foundational  # Can't skip without building on sand

# Special case: URGENT + COMPLEX
if intention_strength == "urgent" and concept.is_complex:
    # Teach minimum viable understanding
    # Note what was skipped for later
    approach = "practical_minimum"
```

### Prompt Instruction for Adaptation

```markdown
## Adapt to Current State

Current context:
- Energy: {{ session_context.energy }}
- Time: {{ session_context.time_available }}
- Mindset: {{ session_context.mindset }}
- Intention: {{ session_context.intention_strength }}

Adaptation guidelines:
{% if session_context.energy == "low" %}
- Keep explanations SHORT and practical
- Focus on one thing at a time
- Offer breaks proactively
{% endif %}

{% if session_context.intention_strength == "urgent" %}
- Skip background theory
- Focus on immediate applicability
- What's the ONE thing they need to handle this?
{% endif %}

{% if session_context.time_available == "short" %}
- Acknowledge time constraint
- Prioritize ruthlessly
- End with clear next step for later
{% endif %}
```

---

## Mode Transitions

### The Mode State Machine

SAGE operates in discrete modes. Transitions happen based on conversation signals.

```
                    ┌─────────────────────────────────────────┐
                    │                                         │
                    ▼                                         │
              ┌──────────┐                                    │
              │ CHECK_IN │ ────────────────────┐              │
              └────┬─────┘                     │              │
                   │                           │              │
      ┌────────────┼────────────┐              │              │
      │            │            │              │              │
      ▼            ▼            ▼              │              │
┌──────────┐ ┌──────────┐ ┌──────────────────┐ │              │
│ FOLLOWUP │ │ OUTCOME  │ │ Resume from last │ │              │
│          │ │ DISCOVERY│ │ session          │ │              │
└────┬─────┘ └────┬─────┘ └────────┬─────────┘ │              │
     │            │                │           │              │
     │            ▼                │           │              │
     │      ┌──────────┐           │           │              │
     │      │ FRAMING  │ ◄─────────┘           │              │
     │      └────┬─────┘                       │              │
     │           │                             │              │
     │           ▼                             │              │
     │      ┌──────────┐                       │              │
     └─────►│ PROBING  │ ◄─────────────────────┤              │
            └────┬─────┘                       │              │
                 │                             │              │
                 ▼                             │              │
            ┌──────────┐                       │              │
            │ TEACHING │                       │              │
            └────┬─────┘                       │              │
                 │                             │              │
                 ▼                             │              │
          ┌──────────────┐                     │              │
          │ VERIFICATION │                     │              │
          └──────┬───────┘                     │              │
                 │                             │              │
        ┌────────┴────────┐                    │              │
        │                 │                    │              │
        ▼                 ▼                    │              │
   [Proof earned]   [Not yet]                  │              │
        │                 │                    │              │
        ▼                 └────────────────────┘              │
  ┌─────────────┐                                             │
  │OUTCOME_CHECK│                                             │
  └──────┬──────┘                                             │
         │                                                    │
    ┌────┴────┐                                               │
    │         │                                               │
    ▼         ▼                                               │
 [Done]   [More gaps] ────────────────────────────────────────┘
```

### Transition Rules

```python
class ModeTransitions:
    """Rules for when to transition between modes"""

    # From CHECK_IN
    CHECK_IN_TRANSITIONS = {
        "pending_followups_exist": DialogueMode.FOLLOWUP,
        "no_active_outcome": DialogueMode.OUTCOME_DISCOVERY,
        "has_active_outcome": DialogueMode.PROBING,  # Or resume from last session
    }

    # From FOLLOWUP
    FOLLOWUP_TRANSITIONS = {
        "followup_complete": DialogueMode.PROBING,  # Continue with learning
        "new_gap_revealed": DialogueMode.TEACHING,  # Address revealed gap first
    }

    # From OUTCOME_DISCOVERY
    OUTCOME_DISCOVERY_TRANSITIONS = {
        "outcome_clarified": DialogueMode.FRAMING,
    }

    # From FRAMING
    FRAMING_TRANSITIONS = {
        "territory_sketched": DialogueMode.PROBING,
    }

    # From PROBING
    PROBING_TRANSITIONS = {
        "gap_identified": DialogueMode.TEACHING,
        "user_claims_knowledge": DialogueMode.VERIFICATION,  # Verify the claim
        "no_gaps_found": DialogueMode.OUTCOME_CHECK,
    }

    # From TEACHING
    TEACHING_TRANSITIONS = {
        "teaching_complete": DialogueMode.VERIFICATION,
        "user_confused": DialogueMode.TEACHING,  # Try different approach
    }

    # From VERIFICATION
    VERIFICATION_TRANSITIONS = {
        "proof_earned": DialogueMode.OUTCOME_CHECK,
        "not_yet_understood": DialogueMode.TEACHING,  # More teaching needed
        "partial_understanding": DialogueMode.PROBING,  # Find specific gap
    }

    # From OUTCOME_CHECK
    OUTCOME_CHECK_TRANSITIONS = {
        "outcome_achieved": None,  # Session can end or new outcome
        "more_gaps_exist": DialogueMode.PROBING,
    }
```

### Transition Signals in Conversation

The LLM detects these signals to determine transitions:

| Signal | From Mode | To Mode | Example |
|--------|-----------|---------|---------|
| User states what they want | CHECK_IN | OUTCOME_DISCOVERY | "I want to learn pricing" |
| Goal is clear and specific | OUTCOME_DISCOVERY | FRAMING | "Confident in pricing calls" |
| Territory acknowledged | FRAMING | PROBING | "Got it, let's see where I am" |
| Gap surfaces in response | PROBING | TEACHING | "I don't know how to..." |
| Teaching delivered | TEACHING | VERIFICATION | After explanation complete |
| Understanding demonstrated | VERIFICATION | OUTCOME_CHECK | Correct application shown |
| User struggles in verification | VERIFICATION | TEACHING | Wrong answer or confusion |
| Can do the thing | OUTCOME_CHECK | (done) | "I feel ready for this" |
| More blocking | OUTCOME_CHECK | PROBING | "But what about..." |

### Mode-Specific Behavior

```python
MODE_BEHAVIORS = {
    DialogueMode.CHECK_IN: {
        "goal": "Gather Set/Setting/Intention",
        "tone": "Warm, quick, not intrusive",
        "output": "SessionContext populated",
    },
    DialogueMode.FOLLOWUP: {
        "goal": "Learn how application went",
        "tone": "Curious, non-judgmental",
        "output": "FollowupResponse with gaps revealed",
    },
    DialogueMode.OUTCOME_DISCOVERY: {
        "goal": "Clarify what they want to DO",
        "tone": "Curious, clarifying",
        "output": "Outcome with stated and clarified goal",
    },
    DialogueMode.FRAMING: {
        "goal": "Light sketch of territory",
        "tone": "Informative but brief",
        "output": "Territory list, expectations set",
    },
    DialogueMode.PROBING: {
        "goal": "Find what's blocking them",
        "tone": "Exploratory, Socratic",
        "output": "GapIdentified or no gaps found",
    },
    DialogueMode.TEACHING: {
        "goal": "Fill the specific gap",
        "tone": "Clear, adapted to state",
        "output": "Concept taught, ready for verification",
    },
    DialogueMode.VERIFICATION: {
        "goal": "Confirm real understanding",
        "tone": "Testing but supportive",
        "output": "ProofEarned or back to teaching",
    },
    DialogueMode.OUTCOME_CHECK: {
        "goal": "Can they do the thing?",
        "tone": "Direct, honest",
        "output": "outcome_achieved or more probing needed",
    },
}
```

---

## Finding Connections to Prior Knowledge

### Why This Matters

When teaching "handling-objections", if they already understand "value-articulation", we can build on it:

> "Remember how you learned to articulate your value? Handling objections is just applying that under pressure. Same foundation, different context."

### Two Sources of Connections

**1. Explicit Relations (stored in database)**

```sql
-- Find proven concepts related to current topic
SELECT
    c.name, c.display_name, c.summary,
    e.metadata->>'relationship' as how_related,
    e.metadata->>'strength' as strength
FROM concepts c
JOIN proofs p ON c.id = p.concept_id
JOIN edges e ON (c.id = e.from_id OR c.id = e.to_id)
WHERE p.learner_id = ?
  AND e.edge_type = 'relates_to'
  AND ? IN (e.from_id, e.to_id)  -- current concept
ORDER BY CAST(e.metadata->>'strength' AS REAL) DESC;
```

**2. LLM-Discovered Relations (during conversation)**

Include proven concepts in prompt and let LLM find connections:

```markdown
## What This Learner Already Knows (Proven)

{% for concept in proven_concepts %}
- **{{ concept.display_name }}**: {{ concept.summary }}
{% endfor %}

## Current Topic
Teaching: {{ current_concept.display_name }}

## Instructions
Look for connections to proven knowledge:
- "Remember when you learned X? This is similar because..."
- "You already know Y, which is the foundation here..."
- "This connects to Z from your pricing work..."

If you use a connection, note it in your response structure.
```

### Storing Discovered Connections

When the LLM finds a connection, it outputs:

```python
class ConnectionDiscovered:
    from_concept: str      # The proven concept
    to_concept: str        # Current concept
    relationship: str      # How they connect
    strength: float        # 0.0-1.0
    used_in_teaching: bool # Did we use this in explanation?
```

This becomes a `relates_to` edge for future sessions.

---

## Learning From Patterns Over Time

SAGE should get better at teaching THIS specific learner.

### LearnerInsights Model

```python
class LearnerInsights:
    """Patterns learned about this learner over time"""

    # WHEN do they learn best?
    best_energy_level: str | None       # "High energy sessions more productive"
    best_time_of_day: str | None        # Inferred from session timestamps
    optimal_session_length: str | None  # "Sweet spot around 45 minutes"

    # HOW do they learn best?
    prefers_examples: bool      # Concrete examples over abstractions
    prefers_theory_first: bool  # Wants "why" before "how"
    needs_frequent_checks: bool # Benefits from more verification
    responds_to_challenge: bool # Rises to difficult questions

    # PATTERNS noticed
    patterns: list[str]
    # "Retains less when in urgent mode—consider follow-up sessions"
    # "Responds well to analogies from design world"
    # "Gets frustrated with repetition—vary approaches"

    # What's worked
    effective_approaches: list[str]
    # "Socratic questioning"
    # "Real-world scenarios"
    # "Building on design expertise"
```

### Updating Insights After Sessions

```python
def update_learner_insights(session: Session, insights: LearnerInsights):
    """Learn from this session to improve future sessions"""

    # Did they earn proofs in certain conditions?
    if session.proofs_earned > 0:
        # Log what worked
        if session.context.energy == "high":
            insights.note("Productive when high energy")
        if session.context.time_available == "open":
            insights.note("Deep work possible with open time")

    # Did they struggle in certain conditions?
    if session.confusion_signals > 2:
        if session.context.energy == "low":
            insights.note("Struggles when low energy—keep it light")

    # What teaching approaches worked?
    for proof in session.proofs:
        approach = proof.exchange.teaching_approach
        insights.effective_approaches.add(approach)
```

---

## Edge Cases and Handling

### 1. Returning After Long Break

```python
if days_since_last_session > 14:
    strategy = "recap_mode"

    # Don't assume they remember everything
    # Quick verification of key concepts before building on them

    SAGE: "It's been a couple weeks—good to have you back.
           Before we continue, let me check where we left off.
           You were working on [outcome]. Quick refresher:
           can you still articulate why your price is what it is?"
```

### 2. User Claims Prior Knowledge

```
User: "I already know how to handle objections"

SAGE: "Great—let me verify so we can skip ahead.
       Quick scenario: Client says your price is too high,
       but you know they have a deadline Friday. What's your move?"

# If they demonstrate → create proof, move on
# If they struggle → "Looks like there's a nuance here..."
```

### 3. State Change Mid-Session

```python
# User: "Actually I have to leave in 5 minutes"

detected_change = StateChange(
    what_changed="time_pressure",
    detected_from="explicit statement",
    recommended_adaptation="wrap_up_mode"
)

SAGE: "Got it. Let me give you the one thing that'll help most.
       We can go deeper next time."
```

### 4. Confusion Spiral

```python
if consecutive_confusion_signals > 3:
    # Current approach isn't working
    # Try completely different angle

    SAGE: "Let me try something different. Forget what I said—
           here's another way to think about this entirely..."

    # Log: this teaching approach didn't work for this learner
    insights.ineffective_approaches.add(current_approach)
```

### 5. User Goes Off-Topic

```
User: "Actually, can we talk about something else?"

SAGE: "Sure. Do you want to:
       1. Pause this goal and come back later?
       2. Switch to a different goal entirely?
       3. Just take a quick tangent and return?

       What you've learned is saved either way."
```

### 6. Energy Drop Detected

```python
# Signals: responses getting shorter, longer delays

SAGE: "You seem like you might be hitting a wall.
       Want to wrap up with a quick win, or save this
       for when you're fresher?"
```

### 7. Knowledge Decay Concern

```python
if proof.earned_at < (now - 60_days) and concept.is_foundational:
    # They proved this long ago, and we're about to build on it

    SAGE: "Before we go further—you learned [concept] a while back.
           Quick check to make sure it's still solid..."

    # Re-verify before building on potentially decayed foundation
```

---

## The Complete Prompt Context Structure

```python
class PromptContext(BaseModel):
    """Everything sent to LLM each turn"""

    # === WHO ===
    learner: LearnerSnapshot
    insights: LearnerInsights

    # === CURRENT STATE ===
    mode: DialogueMode
    session_context: SessionContext
    adaptation_hints: list[str]

    # === GOAL ===
    outcome: OutcomeSnapshot | None
    outcome_progress: OutcomeProgress | None

    # === KNOWLEDGE ===
    proven_concepts: list[ConceptSnapshot]
    current_concept: ConceptSnapshot | None
    related_concepts: list[RelatedConcept]

    # === CONVERSATION ===
    recent_messages: list[Message]  # Last 15-20
    session_summary: str

    # === INSTRUCTIONS ===
    mode_instructions: str
    transition_signals: list[str]


class ConceptSnapshot(BaseModel):
    """Lightweight concept info for prompt"""
    name: str
    display_name: str
    summary: str | None
    has_proof: bool
    proof_confidence: float | None


class OutcomeProgress(BaseModel):
    """Progress toward current goal"""
    stated_goal: str
    clarified_goal: str
    concepts_identified: int
    concepts_proven: int
    current_concept: str | None
```

---

## The LLM Output Structure

The LLM returns structured data, not just text:

```python
class SAGEResponse(BaseModel):
    """Structured output from LLM each turn"""

    # === THE RESPONSE ===
    message: str  # What user sees

    # === MODE ===
    current_mode: DialogueMode
    transition_to: DialogueMode | None
    transition_reason: str | None

    # === STATE UPDATES ===
    gap_identified: GapIdentified | None
    proof_earned: ProofEarned | None
    connection_discovered: ConnectionDiscovered | None

    # === APPLICATION TRACKING ===
    application_detected: ApplicationDetected | None   # Upcoming real-world application
    followup_response: FollowupResponse | None         # Result of asking about past application

    # === CONTEXT UPDATES ===
    state_change_detected: StateChange | None
    context_update: SessionContext | None

    # === OUTCOME ===
    outcome_achieved: bool
    outcome_reasoning: str | None

    # === LEARNING ===
    teaching_approach_used: str | None  # For insights tracking

    # === DEBUG ===
    reasoning: str | None


class GapIdentified(BaseModel):
    name: str
    display_name: str
    description: str
    blocking_outcome: str


class ProofEarned(BaseModel):
    concept_name: str
    demonstration_type: str  # explanation, application, both
    evidence: str
    confidence: float
    exchange: ProofExchange


class StateChange(BaseModel):
    what_changed: str  # energy_drop, time_pressure, confusion, etc.
    detected_from: str  # What triggered this
    recommended_adaptation: str
```

---

## Structured Output Strategy

### How to Get Structured Output from the LLM

We use the OpenAI-compatible structured output API to get validated JSON responses:

```python
from pydantic import BaseModel
from openai import OpenAI

def get_sage_response(
    client: OpenAI,
    model: str,
    prompt_context: PromptContext,
    user_message: str
) -> SAGEResponse:
    """Get structured response from LLM"""

    # Build the full prompt
    system_prompt = build_system_prompt(prompt_context)
    messages = build_message_history(prompt_context, user_message)

    # Request structured output using Pydantic model
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            *messages
        ],
        response_format=SAGEResponse,  # Pydantic model defines schema
    )

    return completion.choices[0].message.parsed
```

### Why Structured Output?

| Approach | Pros | Cons |
|----------|------|------|
| **Structured output (our choice)** | Guaranteed valid JSON, type-safe, Pydantic validation | Requires compatible API |
| Function calling | Widely supported | More boilerplate, less natural |
| JSON mode + parsing | Simpler | No schema validation, can fail |
| Text parsing | No special API needed | Fragile, error-prone |

### Handling Output Errors

```python
def get_sage_response_safe(
    client: OpenAI,
    model: str,
    prompt_context: PromptContext,
    user_message: str
) -> SAGEResponse:
    """Get structured response with error handling"""

    try:
        return get_sage_response(client, model, prompt_context, user_message)

    except ValidationError as e:
        # Pydantic validation failed - shouldn't happen with structured output
        # but handle gracefully
        logger.error(f"Response validation failed: {e}")

        # Return safe fallback - continue conversation without state changes
        return SAGEResponse(
            message="I need a moment to gather my thoughts. Let me try that again.",
            current_mode=prompt_context.mode,
            transition_to=None,
            transition_reason=None,
            gap_identified=None,
            proof_earned=None,
            connection_discovered=None,
            application_detected=None,
            followup_response=None,
            state_change_detected=None,
            context_update=None,
            outcome_achieved=False,
            outcome_reasoning=None,
            teaching_approach_used=None,
            reasoning=f"Fallback due to validation error: {e}"
        )

    except Exception as e:
        # API error, network issue, etc.
        logger.error(f"LLM call failed: {e}")
        raise  # Let caller handle - can't recover gracefully
```

### Validating State Changes

Before persisting state changes from SAGEResponse, validate them:

```python
def validate_response_changes(
    response: SAGEResponse,
    context: PromptContext
) -> list[str]:
    """Validate that response changes make sense given context"""

    warnings = []

    # Can't earn proof without being in VERIFICATION mode
    if response.proof_earned and context.mode != DialogueMode.VERIFICATION:
        warnings.append(
            f"Proof earned in {context.mode} mode (expected VERIFICATION)"
        )

    # Can't identify gap without being in PROBING mode
    if response.gap_identified and context.mode != DialogueMode.PROBING:
        warnings.append(
            f"Gap identified in {context.mode} mode (expected PROBING)"
        )

    # Mode transition should follow rules
    if response.transition_to:
        valid_transitions = get_valid_transitions(context.mode)
        if response.transition_to not in valid_transitions:
            warnings.append(
                f"Invalid transition: {context.mode} -> {response.transition_to}"
            )

    return warnings
```

### Model Requirements

For structured output to work reliably:

- **OpenAI**: `gpt-4o-2024-08-06` or later (structured outputs feature)
- **Grok**: Check current model support for structured output
- **Anthropic**: Use function calling or JSON mode with manual parsing

```python
# Check if model supports structured output
STRUCTURED_OUTPUT_MODELS = {
    "gpt-4o-2024-08-06",
    "gpt-4o-mini-2024-07-18",
    "grok-2",  # Verify current support
}

def supports_structured_output(model: str) -> bool:
    return model in STRUCTURED_OUTPUT_MODELS
```

---

## Snapshot Models

Lightweight models for prompt context. These are read-only summaries optimized for token efficiency.

```python
class LearnerSnapshot(BaseModel):
    """Lightweight learner info for prompt"""
    id: str
    name: str
    created_at: datetime
    total_sessions: int
    total_proofs: int
    active_outcome_id: str | None

    # Preferences (affects content format)
    prefers_examples: bool = True
    prefers_theory_first: bool = False

    @classmethod
    def from_learner(cls, learner: Learner) -> "LearnerSnapshot":
        return cls(
            id=learner.id,
            name=learner.name,
            created_at=learner.created_at,
            total_sessions=learner.total_sessions,
            total_proofs=learner.total_proofs,
            active_outcome_id=learner.active_outcome_id,
            prefers_examples=learner.preferences.get("prefers_examples", True),
            prefers_theory_first=learner.preferences.get("prefers_theory_first", False),
        )


class OutcomeSnapshot(BaseModel):
    """Lightweight outcome info for prompt"""
    id: str
    stated_goal: str
    clarified_goal: str | None
    context: str | None           # Why this matters
    success_criteria: str | None  # How they'll know they achieved it
    status: str                   # active, achieved, abandoned

    @classmethod
    def from_outcome(cls, outcome: Outcome) -> "OutcomeSnapshot":
        return cls(
            id=outcome.id,
            stated_goal=outcome.stated_goal,
            clarified_goal=outcome.clarified_goal,
            context=outcome.context,
            success_criteria=outcome.success_criteria,
            status=outcome.status,
        )


class ApplicationSnapshot(BaseModel):
    """Lightweight application event for prompt"""
    id: str
    context: str              # "pricing call with new client"
    planned_date: date | None
    status: str               # upcoming, pending_followup, completed
    outcome_result: str | None  # went_well, struggled, mixed
    what_worked: str | None
    what_struggled: str | None
    concepts_applied: list[str]  # Names of concepts

    @classmethod
    def from_application_event(
        cls,
        event: ApplicationEvent,
        concept_names: dict[str, str]
    ) -> "ApplicationSnapshot":
        return cls(
            id=event.id,
            context=event.context,
            planned_date=event.planned_date,
            status=event.status,
            outcome_result=event.outcome_result,
            what_worked=event.what_worked,
            what_struggled=event.what_struggled,
            concepts_applied=[
                concept_names.get(cid, cid) for cid in event.concept_ids
            ],
        )


class RelatedConcept(BaseModel):
    """A concept related to current context"""
    name: str
    display_name: str
    summary: str | None
    relationship: str      # How it relates ("builds on", "contrasts with", etc.)
    strength: float        # 0.0-1.0 relevance


class ProofExchange(BaseModel):
    """The verification exchange that led to a proof"""
    verification_question: str
    learner_response: str
    demonstration_type: str  # explanation, application, synthesis
```

---

## Persisting After Each Turn

```python
def persist_turn(session: Session, user_input: str, response: SAGEResponse):
    """Update database after each turn"""

    # ALWAYS: Record messages
    session.messages.append(Message(role="user", content=user_input))
    session.messages.append(Message(role="sage", content=response.message, mode=response.current_mode))

    # If gap identified → create concept
    if response.gap_identified:
        concept = store.create_concept(response.gap_identified)
        store.add_edge(outcome_id, concept.id, "requires")
        session.current_concept = concept.id

    # If proof earned → create proof, update concept
    if response.proof_earned:
        proof = store.create_proof(response.proof_earned)
        store.update_concept_status(concept_id, "understood")
        store.add_edge(concept_id, proof.id, "demonstrated_by")
        learner.total_proofs += 1

    # If connection discovered → create edge
    if response.connection_discovered:
        store.add_edge(
            from_id=response.connection_discovered.from_concept,
            to_id=response.connection_discovered.to_concept,
            edge_type="relates_to",
            metadata=response.connection_discovered
        )

    # If state change → update session context
    if response.state_change_detected:
        session.context = response.context_update
        log_for_insights(response.state_change_detected)

    # If application detected → create application event
    if response.application_detected:
        app_event = store.create_application_event(
            learner_id=learner.id,
            context=response.application_detected.context,
            concept_ids=response.application_detected.concepts,
            outcome_id=outcome.id,
            session_id=session.id,
            planned_date=response.application_detected.planned_date,
            stakes=response.application_detected.stakes
        )
        # Link concepts to this application
        for concept_id in response.application_detected.concepts:
            store.add_edge(concept_id, app_event.id, "applied_in")

    # If followup response → update application event
    if response.followup_response:
        process_followup_struggles(
            event=store.get_application_event(response.followup_response.event_id),
            response=response.followup_response
        )

    # If mode transition
    if response.transition_to:
        session.current_mode = response.transition_to

    # If outcome achieved
    if response.outcome_achieved:
        outcome.status = "achieved"
        outcome.achieved_at = now()
        learner.active_outcome_id = None
```

---

## Key Queries for Context Loading

### Get Everything for Session Start

```sql
-- Learner with active outcome
SELECT l.*, o.*
FROM learners l
LEFT JOIN outcomes o ON l.active_outcome_id = o.id
WHERE l.id = ?;

-- All proven concepts
SELECT c.*, p.confidence, p.earned_at
FROM concepts c
JOIN proofs p ON c.id = p.concept_id
WHERE c.learner_id = ?;

-- All concept relations
SELECT e.*, c1.name as from_name, c2.name as to_name
FROM edges e
JOIN concepts c1 ON e.from_id = c1.id
JOIN concepts c2 ON e.to_id = c2.id
WHERE e.edge_type = 'relates_to'
  AND c1.learner_id = ?;

-- Last session for continuity
SELECT * FROM sessions
WHERE learner_id = ?
ORDER BY ended_at DESC
LIMIT 1;
```

### Find Related Concepts

```sql
-- Explicit relations to a concept
SELECT c.*, e.metadata
FROM concepts c
JOIN edges e ON c.id = e.from_id OR c.id = e.to_id
WHERE e.edge_type = 'relates_to'
  AND ? IN (e.from_id, e.to_id)
  AND c.id != ?
  AND EXISTS (SELECT 1 FROM proofs WHERE concept_id = c.id);
```

---

## Application Follow-ups and Retrospectives

### The Learning Feedback Loop

Real learning happens in application, not just understanding. SAGE tracks when learners mention they'll apply something, then follows up to create a feedback loop:

```
Learn concept → Apply in real world → Report back → Identify gaps → Fill gaps → Apply better
      ↑                                                                              │
      └──────────────────────────────────────────────────────────────────────────────┘
```

### Detecting Application Events

During conversation, SAGE watches for signals that the learner will apply what they're learning:

**Explicit signals:**
- "I have a pricing call tomorrow"
- "I'm meeting with a client Friday"
- "I need to present this next week"

**Implicit signals:**
- Questions about specific scenarios
- Nervousness about upcoming situations
- Time-bounded urgency

**When detected, SAGE:**
1. Captures the context (what, when, stakes)
2. Links relevant concepts to this application
3. Offers targeted preparation
4. Notes it for follow-up

```python
class ApplicationDetected(BaseModel):
    context: str              # "pricing call tomorrow afternoon"
    concepts: list[str]       # Concepts being applied
    planned_date: date | None
    stakes: str               # "high", "medium", "low"
    prep_offered: bool        # Did SAGE offer preparation?
```

### Follow-up Logic at Session Start

Before the regular check-in, SAGE checks for pending follow-ups:

```python
def check_for_followups(learner_id: str) -> list[ApplicationEvent]:
    """Find applications that need follow-up"""
    return store.query("""
        SELECT * FROM application_events
        WHERE learner_id = ?
          AND status IN ('upcoming', 'pending_followup')
          AND (planned_date <= date('now') OR status = 'pending_followup')
        ORDER BY planned_date ASC
    """, learner_id)
```

**If follow-ups exist:**

```
SAGE: "Before we dive in—you had that pricing call on Tuesday.
       How did it go?"

User: "It went okay, but I caved on the discount again."

SAGE: "Got it. What happened in that moment?"

User: "They asked for 20% off and I just said yes without thinking."

SAGE: "That's useful. You've got the value articulation down—
       you said the price confidently. The gap is holding firm
       under pressure. Let's work on that before your next one."
```

### Processing Follow-up Responses

SAGE structures follow-up as a mini-retrospective:

```python
class FollowupResponse(BaseModel):
    """What SAGE extracts from follow-up conversation"""
    event_id: str

    # What happened
    outcome_result: str           # "went_well" | "struggled" | "mixed"

    # Breakdown
    what_worked: str | None       # "Stated price confidently, held silence"
    what_struggled: str | None    # "Caved on discount request"

    # Learning
    gaps_revealed: list[str]      # New concepts/gaps identified
    insights: str | None          # Learner's own reflection

    # Context for future
    reference_for_teaching: str   # Summary to use in future sessions
```

### Using Application History in Teaching

When teaching a concept, SAGE checks for past applications to make it relevant:

**Prompt context includes:**

```markdown
## Past Applications of Related Concepts

{% for app in past_applications %}
### {{ app.context }}
- **Result:** {{ app.outcome_result }}
- **What worked:** {{ app.what_worked }}
- **What struggled:** {{ app.what_struggled }}
- **Their insight:** {{ app.insights }}
{% endfor %}

## Instructions

Reference past real-world experiences when teaching:
- "Last time you had a pricing call, you caved on the discount.
   Let's make sure that doesn't happen again."
- "You mentioned you struggle when they ask for X—here's how to handle it."
- Build on what worked, address what didn't.
```

### Creating New Gaps from Struggles

When a follow-up reveals struggles, SAGE may identify new gaps:

```python
def process_followup_struggles(event: ApplicationEvent, response: FollowupResponse):
    """Turn struggles into teachable moments"""

    if response.gaps_revealed:
        for gap_name in response.gaps_revealed:
            # Create new concept from revealed gap
            concept = store.create_concept(
                learner_id=event.learner_id,
                name=gap_name,
                display_name=gap_name.replace("-", " ").title(),
                description=f"Gap revealed during {event.context}",
                discovered_from=event.outcome_id
            )

            # Note the connection to the application
            store.add_edge(
                from_id=concept.id,
                to_id=event.id,
                edge_type="applied_in",
                metadata={"revealed_by_struggle": True}
            )

    # Update event status
    event.status = ApplicationStatus.COMPLETED
    event.outcome_result = response.outcome_result
    event.what_worked = response.what_worked
    event.what_struggled = response.what_struggled
    event.gaps_revealed = response.gaps_revealed
    event.insights = response.insights
    event.followed_up_at = datetime.utcnow()

    store.update_application_event(event)
```

### Long-term Pattern Detection

Over time, SAGE looks for patterns in applications:

```python
def detect_application_patterns(learner_id: str) -> list[str]:
    """Find recurring struggles or successes"""

    completed = store.get_completed_applications(learner_id)

    # Group by struggle type
    struggles = defaultdict(list)
    for app in completed:
        if app.what_struggled:
            struggles[app.what_struggled].append(app)

    patterns = []
    for struggle, apps in struggles.items():
        if len(apps) >= 2:
            patterns.append(
                f"Recurring struggle: '{struggle}' in {len(apps)} situations"
            )

    return patterns
```

**Example pattern recognition:**
```
SAGE: "I've noticed a pattern—in your last three client
       conversations, you've mentioned caving on discounts.
       This keeps coming up. Want to make it a focused goal?"
```

### Preparing for Known Applications

When a learner mentions an upcoming application, SAGE can offer targeted prep:

```
User: "I have another pricing call on Thursday."

SAGE: "Good. Last time you said you caved on the discount.
       What's your plan for if they ask again?"

User: "I don't know, that's why I'm nervous."

SAGE: "Let's role-play it. I'll ask for a discount, you practice
       holding firm. Ready?"
```

---

*Context Management v1.0 — Runtime Intelligence*
