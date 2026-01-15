# SAGE Project Context

## What Is This?

SAGE is an AI tutor that teaches through conversation, not curriculum. It asks "What do you want to be able to DO?" then finds gaps through dialogue and fills them one at a time until the learner can actually do the thing.

## Core Philosophy

- **Iterate/Discover, not Path-Upfront**: No pre-planned curriculum. Gaps are found through conversation.
- **Outcome-Driven**: Progress = "can you do the thing?" not "steps completed"
- **Earned Knowledge**: Learners demonstrate understanding (Proofs) before moving on
- **Personal Learning Graph**: Grows from conversations, tracks what's been learned and how it connects

## Key Architecture Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Learning approach | Iterate/Discover | More conversational, handles unknown unknowns, respects learner agency |
| Data storage | SQLite + JSON fields | Simple for MVP, easy to query, no external deps |
| Models | Pydantic | Type safety, validation, easy serialization |
| Graph structure | 6 node types, 6 edge types | Minimal complexity for iterate approach |

## The Core Loop

```
0. CHECK-IN → "How are you showing up today?" (every session)
   Gather Set/Setting/Intention, adapt approach
1. OUTCOME → "What do you want to be able to do?"
2. FRAME (light) → "That typically involves X, Y, Z—let's see where you are"
3. PROBE → "What's blocking you from this right now?"
4. TEACH → Fill that specific gap (adapted to context)
5. VERIFY → "Do you actually get this now?" → Proof created
6. CHECK OUTCOME → "Can you do the thing yet?"
   If yes → Done
   If no → Loop back to PROBE
```

## SAGE Personality

- Direct, gets to the point
- Respects intelligence, doesn't talk down
- Honest about gaps without judgment
- Slightly dry, efficient
- Think JARVIS, not professor

## Key Files

```
SAGE/
├── CLAUDE.md                              ← This file (project context)
├── docs/
│   ├── narrative/SAGE_narrative.md        ← Product story, user-facing explanation
│   └── architecture/
│       ├── system-design.md               ← High-level architecture, core loop, components
│       ├── data-model.md                  ← Graph nodes/edges, SQLite schema, Pydantic models
│       └── context-management.md          ← Runtime context, what AI needs each turn
├── data/
│   └── prompts/                           ← LLM prompt templates (per mode)
│       ├── system.md                      ← SAGE personality + capabilities
│       ├── check_in.md                    ← Gather Set/Setting/Intention
│       ├── followup.md                    ← Ask about past applications
│       ├── outcome_discovery.md           ← Find what they want to DO
│       ├── framing.md                     ← Light sketch of territory
│       ├── probing.md                     ← Find the gap
│       ├── teaching.md                    ← Fill the gap (with adaptation)
│       ├── verification.md                ← Check understanding, create proof
│       └── outcome_check.md               ← Can they do the thing?
├── src/sage/                              ← Python backend
│   ├── core/                              ← Config, utilities, logging
│   ├── graph/                             ← Learning Graph (models, store, queries)
│   ├── context/                           ← Context management (FullContext, TurnContext)
│   ├── dialogue/                          ← Conversation engine (modes, transitions)
│   ├── gaps/                              ← Gap finding (replaces path planning)
│   ├── assessment/                        ← Probing, verification, proof creation
│   ├── learner/                           ← Learner state, sessions
│   └── api/                               ← FastAPI backend + WebSocket
├── web/                                   ← Next.js frontend
│   ├── app/                               ← App Router pages
│   ├── components/                        ← React components
│   ├── lib/                               ← API client, utilities
│   └── hooks/                             ← Custom React hooks
├── tests/                                 ← Test suite
├── pyproject.toml                         ← Python project config
└── .env.example                           ← Environment variable template
```

## Data Model Summary

**Nodes:**
- `Learner` - The person (profile, preferences, current state, insights)
  - Includes `age_group` (child/teen/adult) and `skill_level` (beginner/intermediate/advanced)
  - These affect vocabulary, examples, tone, pace, and teaching depth
- `Outcome` - A goal ("price freelance services confidently")
- `Concept` - A gap that was found and taught
- `Proof` - Verified demonstration of understanding
- `Session` - A conversation (includes context + messages)
- `ApplicationEvent` - Real-world application of learning with follow-up tracking

**Session includes:**
- `context` - Set/Setting/Intention captured at session start (including physical environment)
- `messages` - Full conversation history for continuity

**ApplicationEvent enables the Learning Feedback Loop:**
```
Learn concept → Apply in real world → Report back → Identify gaps → Fill gaps → Apply better
      ↑                                                                              │
      └──────────────────────────────────────────────────────────────────────────────┘
```

**Edges:**
- `requires` - Outcome → Concept (gap discovered for this goal)
- `relates_to` - Concept ↔ Concept (cross-domain connections)
- `demonstrated_by` - Concept → Proof
- `explored_in` - Concept → Session
- `builds_on` - Outcome → Outcome (goals that connect)
- `applied_in` - Concept → ApplicationEvent (real-world usage)

