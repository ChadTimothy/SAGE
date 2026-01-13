# SAGE Data Model

**Personal Learning Graph — Iterate/Discover Approach**

---

## Overview

SAGE uses a graph that grows from conversation. No pre-planning, no paths—just outcomes, gaps discovered, concepts learned, and proofs earned.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PERSONAL LEARNING GRAPH                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    NODES                              EDGES                                 │
│    ─────                              ─────                                 │
│    • Learner (1 per user)             • requires (Outcome→Concept)         │
│    • Outcome (goals pursued)          • relates_to (Concept↔Concept)       │
│    • Concept (gaps filled)            • demonstrated_by (Concept→Proof)    │
│    • Proof (verified understanding)   • explored_in (Concept→Session)      │
│    • Session (conversations)          • builds_on (Outcome→Outcome)        │
│    • ApplicationEvent (real-world)    • applied_in (Concept→Application)   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**The Learning Feedback Loop:**
```
Learn concept → Apply in real world → Report back → Identify gaps → Fill gaps → Apply better
      ↑                                                                              │
      └──────────────────────────────────────────────────────────────────────────────┘
```

**Key difference from path-based models:** No `current_path`, no `current_step`, no prerequisite chains. The graph records what happened, not what's planned.

---

## Node Definitions

### Learner

The root node. One per person.

```python
Learner:
  id: str                     # UUID
  created_at: datetime

  # Who they are
  profile:
    name: str | None
    context: str | None       # "freelance designer", "PM at a startup"
    background: str | None    # Relevant experience
    age_group: 'child' | 'teen' | 'adult' | None  # Affects vocabulary, examples, tone
    skill_level: 'beginner' | 'intermediate' | 'advanced' | None  # General learning ability

  # How they learn (Setting)
  preferences:
    session_length: short | medium | long
    style: practical | theoretical | mixed
    pace: patient | moderate | fast

  # Current state
  active_outcome_id: str | None    # What they're working toward
  current_focus: str | None        # Current concept/gap being addressed

  # Stats
  last_session_at: datetime | None
  total_sessions: int
  total_proofs: int
```

**Age Group affects:**
- Vocabulary complexity (simpler for child, professional for adult)
- Examples used (school scenarios for child, work scenarios for adult)
- Tone (more encouraging for child, peer-like for adult)
- Content appropriateness

**Skill Level affects:**
- Pace of teaching (slower for beginner, faster for advanced)
- Depth of explanation (more foundational for beginner)
- Challenge level (simpler verification for beginner)

---

### Outcome

A real-world goal. What they want to be able to DO.

```python
Outcome:
  id: str                     # UUID
  learner_id: str

  # The goal
  stated_goal: str            # What they said
  clarified_goal: str | None  # What we determined they meant
  motivation: str | None      # Why they want this
  success_criteria: str | None # How they'll know they got there

  # Status
  status: 'active' | 'achieved' | 'paused' | 'abandoned'

  # Framing (light sketch, not a plan)
  territory: list[str] | None  # ["knowing your value", "articulating it", "handling pushback"]

  # Timestamps
  created_at: datetime
  achieved_at: datetime | None
  last_worked_on: datetime
```

**Note:** No `current_path` or `current_step`. We don't plan the journey—we discover it.

**Example:**
```json
{
  "id": "outcome-abc123",
  "learner_id": "learner-xyz",
  "stated_goal": "I want to price my freelance services better",
  "clarified_goal": "Confidently set and defend higher rates",
  "motivation": "I know I'm undercharging and panic in pricing conversations",
  "success_criteria": "Have a pricing conversation without anxiety, know what to say when pushed back",
  "status": "active",
  "territory": ["knowing your value", "articulating it", "the conversation", "handling pushback"],
  "created_at": "2024-01-15T10:00:00Z"
}
```

---

### Concept

A unit of understanding. Created when a gap is identified and taught.

