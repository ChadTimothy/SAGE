# SAGE System Design

**High-Level Architecture — Iterate Toward Outcome**

---

## Core Philosophy

SAGE doesn't build a curriculum. It doesn't create a path upfront. It asks:

> **"What do you want to be able to do?"**

Then it probes, finds gaps, fills them, and repeats—until you can actually do the thing.

The path emerges from the conversation. The graph grows from what you explore. Progress is measured by capability, not steps completed.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                   SAGE                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                          ┌─────────────────────┐                            │
│                          │   CONVERSATION      │                            │
│                          │   INTERFACE         │                            │
│                          └──────────┬──────────┘                            │
│                                     │                                        │
│                          ┌──────────▼──────────┐                            │
│                          │   DIALOGUE ENGINE   │                            │
│                          │                     │                            │
│                          │   Orchestrates the  │                            │
│                          │   conversation      │                            │
│                          └──────────┬──────────┘                            │
│                                     │                                        │
│          ┌──────────────────────────┼──────────────────────────┐            │
│          │                          │                          │            │
│          ▼                          ▼                          ▼            │
│  ┌───────────────┐        ┌─────────────────┐        ┌─────────────────┐   │
│  │   GAP         │        │   ASSESSMENT    │        │    LEARNER      │   │
│  │   FINDER      │        │   ENGINE        │        │    STATE        │   │
│  │               │        │                 │        │                 │   │
│  │ • What's      │        │ • Probe         │        │ • Profile       │   │
│  │   blocking?   │        │ • Analyze       │        │ • Current goal  │   │
│  │ • Next gap    │        │ • Verify        │        │ • Preferences   │   │
│  └───────┬───────┘        └────────┬────────┘        └────────┬────────┘   │
│          │                         │                          │            │
│          └─────────────────────────┼──────────────────────────┘            │
│                                    │                                        │
│                         ┌──────────▼──────────┐                            │
│                         │   LEARNING GRAPH    │                            │
│                         │                     │                            │
│                         │  • Outcomes         │                            │
│                         │  • Concepts         │                            │
│                         │  • Proofs           │                            │
│                         │  • Connections      │                            │
│                         │  • Sessions         │                            │
│                         └─────────────────────┘                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## The Core Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  0. CHECK-IN (every session)                                   │
│     "How are you showing up today?"                            │
│     Gather Set, Setting, Intention for THIS session.           │
│     Adapt approach accordingly.                                │
│                              │                                  │
│                              ▼                                  │
│  1. OUTCOME (if new or changed)                                │
│     "What do you want to be able to do?"                       │
│                              │                                  │
│                              ▼                                  │
│  2. FRAME (light)                                              │
│     "That typically involves X, Y, Z—but let's see where      │
│      you actually are."                                        │
│                              │                                  │
│                              ▼                                  │
│  3. PROBE                                                       │
│     "What's blocking you from this right now?"                 │
│     Find the gap through conversation.                         │
│                              │                                  │
│                              ▼                                  │
│  4. TEACH                                                       │
│     Fill that specific gap.                                    │
│     Concept added to graph.                                    │
│     (Adapted to current Set/Setting/Intention)                 │
│                              │                                  │
│                              ▼                                  │
│  5. VERIFY                                                      │
│     "Do you actually get this now?"                            │
│     If yes → Proof created.                                    │
│     If no → More teaching or different angle.                  │
│                              │                                  │
│                              ▼                                  │
│  6. CHECK OUTCOME                                               │
│     "Can you do the thing yet?"                                │
│     If yes → Done.                                             │
│     If no → Loop back to PROBE.                                │
│                              │                                  │
│                              ▼                                  │
│                    [Repeat until capable]                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key difference from path-based approach:**
- No upfront decomposition into detailed concepts
- No pre-built path to follow
- Each step determined by what's actually blocking progress
- Done when they can DO the thing, not when a list is complete

**Why Check-in matters:**
The same person learns differently depending on their current state. Someone exhausted after work needs shorter, practical chunks. Someone curious on a Saturday morning is ready for deeper exploration. SAGE adapts.

---

## Core Components