## Build Order

1. **Graph Store** ← START HERE
   - Pydantic models (`src/graph/models.py`)
   - SQLite store with schema (`src/graph/store.py`)
   - Graph queries (`src/graph/queries.py`)

2. **Context Manager**
   - FullContext loader (session start + pending follow-ups)
   - TurnContext builder (each turn)
   - State persistence after turns
   - LearnerInsights tracking
   - Application event tracking and follow-up logic

3. **Prompts**
   - SAGE system prompt (voice, personality)
   - Check-in prompt (gather Set/Setting/Intention)
   - Mode-specific prompts (discovery, probing, teaching, verification)
   - Adaptation instructions (how to adjust for context)

4. **Dialogue Shell**
   - Conversation loop with LLM
   - Structured output parsing (SAGEResponse)
   - Mode detection and transitions
   - State change detection

5. **Gap Finder**
   - Probing question generation
   - Gap identification from responses
   - Connection discovery (to proven concepts)

6. **Assessment**
   - Verification questions
   - Proof creation
   - Confidence scoring

7. **Integration**
   - Full loop end-to-end
   - Cross-session continuity
   - Insights learning over time

8. **Web UI**
   - FastAPI backend with WebSocket streaming
   - Next.js frontend with conversation UI
   - Voice input/output (JARVIS-like)
   - Rich content (diagrams, code, math)
   - Progress sidebar and knowledge graph visualization
   - Practice/roleplay mode

## Technical Stack

### Backend (Python)
- **Python**: 3.11+
- **Data Models**: Pydantic v2
- **Database**: SQLite (built-in)
- **API**: FastAPI + WebSocket (streaming)
- **LLM**: OpenAI SDK (works with Grok/xAI, OpenAI, Anthropic via base_url swap)

### Frontend (Web)
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS + shadcn/ui
- **Content**: React Markdown, Mermaid.js, KaTeX
- **Voice**: Grok Voice API (real-time WebSocket with voice selection)
- **Visualization**: vis-network (knowledge graph)

### LLM Configuration

Using OpenAI SDK as the standard interface. Provider configured via environment:

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL", "https://api.x.ai/v1"),  # Default to Grok
)

