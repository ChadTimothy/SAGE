# Voice/UI Parity Architecture

## Executive Summary

This document presents a comprehensive architecture for achieving complete voice/UI parity in SAGE, ensuring that every interaction available through the graphical user interface is equally accessible via voice conversation, and vice versa.

**Key Use Cases:**
- **Dog walker**: Voice only, no screen - all features work through conversation
- **Train commuter**: UI only, can't speak - all features work through forms

## Problem Statement

Currently, SAGE has feature gaps between modalities:

| Feature | UI Support | Voice Support |
|---------|------------|---------------|
| Check-in (Set/Setting/Intention) | Modal form | None |
| Practice Setup | Modal form | None |
| Chat/Learning | Text input | Full voice I/O |
| Graph Filters | Filter panel | None |
| Verification | Text response | Basic voice |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ UI Components│  │ Voice Input │  │ Voice Output│                 │
│  └──────┬──────┘  └──────┬──────┘  └──────▲──────┘                 │
│         │                │                │                         │
│         └────────────────┼────────────────┘                         │
│                          ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              UNIFIED INPUT NORMALIZER                        │   │
│  │  Form Parser | Voice STT Parser | Chat Parser | Hybrid       │   │
│  │                          ↓                                    │   │
│  │              SEMANTIC INTENT EXTRACTOR (LLM)                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  SAGE ORCHESTRATOR                           │   │
│  │  Intent Router → Mode Decider → Response Strategy            │   │
│  │                          ↓                                    │   │
│  │         UI GENERATION AGENT (Grok-2 Tool)                    │   │
│  │         Composes UITree from ~15 primitive components        │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      OUTPUT LAYER                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              EXTENDED SAGEResponse                           │   │
│  │  message | ui_tree (composable) | voice_hints                │   │
│  │                          ↓                                    │   │
│  │              MODALITY ADAPTERS                               │   │
│  │  UI Renderer | Voice Synthesizer | Hybrid Mixer              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Architecture Decision: Ad-Hoc UI Generation