```python
Concept:
  id: str                     # UUID
  learner_id: str

  # What it is
  name: str                   # "value-articulation"
  display_name: str           # "Value Articulation"
  description: str            # What this concept covers

  # Origin
  discovered_from: str        # outcome_id where this gap was found
  discovered_at: datetime

  # Status
  status: 'identified' | 'teaching' | 'understood'

  # For future sessions
  summary: str | None         # Brief recap of what was taught

  # Stats
  times_discussed: int
  understood_at: datetime | None
```

**Note:** Concepts are created when gaps are found, not planned upfront.

**Example:**
```json
{
  "id": "concept-def456",
  "learner_id": "learner-xyz",
  "name": "value-articulation",
  "display_name": "Value Articulation",
  "description": "Being able to explain why your work is worth what you charge",
  "discovered_from": "outcome-abc123",
  "status": "understood",
  "summary": "Reframing from 'I charge X' to 'you're buying Y which delivers Z'",
  "times_discussed": 2,
  "understood_at": "2024-01-15T10:45:00Z"
}
```

---

### Proof

Verified understanding. The learner demonstrated they get it.

```python
Proof:
  id: str                     # UUID
  learner_id: str
  concept_id: str             # What was proven
  session_id: str             # When it was earned

  # Evidence
  demonstration_type: 'explanation' | 'application' | 'both'
  evidence: str               # Summary of how they demonstrated it
  confidence: float           # 0.0 - 1.0

  # The exchange that earned it
  exchange:
    prompt: str               # What SAGE asked
    response: str             # What the learner said
    analysis: str             # Why this demonstrates understanding

  # Timestamp
  earned_at: datetime
```

**Example:**
```json
{
  "id": "proof-ghi789",
  "learner_id": "learner-xyz",
  "concept_id": "concept-def456",
  "session_id": "session-001",
  "demonstration_type": "application",
  "evidence": "Successfully reframed a price objection in terms of value delivered",
  "confidence": 0.85,
  "exchange": {
    "prompt": "Client says: 'Why should I pay you $2000 when I can get a logo for $100 online?' What do you say?",
    "response": "You're not comparing the same thing. A $100 logo is just an image. What I do is figure out what your brand needs to communicate, design something that does that, and make sure it works everywhere you'll use it. You're buying a business tool, not a picture.",
    "analysis": "Demonstrated value framing without mentioning costs or time. Correctly positioned as different product category."
  },
  "earned_at": "2024-01-15T10:45:00Z"
}
```

---

### Session

A conversation. What happened, what was covered, and the learner's state when it started.

```python
Session:
  id: str                     # UUID
  learner_id: str
  outcome_id: str | None      # Which goal was active

  # Timing
  started_at: datetime
  ended_at: datetime | None

  # Set, Setting, Intention for THIS session
  # (Captured at session start—same person learns differently depending on state)
  context:
    # SET - Current mental/physical state
    energy: 'low' | 'medium' | 'high' | None
    mindset: str | None           # "stressed about deadline", "curious and relaxed"
    time_available: str | None    # "15 minutes", "an hour", "open-ended"

    # SETTING - Current environment
    environment: str | None       # "quiet office", "commuting", "at home evening"

    # INTENTION - Purpose for this session
    intention_strength: 'curious' | 'learning' | 'urgent' | None
    session_goal: str | None      # What they want from THIS session specifically

  # Conversation history
  messages: list[Message]         # Full exchange for context/continuity

  # What happened (summary)
  summary: str | None             # "Found gap in value articulation, taught reframing, earned proof"

  # What was touched
  concepts_explored: list[str]     # concept_ids
  proofs_earned: list[str]         # proof_ids
  connections_found: list[str]     # edge_ids for relates_to edges

  # For continuity
  ending_state:
    mode: str                      # What mode we were in
    current_focus: str | None      # What concept/gap we were on
    next_step: str | None          # Brief note on what comes next


Message:
  role: 'user' | 'sage'
  content: str
  timestamp: datetime
  mode: str | None                # What dialogue mode produced this
```