# Works with:
# - Grok: base_url="https://api.x.ai/v1", model="grok-4"
# - OpenAI: base_url="https://api.openai.com/v1", model="gpt-4"
# - Any OpenAI-compatible endpoint
```

## Current State

- [x] Narrative document complete
- [x] System design complete (iterate/discover approach)
- [x] Data model complete (includes Session Context, Messages, LearnerInsights)
- [x] Context management design complete (what AI needs each turn, structured output strategy)
- [x] Prompt templates created (starter templates for all 8 modes)
- [x] **M1: Graph Store complete** (models, store, queries, LearningGraph interface)
- [x] **M2: Context Manager complete** (snapshots, FullContext, TurnContext, persistence, insights, applications)
- [x] **M3: Dialogue Shell complete** (prompt builder, structured output, modes, state detection, conversation loop)
- [x] **M4: Gap Finder complete** (probing context, gap identification, connection discovery, teaching connections)
- [x] **M5: Assessment complete** (verification, proof creation, confidence scoring)
- [x] **M6: Integration complete** (GapFinder/ProofHandler wired into ConversationEngine, mode-specific hints, integration tests)
- [ ] M7: Web UI (in progress)
  - [x] FastAPI backend with WebSocket streaming
  - [x] Next.js frontend with chat interface
  - [x] Grok Voice integration (real-time voice input/output)
  - [x] Practice/roleplay mode (dynamic scenarios, feedback)
  - [ ] Knowledge graph visualization
  - [ ] Rich content rendering (Mermaid diagrams, KaTeX math)
  - [ ] Progress sidebar

## Key Concepts to Remember

### Set, Setting, Intention (Per-Session)

The same person learns differently depending on their current state. SAGE checks in at the START of each session to gather context and adapt.

**SET** — Current mental/physical state
- Energy level (low/medium/high)
- Mindset ("stressed about deadline", "curious and relaxed", "nervous about tomorrow")
- Time available ("15 minutes", "couple hours", "open-ended")

**SETTING** — Current environment
- Where they are ("quiet office", "commuting", "home evening")
- Can they speak out loud? (affects practice exercises)
- Distraction level ("focused", "some interruptions", "noisy")
- Device ("desktop", "phone" - affects content format)
- Baseline preferences stored in Learner profile

**INTENTION** — Purpose for THIS session
- Strength: curious (exploring) → learning (active) → urgent (high stakes)
- Specific goal: what they want from this session

**How this adapts learning:**

| Context | Adaptation |
|---------|------------|
| Low energy, 15 min | Shorter chunks, practical focus, quick wins |
| High energy, open time | Deeper exploration, can follow tangents |
| Urgent deadline | Skip theory, focus on immediate applicability |
| Stressed mindset | Gentler pace, smaller steps, more encouragement |

### Runtime Context (What AI Needs Each Turn)

**Loaded at session start (eager):**
- Learner profile + insights (patterns learned over time)
- All proven concepts (what they KNOW)
- Active outcome and progress
- Last session for continuity
- All concept relations (for finding connections)
- Pending follow-ups (applications that need checking on)
- Completed applications (for teaching context)

**Built each turn:**
- Current mode and session context (Set/Setting/Intention)
- Recent messages (last 15-20)
- Relevant proven concepts for current topic
- Relevant past applications for current topic
- Adaptation hints based on state

**LLM outputs structured response:**
- Message to show user
- Mode transitions
- Gaps identified, proofs earned, connections discovered
- State changes detected (energy drop, confusion, etc.)
- Applications detected (upcoming real-world use)
- Follow-up responses (how past applications went)

**Key insight:** The LLM both USES context AND UPDATES it. It monitors for state changes, discovers connections, tracks applications, and reports them back for persistence.

### Application Tracking (The Learning Feedback Loop)

Real learning is proven in application. SAGE tracks when learners mention they'll apply something, then follows up:

**At session start:** Check for pending follow-ups before check-in
- "Before we dive in—you had that pricing call on Tuesday. How did it go?"

**During conversation:** Detect application signals
- "I have a pricing call tomorrow" → create ApplicationEvent
- "I'm meeting with a client Friday" → link relevant concepts

**On follow-up:** Turn struggles into teachable moments
- What worked? → reinforces learning
- What struggled? → reveals new gaps to fill
- Pattern detection: "You've caved on discounts 3 times now—let's make this a focus"

**In teaching:** Reference past applications
- "Last time you had a pricing call, you said X happened. Let's make sure that doesn't happen again."

### What's NOT in this system
- No pre-built prerequisite database
- No upfront path planning
- No `current_step` tracking
- No topological sorting of concepts

The graph records **what happened**, not **what's planned**.

## Testing Approach

- Unit tests for graph operations
- Integration tests for conversation flows
- Mock LLM responses for deterministic testing

## Project Management

### GitHub Repository
- **Repo:** https://github.com/ChadTimothy/SAGE
- **Project Board:** https://github.com/users/ChadTimothy/projects/2

### Issue-Driven Development

Every piece of work has a GitHub issue. This enables:
- Context preservation across AI sessions
- Clear scope and acceptance criteria
- Progress tracking via milestones
- Session handoff without context loss

### Milestones (aligned with Build Order)

| Milestone | Focus | Issues |
|-----------|-------|--------|
| M1: Graph Store | Pydantic models, SQLite, queries | #1-4, #22 ✅ |
| M2: Context Manager | FullContext, TurnContext, persistence, snapshots | #5-8, #23-24 |
| M3: Dialogue Shell | Prompts, structured output, modes, state detection | #9-12, #25 |
| M4: Gap Finder | Probing, gap identification, connections | #13-15 |
| M5: Assessment | Verification, proofs, confidence | #16-18 |
| M6: Integration | Full loop, cross-session continuity | #19-20 |
| M7: Web UI | FastAPI, Next.js, voice, rich content, graph viz | #26-33 |

### AI Session Protocol

**Starting a session:**
1. Read this file (CLAUDE.md)
2. Check GitHub Project board for current state
3. Look at in-progress issues
4. Continue from where we left off

**During a session:**
1. Work on one issue at a time
2. Update issue with progress notes
3. Create commits with issue references (`#1`, `#2`, etc.)
4. Move issues on board as status changes

**Ending a session:**
1. Commit all work in progress
2. Update current issue with session notes (what was done, what's next)
3. If mid-task, add clear handoff note for next session

**Handoff note format:**
```
## Session Handoff - [Date]

### Completed This Session
- [What was accomplished]

### Current State
- Working on: [Issue #X]
- File in progress: [path/to/file.py]
- Next step: [Specific next action]

### Blockers/Notes
- [Any issues encountered or decisions needed]
```

### Why This Approach

Based on research into AI-assisted development best practices:

1. **Context Window Limits:** AI sessions may need to restart. Issues preserve context.
2. **Single Source of Truth:** GitHub issues are the authoritative state, not conversation history.
3. **Handoff Continuity:** Clear session notes enable smooth transitions.
4. **Progress Visibility:** Milestones and board show real progress.

Sources:
- [Agentic Project Management](https://github.com/sdi2200262/agentic-project-management) - Context retention across sessions
- [GitHub Best Practices](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/best-practices-for-projects) - Project organization
- [Solo Developer Guide](https://www.bitovi.com/blog/github-projects-for-solo-developers) - Kanban for individual work

## When Resuming This Project

1. Read this file first
2. Check GitHub Project board: https://github.com/users/ChadTimothy/projects/2
3. Look at in-progress issues for current state
4. Read the most recent issue comments for handoff notes
5. Continue from where we left off

---

*Last updated: M7 Web UI in progress. Completed: FastAPI backend, Next.js frontend, Grok Voice integration, Practice Mode. Remaining: Knowledge graph visualization, rich content rendering, progress sidebar*