### 1. Dialogue Engine

**What it does:** Runs the conversation. Decides what mode we're in, what to say, when to shift.

**Modes:**

| Mode | When | What Happens |
|------|------|--------------|
| **Check-in** | Session start | Gather Set/Setting/Intention, adapt approach |
| **Outcome Discovery** | No active goal, or goal unclear | "What do you want to be able to do?" |
| **Framing** | Goal is clear | Light sketch of territory, set expectations |
| **Probing** | Need to find the gap | Conversational questions to locate what's missing |
| **Teaching** | Gap identified | Fill the specific gap (adapted to context) |
| **Verification** | After teaching | Confirm understanding, create proof |
| **Outcome Check** | After verification | "Can you do the thing now?" |

**How Check-in adapts the session:**

| Context | Adaptation |
|---------|------------|
| Low energy, 15 minutes | Shorter chunks, practical focus, quick wins |
| High energy, open time | Deeper exploration, can follow tangents |
| Urgent deadline | Skip theory, focus on immediate applicability |
| Curious/exploring | More context, connections, broader picture |
| Stressed mindset | Gentler pace, more encouragement, smaller steps |

---

### 2. Gap Finder

**What it does:** Identifies what's blocking the learner from their outcome.

**This replaces "decomposition" and "path building."**

Instead of asking "what are all the concepts needed for this goal?", we ask:
- "What's stopping you from doing this right now?"
- "If you tried to do this tomorrow, where would you get stuck?"
- "What part of this feels fuzzy?"

The gap finder works through:
1. **Direct probing** — Ask the learner where they feel blocked
2. **Indirect probing** — Ask them to explain or apply something, see where it breaks down
3. **Graph consultation** — Check if this gap relates to something they've covered before

**Example:**

```
SAGE: "You want to price your services confidently. If you had
       a pricing conversation tomorrow, what part would feel
       hardest?"

USER: "Probably when they push back and say it's too expensive."

SAGE: "Okay, so handling objections is the gap. But let me check
       something first—do you know why your price is what it is?
       Like, could you explain the value you provide?"

USER: "Not really... I just picked a number."

SAGE: "That's actually the deeper gap. If you can't articulate
       your value, you can't defend your price. Let's start there."
```

The gap found wasn't what the user initially said. Probing revealed the real blocker.

---

### 3. Assessment Engine

**What it does:** Probes understanding through conversation, analyzes responses, creates proofs.

**Not quizzes. Dialogue.**

```
SAGE: "You said you understand value-based pricing now. Quick
       check: if a client asks why you charge more than someone
       on Fiverr, what would you say?"

USER: "I'd explain that they're not just buying a logo, they're
       buying a brand identity that'll work across all their
       materials, and that I'll make sure it actually fits their
       business, not just look pretty."

SAGE: "That's it. You just articulated value without mentioning
       your costs or time. That's the shift. You've got this one."

       [Creates Proof for "value-articulation"]
```

---

### 4. Learner State

**What it does:** Tracks who this person is and where they are in their journey.