**Why capture Set/Setting/Intention per session?**

The same person learns differently based on their current state:
- Exhausted after work → shorter, more practical chunks
- Fresh Saturday morning → ready for deeper exploration
- Urgent deadline → focused on immediate applicability
- Casual curiosity → more exploratory, can go on tangents

SAGE checks in at session start and adapts approach accordingly.

---

### Application Event

Real-world applications of learning. Created when learner mentions they'll use something, followed up later.

```python
ApplicationEvent:
  id: str                     # UUID
  learner_id: str
  concept_ids: list[str]      # Concepts being applied
  outcome_id: str             # Related outcome
  session_id: str             # Session where mentioned

  # What's planned
  context: str                # "pricing call tomorrow", "design presentation Friday"
  planned_date: date | None   # When they'll apply it
  stakes: str | None          # "high", "medium", "low"

  # Status
  status: 'upcoming' | 'pending_followup' | 'completed' | 'skipped'
  created_at: datetime

  # Follow-up (filled in later)
  followup_session_id: str | None
  followed_up_at: datetime | None

  # What happened
  outcome_result: str | None           # "went well", "struggled", "mixed"
  what_worked: str | None              # What they did well
  what_struggled: str | None           # Where they had trouble
  gaps_revealed: list[str] | None      # New gaps discovered
  insights: str | None                 # Their reflection
```

**Example:**

```json
{
  "id": "app-xyz123",
  "learner_id": "learner-xyz",
  "concept_ids": ["concept-price-presentation", "concept-handling-objections"],
  "context": "pricing call with potential client tomorrow at 2pm",
  "planned_date": "2024-01-16",
  "stakes": "high",
  "status": "completed",
  "outcome_result": "mixed",
  "what_worked": "Stated price confidently, held the silence",
  "what_struggled": "When they asked for a discount, I caved too quickly",
  "gaps_revealed": ["discount-negotiation"],
  "insights": "I was ready for objections about value but not for 'can you do it cheaper'"
}
```

**Why this matters:**

This creates a feedback loop:
1. Learn concept → 2. Apply in real world → 3. Report back → 4. Identify gaps → 5. Fill gaps → 6. Apply better

SAGE can reference past applications:
> "Last time you had a pricing call, you said you caved on the discount.
>  Let's make sure that doesn't happen again—what will you do differently?"

---

## Edge Definitions

### requires

**Outcome → Concept**

"This gap was found while pursuing this goal."

```python
RequiresEdge:
  id: str
  from_id: str              # outcome_id
  to_id: str                # concept_id
  edge_type: 'requires'
  created_at: datetime
```

**Note:** This edge is created when a gap is discovered, not upfront.

---

### relates_to

**Concept ↔ Concept**

"These connect." Discovered during conversation.

```python
RelatesToEdge:
  id: str
  from_id: str              # concept_id
  to_id: str                # concept_id
  edge_type: 'relates_to'

  relationship: str         # How they connect
  strength: float           # 0.0 - 1.0
  discovered_in: str        # session_id
  created_at: datetime
```

**Example:** SAGE notices that "pricing-psychology" (from a pricing goal) relates to "risk-return-tradeoff" (from an investing goal).

---

### demonstrated_by

**Concept → Proof**

"Understanding was verified here."

```python
DemonstratedByEdge:
  id: str
  from_id: str              # concept_id
  to_id: str                # proof_id
  edge_type: 'demonstrated_by'
  created_at: datetime
```

---

### explored_in

**Concept → Session**

"We discussed this in this session."

```python
ExploredInEdge:
  id: str
  from_id: str              # concept_id
  to_id: str                # session_id
  edge_type: 'explored_in'
  depth: 'mentioned' | 'discussed' | 'deep_dive'
  created_at: datetime
```