**Decision (see GitHub #83)**: We use **true ad-hoc UI generation** where the AI composes arbitrary UIs from primitive building blocks, rather than selecting from fixed SAGE-specific components.

### Why Ad-Hoc Over Fixed Components?

| Capability | Fixed Components | Ad-Hoc Generation |
|------------|------------------|-------------------|
| Predefined forms | ✅ | ✅ |
| Custom verification quizzes | ❌ | ✅ |
| Dynamic comparison tables | ❌ | ✅ |
| Progress visualizations | ❌ | ✅ |
| Context-aware UI adaptation | ❌ | ✅ |

### Ad-Hoc Generation Flow

```
User Input (Voice/Form/Chat)
         ↓
Unified Input Normalizer
         ↓
Semantic Intent Extractor (LLM)
         ↓
SAGE Orchestrator
    ├── Decides: "UI would help here"
    └── Calls UI Agent (tool)
              ↓
         Grok-2 generates UITree from primitives (<500ms)
              ↓
Extended SAGEResponse (message + ui_tree + voice_hints)
         ↓
Frontend renders UITree recursively
         ↓
User interacts → data sent back to Orchestrator
```

## Core Components

### 1. Unified Input Normalizer

Converts any input type to a normalized semantic intent:

```python
@dataclass
class NormalizedInput:
    intent: str              # "session_check_in", "practice_setup", etc.
    data: Dict[str, Any]     # Extracted structured data
    data_complete: bool      # All required fields present?
    missing_fields: List[str]
    source_modality: InputModality  # FORM | VOICE | CHAT | HYBRID
```

### 2. Semantic Intent Extractor

LLM-powered extraction of structured data from natural language:

```python
# Voice: "I have 30 minutes, feeling tired"
# Extracts:
{
    "intent": "session_check_in",
    "data": {
        "timeAvailable": "focused",  # mapped from "30 minutes"
        "energyLevel": 30,           # mapped from "tired"
        "mindset": null              # not mentioned
    },
    "data_complete": false,
    "missing_fields": ["mindset"]
}
```

### 3. SAGE Orchestrator

Central decision-maker that routes inputs and determines response format:

**Decision Tree:**
1. **INTENT CLASSIFICATION**: Form, Voice, Chat, or Hybrid?
2. **DATA COMPLETENESS**: All required fields present?
3. **ACTION DECISION**: Process action, or request more data?
4. **OUTPUT STRATEGY**: Text only, UI tree, voice description, or hybrid?
5. **UI GENERATION**: If UI needed, call UI Generation Agent as tool

### 4. UI Generation Agent (Tool)

Fast, composition-aware agent called by the orchestrator:

- **Model**: Grok-2 (fast, <500ms target)
- **Purpose**: Compose UITree from primitive components
- **Architecture**: Called as tool by orchestrator (not monitoring conversation)
- **Input**: Purpose + conversation context
- **Output**: UITreeSpec with voice_fallback

```python
class UIGenerationAgent:
    MODEL = "grok-2"
    TEMPERATURE = 0.3  # Consistent structure

    async def generate(
        self,
        purpose: str,
        context: dict[str, Any],
    ) -> UITreeSpec:
        # Composes from primitives
        pass
```

### 5. Extended SAGEResponse

Enhanced response structure with composable UI tree:

```python
class UITreeNode(BaseModel):
    """Recursive composable UI node."""
    component: str  # Primitive component name
    props: dict[str, Any] = Field(default_factory=dict)
    children: list["UITreeNode"] | None = None

class ExtendedSAGEResponse(SAGEResponse):
    # Existing fields...

    # New fields for modality parity
    ui_tree: UITreeNode | None = None  # Composable tree
    voice_hints: VoiceHints | None = None  # TTS optimization
    pending_data_request: PendingDataRequest | None = None
```

## Primitive Component Library (~15 Components)

Instead of fixed SAGE-specific components, we use reusable primitives:

### Layout
- `Stack` - Vertical/horizontal arrangement
- `Grid` - Grid layout (1-4 columns)
- `Card` - Contained section with optional title
- `Divider` - Visual separator

### Typography
- `Text` - Text with variants (heading, body, caption)
- `Markdown` - Rich text rendering

### Inputs
- `TextInput` - Single-line text
- `TextArea` - Multi-line text
- `Slider` - Numeric range
- `RadioGroup` + `Radio` - Single selection
- `Checkbox` - Boolean
- `Select` - Dropdown selection

### Actions
- `Button` - Action trigger
- `ButtonGroup` - Multiple buttons

### Display
- `Image` - Image display
- `Table` - Data table
- `ProgressBar` - Progress indicator
- `Badge` - Status badge

## Data Flow Examples

### Voice Check-In Flow

```
User speaks: "I have about 30 minutes, feeling tired"
    ↓
Grok Voice STT: Transcription
    ↓
Semantic Intent Extractor:
    intent=session_check_in,
    data={timeAvailable: "focused", energyLevel: 30, mindset: null}
    data_complete=false, missing=["mindset"]
    ↓
Orchestrator: request_more (conversational)
    ↓
SAGE speaks: "Got it - 30 minutes, lower energy. Anything on your mind?"
    ↓
User speaks: "Nervous about a pricing call tomorrow"
    ↓
Semantic Intent Extractor: merges with pending
    data_complete=true
    ↓
Orchestrator: process action
    ↓
Backend: Store SessionContext, transition mode
    ↓
SAGE speaks: "Got it - I see you have that pricing call on your mind..."
```

### UI Check-In Flow (Ad-Hoc)

```
User opens session
    ↓
Orchestrator decides: UI would help for check-in
    ↓
UI Agent generates: UITree from primitives
    {
      component: "Stack",
      children: [
        { component: "Text", props: { content: "Quick Check-In" } },
        { component: "RadioGroup", props: { name: "timeAvailable", ... } },
        { component: "Slider", props: { name: "energyLevel", ... } },
        { component: "TextArea", props: { name: "mindset", ... } },
        { component: "Button", props: { label: "Let's begin" } }
      ]
    }
    ↓
Frontend renders UITree recursively
    ↓
User fills form, submits
    ↓
Form data sent via WebSocket: { form_id, data: {...} }
    ↓
Orchestrator: process action (same as voice path)
    ↓
Backend: Store SessionContext, transition mode
```

**Key insight**: Both paths execute the SAME backend action.

## State Synchronization

### Session State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│                      SESSION STATE                               │
│                                                                  │
│  ┌─────────────┐                                                │
│  │ INIT        │ ← Session created                              │
│  └──────┬──────┘                                                │
│         │ startSession()                                        │
│         ▼                                                       │
│  ┌─────────────┐                                                │
│  │ CHECKING_IN │ ← Gathering Set/Setting/Intention              │
│  └──────┬──────┘                                                │
│         │ checkInComplete()                                     │
│         ▼                                                       │
│  ┌─────────────┐                                                │
│  │ ACTIVE      │ ← Normal dialogue loop                         │
│  └──────┬──────┘                                                │
│         │ endSession() | timeout                                │
│         ▼                                                       │
│  ┌─────────────┐                                                │
│  │ ENDED       │                                                │
│  └─────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```

### Cross-Modality State Sync

The same state is maintained regardless of input modality:

```python
class UnifiedSessionState:
    session_id: str
    modality_preference: InputModality  # User's preferred modality

    # Pending data collection (survives modality switches)
    pending_data_request: Optional[PendingDataRequest]

    # Check-in state
    check_in_data: Partial[SessionContext]
    check_in_complete: bool

    # Dialogue state
    current_mode: DialogueMode
    messages: List[Message]  # All messages, tagged with modality
```

### Storage Strategy

- **sessionStorage**: Session-scoped data (pending data, session ID)
- **localStorage**: User preferences (modality preference, voice enabled)

## Implementation Phases

### Phase 0: Prerequisites
- #83 - ✅ DECIDED: Ad-Hoc UI Generation with Primitives
- #84 - **BLOCKING**: WebSocket Protocol Extension

### Phase 1: Foundation
- #68 - Extended SAGEResponse with composable UITreeNode
- #69 - Unified Input Normalizer
- #70 - Semantic Intent Extractor

### Phase 2: Orchestrator
- #71 - SAGE Orchestrator Core
- #72 - Pending Data Request Handling

### Phase 3: UI Generation
- #73 - Primitive UI Renderer Integration
- #74 - Primitive Component Library (~15 components)
- #75 - UI Generation Agent (Grok-2 composition tool)

### Phase 4: Patterns & Verification
- #76 - UI Patterns & Agent Verification

### Phase 5: State Sync & Error Handling
- #81 - Cross-Modality State Synchronization
- #85 - Voice Error Recovery & Graceful Degradation

### Phase 6: Testing & Polish
- #82 - Integration Testing & Voice/UI Parity Verification
- #87 - Accessibility for Voice/UI Parity

## Error Handling

### Network Interruption During Data Collection

```python
if connection_lost and pending_data_request:
    # Store partial data in sessionStorage
    SessionPersistence.setPendingData(pending_data_request)

    # On reconnect, resume from where left off
    if SessionPersistence.getPendingData():
        resume_data_collection()
```

### Voice Transcription Errors

```python
if transcription_confidence < 0.7:
    response = ExtendedSAGEResponse(
        message="I didn't quite catch that. Could you say it again?",
        voice_hints=VoiceHints(slower=True),
    )
```

### Modality Mismatch

```python
if intent_expects_voice and not session.can_speak:
    # Adapt to UI-only mode via ad-hoc generation
    ui_tree = await ui_agent.generate(purpose=intent, context=session_context)
    return ExtendedSAGEResponse(ui_tree=ui_tree, ...)
```

## Success Criteria

1. **Full Feature Parity**: Every feature works in both voice and UI modes
2. **Same Backend Actions**: Identical data structures stored regardless of input method
3. **Seamless Switching**: User can switch modalities mid-session without data loss
4. **Natural Voice Flow**: Voice interactions feel conversational, not form-filling
5. **Responsive UI**: UI components provide instant feedback and validation
6. **Ad-Hoc Flexibility**: AI can create custom UIs for any interaction type

## Dependencies

- **UI Renderer**: Custom recursive renderer (~100 lines) or json-render library
- **json-render reference**: https://github.com/vercel-labs/json-render
- **Grok-2**: Fast model for UI generation (<500ms target)
- **Grok Voice API**: Already integrated
- **FastAPI WebSocket**: Already implemented
- **Pydantic v2**: Already used for all models

## Related Documents

- [System Design](./system-design.md)
- [Data Model](./data-model.md)
- [Context Management](./context-management.md)