- Profile (context, background)
- Preferences (how they learn best)
- Current outcome (what they're working toward)
- Current focus (what concept/gap we're on right now)

---

### 5. Learning Graph

**What it does:** Growing record of everything explored, learned, and how it connects.

**Grows organically from conversation:**
- Outcome added when goal is stated
- Concepts added when gaps are identified and taught
- Proofs added when understanding is verified
- Connections added when SAGE notices relationships

**NOT pre-populated. NOT planned upfront.**

---

## How It Works: Full Example

```
SESSION 1:
=========

SAGE [Check-in]:
     "Before we dive in—how are you showing up today? Quick check:
      how's your energy, and how much time do you have?"

USER: "Pretty good actually. It's Saturday morning, I've got a
      couple hours. Feeling motivated."

SAGE [Logs context]:
     {
       energy: "high",
       mindset: "motivated, weekend mode",
       time_available: "couple hours",
       environment: "home, relaxed",
       intention_strength: "learning"
     }

SAGE: "Nice. Weekend energy, open time—we can go deep if needed.
       What do you want to work on?"

USER: "I want to price my freelance services better"

SAGE [Outcome Discovery]:
     "What's the situation? Raising rates, setting them for the
      first time, or something else?"

USER: "I've been freelancing for 2 years but I know I'm
      undercharging. I panic in pricing conversations."

SAGE [Creates Outcome]:
     {
       stated: "price freelance services better"
       clarified: "confidently set and defend higher rates"
       motivation: "knows they're undercharging, panics in conversations"
     }

SAGE [Framing - light]:
     "Pricing confidence usually comes down to knowing your value,
      being able to articulate it, and handling pushback. But
      let's not assume—where do you actually feel stuck?"

USER: "All of it, honestly. I just make up a number and hope
      they say yes."

SAGE [Probing]:
     "When you say you make up a number—what goes through your
      head? What are you basing it on?"

USER: "I look at what other designers charge and pick something
      in the middle. I don't want to seem greedy."

SAGE [Gap identified]:
     "Okay, so you're pricing based on market comparison, not
      on your value. That's why you can't defend it—there's
      nothing TO defend except 'other people charge this.'

      Let me ask: what makes you different from someone on
      Fiverr who charges $50 for a logo?"

USER: "I mean... I do more research, I make sure it works for
      their actual business, I revise until it's right..."

SAGE [Teaching - identifies the gap more precisely]:
     "You just listed your value without realizing it. That's
      the gap—you KNOW you're different, but you haven't
      connected it to your price.

      Here's the shift: you're not selling a logo. You're selling
      a brand identity that actually works. The Fiverr person is
      selling pixels. Different products, different prices.

      Does that framing land?"

USER: "Yeah... I never thought of it as a different product."

SAGE [Verification]:
     "Okay, let's test it. Client says: 'Why should I pay you
      $2000 when I can get a logo for $100 online?' What do you
      say?"

USER: "I'd say... you're not comparing the same thing. A $100
      logo is just an image. What I do is figure out what your
      brand needs to communicate, design something that does
      that, and make sure it works everywhere you'll use it.
      You're buying a business tool, not a picture."

SAGE [Creates Proof]:
     {
       concept: "value-articulation"
       evidence: "Successfully reframed price objection in terms of value"
       confidence: 0.85
     }

SAGE: "You've got it. That's the foundation—everything else
       builds on this."

SAGE [Outcome Check]:
     "That's the biggest piece. But there's more to confident
      pricing. Do you know what number to actually charge? Like,
      how do you figure out what your value-based price IS?"

USER: "No, I still don't know how to pick the actual number."

SAGE [Next gap identified]:
     "That's next. The articulation was the foundation—now we
      work on the calculation."

[Session continues, finding and filling gaps one by one]


SESSION 3:
=========

SAGE [Check-in]:
     "How are you showing up today?"

USER: "Honestly, kind of stressed. I have a pricing call tomorrow
      and I'm nervous. Only have like 30 minutes."

SAGE [Logs context - different from Session 1]:
     {
       energy: "medium",
       mindset: "stressed, nervous about tomorrow",
       time_available: "30 minutes",
       intention_strength: "urgent"
     }

SAGE [Adapts approach]:
     "Got it—you've got a real conversation tomorrow. Let's make
      this practical. Last time we covered value articulation and
      pricing calculation. The piece that matters for tomorrow is
      the actual conversation—presenting the price without panic.
      That's where you wanted to focus. Still true?"

USER: "Yeah, I know my price now but I freeze up saying it."

SAGE [Probing]:
     "What specifically happens? Walk me through the moment."

USER: "I say the number and then immediately start justifying
      or offering discounts before they even respond."

SAGE [Gap identified]:
     "You're negotiating against yourself. The gap isn't knowing
      what to say—it's the silence after you say it. Let's work
      on that..."

[Continues until user can confidently handle the conversation]


SESSION 5:
=========

SAGE [Outcome Check]:
     "We've covered value articulation, pricing calculation,
      presenting the price, and handling objections. If you had
      a pricing conversation tomorrow, how would you feel?"

USER: "Honestly? I'd feel ready. I know what I charge and why.
      I know what to say if they push back. I'm not scared of
      the conversation anymore."

SAGE: "That was the goal. You're there."

      [Marks Outcome as achieved]


SESSION 6 — APPLICATION FOLLOW-UP:
==================================

USER: [Opens new session]

SAGE [Check-in with pending follow-up]:
     "Before we dive in—you mentioned you had a pricing call with
      that potential client on Tuesday. How did it go?"

USER: "It went okay. I stated my price confidently and held the
      silence like we practiced. But then they asked for a discount
      and I caved pretty quick."

SAGE [Captures follow-up]:
     {
       event: "pricing call Tuesday"
       outcome_result: "mixed"
       what_worked: "Stated price confidently, held silence"
       what_struggled: "Caved on discount request"
       gaps_revealed: ["discount-negotiation"]
     }

SAGE: "That's useful data. You've got the price presentation down—
       that's proven. The gap that showed up is handling discount
       requests specifically. That's different from general objections.

       What happened in that moment? What did they say?"

USER: "They asked 'Can you do it for 20% less?' and I just said
       yes without thinking."

SAGE [Identifies specific gap]:
     "So you didn't freeze or panic—you handled the conversation.
      You just didn't have a response ready for the discount ask.
      That's a smaller gap than we started with.

      Here's the thing: a discount request isn't an objection about
      value. It's a negotiation move. Different response needed.
      Want to work on that for next time?"

USER: "Yeah, I have another call Friday."

SAGE [Creates new ApplicationEvent]:
     {
       context: "pricing call Friday"
       concepts: ["discount-negotiation"]
       stakes: "high"
       status: "upcoming"
     }

SAGE: "Good. Let's make sure Friday goes differently. When they
       ask for a discount, you have three options..."

[Teaching continues, building on what worked and addressing what didn't]
```

**The Learning Feedback Loop:**

```
Learn concept → Apply in real world → Report back → Identify gaps → Fill gaps → Apply better
      ↑                                                                              │
      └──────────────────────────────────────────────────────────────────────────────┘
```

This feedback loop surfaces gaps that theory alone can't find. The learner *thought* they were ready, attempted it, and discovered a specific gap in real-world pressure. SAGE tracks this and follows up.

---

## The Graph After This Journey

```
LEARNER
    │
    └── OUTCOME: "Price freelance services confidently" ✓ achieved
            │
            ├── CONCEPT: value-articulation
            │       └── PROOF (session 1)
            │
            ├── CONCEPT: pricing-calculation
            │       └── PROOF (session 2)
            │
            ├── CONCEPT: price-presentation
            │       └── PROOF (session 3)
            │           │
            │           └── RELATES_TO: negotiation-psychology
            │               (discovered during teaching)
            │
            └── CONCEPT: handling-objections
                    └── PROOF (session 4)
```

**Note:** The concepts weren't planned upfront. They emerged from probing for gaps.

---

## What This Changes

| Path-Based | Iterate-Based |
|------------|---------------|
| Decompose goal into concepts upfront | Frame lightly, then probe for gaps |
| Build ordered path | No path—follow the gaps |
| Progress = steps completed | Progress = can you do the thing? |
| Graph populated at start | Graph grows organically |
| "You're on step 3 of 7" | "Here's what's blocking you next" |
| Done when path complete | Done when outcome achieved |

---

## Component Responsibilities (Updated)

### Dialogue Engine
- Manage conversation modes
- Orchestrate transitions between probing, teaching, verification
- Maintain SAGE voice throughout

### Gap Finder
- Identify what's blocking progress toward outcome
- Direct probing (ask the learner)
- Indirect probing (have them try something, see where it breaks)
- Consult graph for related knowledge

### Assessment Engine
- Generate probing questions
- Analyze responses for understanding vs gaps
- Create proofs when understanding is verified
- Detect misconceptions

### Learning Graph
- Store outcomes, concepts, proofs, sessions
- Track connections between concepts
- Enable "have we covered something related?" queries
- Grow from conversation, not upfront planning

### Learner State
- Profile and preferences
- Current outcome
- Current focus (what gap we're working on)
- Session continuity

---

## Directory Structure

```
SAGE/
├── docs/
│   ├── narrative/
│   │   └── SAGE_narrative.md
│   ├── architecture/
│   │   ├── system-design.md          ← This document
│   │   └── data-model.md
│   └── research/
│
├── src/
│   ├── core/                         ← Config, utilities
│   │
│   ├── dialogue/                     ← Conversation engine
│   │   ├── engine.py                 ← Mode management
│   │   ├── modes.py                  ← Discovery, probing, teaching, etc.
│   │   └── voice.py                  ← SAGE personality
│   │
│   ├── gaps/                         ← Gap finding (replaces planning/)
│   │   ├── finder.py                 ← Identify what's blocking
│   │   ├── probing.py                ← Questions to surface gaps
│   │   └── framing.py                ← Light territory sketching
│   │
│   ├── assessment/                   ← Understanding detection
│   │   ├── probing.py                ← Verification questions
│   │   ├── analysis.py               ← Response analysis
│   │   └── verification.py           ← Proof creation
│   │
│   ├── learner/                      ← Learner state
│   │   ├── state.py                  ← Profile, preferences, current focus
│   │   └── session.py                ← Session management
│   │
│   ├── graph/                        ← Learning Graph
│   │   ├── models.py                 ← Node and Edge definitions
│   │   ├── store.py                  ← Persistence
│   │   ├── queries.py                ← Graph queries
│   │   └── visualization.py          ← Visual representation
│   │
│   └── api/
│       └── cli.py                    ← Command-line interface
│
├── data/
│   └── prompts/                      ← LLM prompt templates
│       ├── system.md                 ← Base SAGE personality
│       ├── check_in.md               ← Session start, gather Set/Setting/Intention
│       ├── discovery.md              ← Outcome discovery
│       ├── framing.md                ← Light territory sketch
│       ├── gap_finding.md            ← Probing for gaps
│       ├── teaching.md               ← Filling gaps (with context adaptation)
│       └── verification.md           ← Checking understanding
│
└── tests/
```

---

## Build Order

1. **Graph Store**
   - Simplified models (no path tracking)
   - Basic CRUD
   - Connection queries

2. **Prompts**
   - SAGE voice
   - Gap-finding prompts
   - Teaching prompts
   - Verification prompts

3. **Dialogue Shell**
   - Conversation loop
   - Mode transitions
   - Context management

4. **Gap Finder**
   - Probing questions
   - Gap identification
   - Light framing

5. **Assessment**
   - Verification questions
   - Response analysis
   - Proof creation

6. **Integration**
   - Full loop: outcome → probe → teach → verify → check → repeat
   - Cross-session continuity

---

## Practice Mode

Practice Mode enables roleplay scenarios where learners can apply what they've learned in realistic situations. SAGE plays a character role while the learner practices skills.

### How It Works

1. **Scenario Setup**: Learner selects or creates a practice scenario
   - Defines SAGE's role (e.g., "skeptical client", "difficult stakeholder")
   - Defines learner's role (e.g., "consultant", "sales representative")
   - Sets the context/situation

2. **In-Character Roleplay**: SAGE stays in character throughout
   - Provides realistic responses and pushback
   - Adjusts difficulty based on learner performance
   - Tracks strengths and areas for improvement

3. **Post-Practice Feedback**: When session ends, SAGE provides:
   - What the learner did well
   - Areas for improvement
   - Revealed gaps to explore in future learning

### Practice API Endpoints

```
POST /api/practice/start         # Start a new practice session
POST /api/practice/{id}/message  # Send message in practice session
POST /api/practice/{id}/hint     # Request coaching hint (breaks character)
POST /api/practice/{id}/end      # End practice and get feedback
```

---

## Success Criteria

A user can:

1. State what they want to be able to do
2. Have SAGE find their actual gaps through conversation
3. Learn what they need, when they need it
4. Demonstrate understanding (proofs)
5. Repeat until they can DO the thing
6. Come back later, SAGE remembers what they've proven
7. Pursue new goal, SAGE finds connections to past learning

---

*Architecture v1.1 — Iterate Toward Outcome (Practice Mode added)*