---

### builds_on

**Outcome → Outcome**

"This goal connects to a previous one."

```python
BuildsOnEdge:
  id: str
  from_id: str              # outcome_id (new)
  to_id: str                # outcome_id (previous)
  edge_type: 'builds_on'
  relationship: str         # How they connect
  created_at: datetime
```

---

### applied_in

**Concept → ApplicationEvent**

"This concept was applied in this real-world situation."

```python
AppliedInEdge:
  id: str
  from_id: str              # concept_id
  to_id: str                # application_event_id
  edge_type: 'applied_in'
  created_at: datetime
```

**Example:** When learner mentions "I have a pricing call tomorrow," concepts like `price-presentation` and `handling-objections` get linked to that ApplicationEvent.

---

## Graph Growth: Example

**Session 1: User states goal**

```
Graph:
  └── Outcome: "Price freelance services confidently"
```

**Session 1: Gap discovered, taught, proven**

```
Graph:
  └── Outcome: "Price freelance services confidently"
          │
          └── requires → Concept: "value-articulation"
                              │
                              └── demonstrated_by → Proof
```

**Session 2: Another gap found**

```
Graph:
  └── Outcome: "Price freelance services confidently"
          │
          ├── requires → Concept: "value-articulation" ✓
          │                   └── demonstrated_by → Proof
          │
          └── requires → Concept: "pricing-calculation"
                              └── (teaching in progress)
```

**Session 5: Goal achieved**

```
Graph:
  └── Outcome: "Price freelance services confidently" ✓ ACHIEVED
          │
          ├── Concept: "value-articulation" ✓
          ├── Concept: "pricing-calculation" ✓
          ├── Concept: "price-presentation" ✓
          │       └── relates_to → "negotiation-psychology"
          └── Concept: "handling-objections" ✓
```

**Later: New goal with connection**

```
Graph:
  ├── Outcome: "Price freelance services" ✓
  │       └── [concepts with proofs]
  │
  └── Outcome: "Negotiate better contracts"  ← NEW
          │
          └── builds_on → previous outcome
              (SAGE noticed: "You already know pricing psychology,
               which connects to negotiation...")
```

---

## SQLite Schema

```sql
CREATE TABLE learners (
    id TEXT PRIMARY KEY,
    profile JSON,
    preferences JSON,
    insights JSON,               -- Patterns learned over time
    active_outcome_id TEXT,
    current_focus TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_session_at DATETIME,
    total_sessions INTEGER DEFAULT 0,
    total_proofs INTEGER DEFAULT 0
);

CREATE TABLE outcomes (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    stated_goal TEXT NOT NULL,
    clarified_goal TEXT,
    motivation TEXT,
    success_criteria TEXT,
    status TEXT DEFAULT 'active',
    territory JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    achieved_at DATETIME,
    last_worked_on DATETIME,
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);

CREATE TABLE concepts (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    discovered_from TEXT,
    status TEXT DEFAULT 'identified',
    summary TEXT,
    times_discussed INTEGER DEFAULT 0,
    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    understood_at DATETIME,
    FOREIGN KEY (learner_id) REFERENCES learners(id),
    FOREIGN KEY (discovered_from) REFERENCES outcomes(id)
);

CREATE TABLE proofs (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    demonstration_type TEXT,
    evidence TEXT,
    confidence REAL,
    exchange JSON,
    earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (learner_id) REFERENCES learners(id),
    FOREIGN KEY (concept_id) REFERENCES concepts(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    outcome_id TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    context JSON,                -- Set/Setting/Intention for this session
    messages JSON,               -- Full conversation history
    summary TEXT,
    concepts_explored JSON,
    proofs_earned JSON,
    connections_found JSON,
    ending_state JSON,
    FOREIGN KEY (learner_id) REFERENCES learners(id),
    FOREIGN KEY (outcome_id) REFERENCES outcomes(id)
);

CREATE TABLE application_events (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    concept_ids JSON NOT NULL,
    outcome_id TEXT,
    session_id TEXT NOT NULL,
    context TEXT NOT NULL,
    planned_date DATE,
    stakes TEXT,
    status TEXT DEFAULT 'upcoming',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    followup_session_id TEXT,
    followed_up_at DATETIME,
    outcome_result TEXT,
    what_worked TEXT,
    what_struggled TEXT,
    gaps_revealed JSON,
    insights TEXT,
    FOREIGN KEY (learner_id) REFERENCES learners(id),
    FOREIGN KEY (outcome_id) REFERENCES outcomes(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE edges (
    id TEXT PRIMARY KEY,
    from_id TEXT NOT NULL,
    from_type TEXT NOT NULL,
    to_id TEXT NOT NULL,
    to_type TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_outcomes_learner ON outcomes(learner_id);
CREATE INDEX idx_outcomes_status ON outcomes(status);
CREATE INDEX idx_concepts_learner ON concepts(learner_id);
CREATE INDEX idx_concepts_outcome ON concepts(discovered_from);
CREATE INDEX idx_proofs_learner ON proofs(learner_id);
CREATE INDEX idx_proofs_concept ON proofs(concept_id);
CREATE INDEX idx_sessions_learner ON sessions(learner_id);
CREATE INDEX idx_edges_from ON edges(from_id, from_type);
CREATE INDEX idx_edges_to ON edges(to_id, to_type);
CREATE INDEX idx_edges_type ON edges(edge_type);
CREATE INDEX idx_applications_learner ON application_events(learner_id);
CREATE INDEX idx_applications_status ON application_events(status);
CREATE INDEX idx_applications_followup ON application_events(status, planned_date);
```

---

## Key Queries

### Where did we leave off?

```sql
SELECT
    o.clarified_goal,
    o.status,
    l.current_focus,
    s.ending_state,
    s.summary as last_session_summary
FROM learners l
LEFT JOIN outcomes o ON l.active_outcome_id = o.id
LEFT JOIN sessions s ON s.learner_id = l.id
WHERE l.id = ?
ORDER BY s.ended_at DESC
LIMIT 1;
```

### What has the learner proven?

```sql
SELECT
    c.display_name,
    c.summary,
    p.evidence,
    p.earned_at
FROM proofs p
JOIN concepts c ON p.concept_id = c.id
WHERE p.learner_id = ?
ORDER BY p.earned_at DESC;
```

### Does this connect to something they know?

```sql
-- Find related concepts the learner has proofs for
SELECT
    known.display_name,
    e.metadata->>'relationship' as how_related,
    e.metadata->>'strength' as strength
FROM edges e
JOIN concepts known ON e.from_id = known.id
JOIN proofs p ON known.id = p.concept_id
WHERE e.edge_type = 'relates_to'
  AND e.to_id = ?  -- new concept being considered
  AND p.learner_id = ?
ORDER BY CAST(e.metadata->>'strength' AS REAL) DESC;
```

### What concepts came from this outcome?

```sql
SELECT c.*, p.id as proof_id, p.earned_at
FROM concepts c
LEFT JOIN proofs p ON c.id = p.concept_id
WHERE c.discovered_from = ?
ORDER BY c.discovered_at;
```

### Pending follow-ups (check at session start)

```sql
-- Find applications that need follow-up
-- (planned date has passed OR status is pending_followup)
SELECT
    ae.*,
    o.clarified_goal as outcome_goal
FROM application_events ae
LEFT JOIN outcomes o ON ae.outcome_id = o.id
WHERE ae.learner_id = ?
  AND ae.status IN ('upcoming', 'pending_followup')
  AND (
    ae.planned_date <= date('now')
    OR ae.status = 'pending_followup'
  )
ORDER BY ae.planned_date ASC, ae.created_at ASC;
```

### Past applications for a concept (for teaching context)

```sql
-- When teaching a concept, find past applications to reference
SELECT
    ae.context,
    ae.outcome_result,
    ae.what_worked,
    ae.what_struggled,
    ae.insights
FROM application_events ae
WHERE ae.learner_id = ?
  AND ae.status = 'completed'
  AND EXISTS (
    SELECT 1 FROM json_each(ae.concept_ids)
    WHERE value = ?
  )
ORDER BY ae.followed_up_at DESC;
```

### Learning patterns from applications

```sql
-- Find patterns: what struggles keep appearing?
SELECT
    ae.what_struggled,
    ae.gaps_revealed,
    ae.outcome_result,
    COUNT(*) as occurrences
FROM application_events ae
WHERE ae.learner_id = ?
  AND ae.status = 'completed'
  AND ae.what_struggled IS NOT NULL
GROUP BY ae.what_struggled
ORDER BY occurrences DESC;
```

---

## Python Models

```python
from datetime import datetime, date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


def gen_id() -> str:
    return str(uuid.uuid4())


# Enums
class OutcomeStatus(str, Enum):
    ACTIVE = "active"
    ACHIEVED = "achieved"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class ConceptStatus(str, Enum):
    IDENTIFIED = "identified"
    TEACHING = "teaching"
    UNDERSTOOD = "understood"


class DemoType(str, Enum):
    EXPLANATION = "explanation"
    APPLICATION = "application"
    BOTH = "both"


class EdgeType(str, Enum):
    REQUIRES = "requires"
    RELATES_TO = "relates_to"
    DEMONSTRATED_BY = "demonstrated_by"
    EXPLORED_IN = "explored_in"
    BUILDS_ON = "builds_on"
    APPLIED_IN = "applied_in"


class DialogueMode(str, Enum):
    """What mode SAGE is currently in"""
    CHECK_IN = "check_in"                    # Gathering Set/Setting/Intention
    FOLLOWUP = "followup"                    # Asking about past application
    OUTCOME_DISCOVERY = "outcome_discovery"  # Finding what they want to do
    FRAMING = "framing"                      # Light sketch of territory
    PROBING = "probing"                      # Finding the gap
    TEACHING = "teaching"                    # Filling the gap
    VERIFICATION = "verification"            # Checking understanding
    OUTCOME_CHECK = "outcome_check"          # Can they do the thing?


class ExplorationDepth(str, Enum):
    """How deeply a concept was explored in a session"""
    MENTIONED = "mentioned"      # Briefly referenced
    DISCUSSED = "discussed"      # Talked through
    DEEP_DIVE = "deep_dive"      # Extensive exploration


class AgeGroup(str, Enum):
    CHILD = "child"          # Under 13
    TEEN = "teen"            # 13-17
    ADULT = "adult"          # 18+


class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# Models
class LearnerProfile(BaseModel):
    name: Optional[str] = None
    context: Optional[str] = None
    background: Optional[str] = None
    age_group: Optional[AgeGroup] = None      # Affects vocabulary, examples, tone
    skill_level: Optional[SkillLevel] = None  # General learning ability


class LearnerPreferences(BaseModel):
    session_length: str = "medium"
    style: str = "mixed"
    pace: str = "moderate"


class LearnerInsights(BaseModel):
    """Patterns learned about this learner over time"""

    # WHEN do they learn best?
    best_energy_level: Optional[str] = None
    best_time_of_day: Optional[str] = None
    optimal_session_length: Optional[str] = None

    # HOW do they learn best?
    prefers_examples: bool = True
    prefers_theory_first: bool = False
    needs_frequent_checks: bool = False
    responds_to_challenge: bool = True

    # What's worked / not worked
    effective_approaches: list[str] = Field(default_factory=list)
    ineffective_approaches: list[str] = Field(default_factory=list)

    # Patterns noticed (free text observations)
    patterns: list[str] = Field(default_factory=list)


class Learner(BaseModel):
    id: str = Field(default_factory=gen_id)
    profile: LearnerProfile = Field(default_factory=LearnerProfile)
    preferences: LearnerPreferences = Field(default_factory=LearnerPreferences)
    insights: LearnerInsights = Field(default_factory=LearnerInsights)
    active_outcome_id: Optional[str] = None
    current_focus: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_session_at: Optional[datetime] = None
    total_sessions: int = 0
    total_proofs: int = 0


class Outcome(BaseModel):
    id: str = Field(default_factory=gen_id)
    learner_id: str
    stated_goal: str
    clarified_goal: Optional[str] = None
    motivation: Optional[str] = None
    success_criteria: Optional[str] = None
    status: OutcomeStatus = OutcomeStatus.ACTIVE
    territory: Optional[list[str]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    achieved_at: Optional[datetime] = None
    last_worked_on: datetime = Field(default_factory=datetime.utcnow)


class Concept(BaseModel):
    id: str = Field(default_factory=gen_id)
    learner_id: str
    name: str
    display_name: str
    description: Optional[str] = None
    discovered_from: Optional[str] = None
    status: ConceptStatus = ConceptStatus.IDENTIFIED
    summary: Optional[str] = None
    times_discussed: int = 0
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    understood_at: Optional[datetime] = None


class ProofExchange(BaseModel):
    prompt: str
    response: str
    analysis: str


class Proof(BaseModel):
    id: str = Field(default_factory=gen_id)
    learner_id: str
    concept_id: str
    session_id: str
    demonstration_type: DemoType
    evidence: str
    confidence: float = 0.8
    exchange: ProofExchange
    earned_at: datetime = Field(default_factory=datetime.utcnow)


class EnergyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IntentionStrength(str, Enum):
    CURIOUS = "curious"      # Just exploring, no pressure
    LEARNING = "learning"    # Actively trying to understand
    URGENT = "urgent"        # Need this now, high stakes


class SessionContext(BaseModel):
    """Set, Setting, Intention captured at session start"""
    # SET - Current mental/physical state
    energy: Optional[EnergyLevel] = None
    mindset: Optional[str] = None           # Free text: "stressed", "curious", etc.
    time_available: Optional[str] = None    # "15 minutes", "an hour", "open-ended"

    # SETTING - Physical environment (affects HOW to teach)
    environment: Optional[str] = None       # "quiet office", "coffee shop", "commuting"
    can_speak: Optional[bool] = None        # Can they talk out loud? (affects practice exercises)
    distraction_level: Optional[str] = None # "focused", "some interruptions", "noisy"
    device: Optional[str] = None            # "desktop", "phone" - affects content format

    # INTENTION - Purpose for this session
    intention_strength: Optional[IntentionStrength] = None
    session_goal: Optional[str] = None      # What they want from THIS session


class Message(BaseModel):
    """A single exchange in the conversation"""
    role: str                               # "user" or "sage"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    mode: Optional[str] = None              # Dialogue mode that produced this


class SessionEndingState(BaseModel):
    mode: str
    current_focus: Optional[str] = None
    next_step: Optional[str] = None


class Session(BaseModel):
    id: str = Field(default_factory=gen_id)
    learner_id: str
    outcome_id: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    context: Optional[SessionContext] = None      # Set/Setting/Intention
    messages: list[Message] = Field(default_factory=list)
    summary: Optional[str] = None
    concepts_explored: list[str] = Field(default_factory=list)
    proofs_earned: list[str] = Field(default_factory=list)
    connections_found: list[str] = Field(default_factory=list)
    ending_state: Optional[SessionEndingState] = None


class ApplicationStatus(str, Enum):
    UPCOMING = "upcoming"           # Planned, hasn't happened yet
    PENDING_FOLLOWUP = "pending_followup"  # Happened, needs follow-up
    COMPLETED = "completed"         # Followed up and recorded
    SKIPPED = "skipped"             # Didn't happen or wasn't followed up


class ApplicationEvent(BaseModel):
    """Real-world application of learning, with follow-up tracking"""
    id: str = Field(default_factory=gen_id)
    learner_id: str
    concept_ids: list[str]          # Concepts being applied
    outcome_id: Optional[str] = None
    session_id: str                 # Where it was mentioned

    # What's planned
    context: str                    # "pricing call tomorrow"
    planned_date: Optional[date] = None
    stakes: Optional[str] = None    # "high", "medium", "low"

    # Status
    status: ApplicationStatus = ApplicationStatus.UPCOMING
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Follow-up
    followup_session_id: Optional[str] = None
    followed_up_at: Optional[datetime] = None

    # What happened (filled after follow-up)
    outcome_result: Optional[str] = None      # "went well", "struggled", "mixed"
    what_worked: Optional[str] = None
    what_struggled: Optional[str] = None
    gaps_revealed: Optional[list[str]] = None
    insights: Optional[str] = None


class Edge(BaseModel):
    id: str = Field(default_factory=gen_id)
    from_id: str
    from_type: str
    to_id: str
    to_type: str
    edge_type: EdgeType
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## Graph Operations

```python
class LearningGraph:
    """Simple interface for the learning graph"""

    # Learner
    def get_or_create_learner(self, learner_id: str = None) -> Learner: ...
    def update_learner(self, learner: Learner) -> None: ...

    # Outcomes
    def create_outcome(self, learner_id: str, stated_goal: str) -> Outcome: ...
    def get_active_outcome(self, learner_id: str) -> Optional[Outcome]: ...
    def update_outcome(self, outcome: Outcome) -> None: ...
    def mark_achieved(self, outcome_id: str) -> None: ...

    # Concepts
    def create_concept(self, learner_id: str, name: str, discovered_from: str) -> Concept: ...
    def get_concept(self, concept_id: str) -> Concept: ...
    def update_concept(self, concept: Concept) -> None: ...
    def get_concepts_for_outcome(self, outcome_id: str) -> list[Concept]: ...

    # Proofs
    def create_proof(self, learner_id: str, concept_id: str, session_id: str, **kwargs) -> Proof: ...
    def get_proofs_for_learner(self, learner_id: str) -> list[Proof]: ...
    def has_proof(self, concept_id: str) -> bool: ...

    # Sessions
    def start_session(self, learner_id: str, outcome_id: str = None) -> Session: ...
    def end_session(self, session: Session) -> None: ...
    def get_last_session(self, learner_id: str) -> Optional[Session]: ...

    # Edges
    def add_edge(self, edge: Edge) -> None: ...
    def find_related_concepts(self, concept_id: str, learner_id: str) -> list[tuple[Concept, dict]]: ...

    # Application Events
    def create_application_event(self, learner_id: str, context: str, concept_ids: list[str], **kwargs) -> ApplicationEvent: ...
    def get_pending_followups(self, learner_id: str) -> list[ApplicationEvent]: ...
    def record_followup(self, event_id: str, result: str, what_worked: str, what_struggled: str, gaps: list[str], insights: str) -> None: ...
    def get_applications_for_concept(self, concept_id: str, learner_id: str) -> list[ApplicationEvent]: ...

    # Queries
    def get_learner_state(self, learner_id: str) -> dict: ...
    def find_connections(self, new_concept_name: str, learner_id: str) -> list[dict]: ...
```

---

## What's NOT Here

Since we're iterating toward outcomes (not building paths):

- ❌ `current_path` on Outcome
- ❌ `current_step` tracking
- ❌ `prerequisite` edges (no upfront ordering)
- ❌ Path building algorithms
- ❌ Topological sorting

The graph is a **record of what happened**, not a **plan for what will happen**.

---

*Data Model v1.0 — Iterate/Discover Approach*
