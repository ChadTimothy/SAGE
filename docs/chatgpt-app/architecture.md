# SAGE ChatGPT App Architecture

## Overview

This document describes the architecture for integrating SAGE as a ChatGPT App using OpenAI's Apps SDK. The integration enables users to access SAGE tutoring through ChatGPT's interface while maintaining their learning data synchronized with the SAGE web application.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ChatGPT Interface                                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  User Message: "I want to learn how to negotiate pricing"           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ChatGPT Model (tool selection)                                      │   │
│  │  → Invokes: sage_start_session(goal="negotiate pricing")            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  SAGE Widget (sandboxed iframe)                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │  Check-in Form                                               │    │   │
│  │  │  [Energy: Low/Med/High]  [Time: 15m/30m/1h]                 │    │   │
│  │  │  [What's your focus?_______________]  [Start Session]       │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ MCP Protocol (HTTPS)
                                     │ + OAuth 2.1 Bearer Token
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SAGE MCP Server                                      │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │ Tool Registry   │  │ Widget Registry │  │ OAuth Validator │            │
│  │                 │  │                 │  │                 │            │
│  │ sage_start_     │  │ checkin.html    │  │ validate_token()│            │
│  │ sage_checkin    │  │ progress.html   │  │ get_user_ctx()  │            │
│  │ sage_message    │  │ graph.html      │  │                 │            │
│  │ sage_progress   │  │ practice.html   │  │                 │            │
│  │ sage_graph      │  │                 │  │                 │            │
│  │ sage_practice_* │  │                 │  │                 │            │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘            │
│           │                    │                    │                      │
│           └────────────────────┴────────────────────┘                      │
│                                │                                           │
└────────────────────────────────┼───────────────────────────────────────────┘
                                 │
                                 │ Internal HTTP calls
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Existing SAGE Backend (FastAPI)                          │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ /api/sessions│  │ /api/learners│  │ /api/practice│  │ /api/mcp/*   │   │
│  │              │  │              │  │              │  │ (NEW)        │   │
│  │ create       │  │ get_state    │  │ start        │  │ message      │   │
│  │ get_state    │  │ get_graph    │  │ message      │  │ (REST ver of │   │
│  │ merge_data   │  │ get_proofs   │  │ end          │  │  WebSocket)  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     SQLite Database                                  │   │
│  │  learners | sessions | outcomes | concepts | proofs | users         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### 1. ChatGPT Interface
- Hosts conversation with user
- Invokes MCP tools based on user intent
- Renders widget iframes inline in conversation
- Manages OAuth flow for account linking

### 2. SAGE MCP Server
- Exposes SAGE functionality as MCP tools
- Registers widget HTML as resources (`text/html+skybridge`)
- Validates OAuth 2.1 tokens from ChatGPT
- Transforms SAGE API responses to MCP format
- **Technology**: Python with FastMCP or mcp SDK

### 3. SAGE Backend (Existing)
- All existing API endpoints remain unchanged
- New REST endpoint for MCP conversation (replaces WebSocket)
- OAuth 2.1 endpoints added for ChatGPT auth
- All learning data stored in SQLite

### 4. Widgets
- Sandboxed HTML/JS components in iframes
- Communicate via `window.openai` API
- Can invoke MCP tools directly (`callTool`)
- State persisted via `setWidgetState`
- **Technology**: React + apps-sdk-ui library

## Data Flow Patterns

### Pattern 1: Session Start with Check-in

```
User: "I want to learn negotiation"
         │
         ▼
ChatGPT: Selects sage_start_session tool
         │
         ▼
MCP Server:
  1. Validates OAuth token → gets user_id, learner_id
  2. Calls POST /api/sessions (creates session)
  3. Returns structuredContent + widget trigger
         │
         ▼
ChatGPT: Renders checkin.html widget
         │
         ▼
Widget: User completes form, clicks "Start"
  1. Calls window.openai.callTool('sage_checkin', {...})
  2. Calls window.openai.sendFollowUpMessage({prompt: "Ready to start"})
         │
         ▼
MCP Server: sage_checkin
  1. Calls POST /api/sessions/{id}/merge-data
  2. Returns confirmation
         │
         ▼
ChatGPT: Continues conversation with SAGE
```

### Pattern 2: Tutoring Conversation

```
User: "What should I know first about pricing?"
         │
         ▼
ChatGPT: Selects sage_message tool
         │
         ▼
MCP Server:
  1. Validates OAuth token
  2. Calls POST /api/mcp/message (NEW endpoint)
     - Routes through SAGEOrchestrator
     - Returns response + dialogue mode + any state changes
  3. Returns structuredContent with:
     - assistant_message (shown to user)
     - mode (probing/teaching/verification)
     - concepts_discussed (for model context)
     - proofs_earned (if any)
         │
         ▼
ChatGPT: Shows SAGE's response to user
```

### Pattern 3: Progress Visualization

```
User: "Show me my progress"
         │
         ▼
ChatGPT: Selects sage_progress tool
         │
         ▼
MCP Server:
  1. Calls GET /api/learners/{id}/state
  2. Returns:
     - structuredContent: summary stats (model sees)
     - _meta: full state (widget sees, model doesn't)
     - outputTemplate: progress.html
         │
         ▼
ChatGPT: Renders progress.html widget
         │
         ▼
Widget:
  - Reads window.openai.toolOutput (summary)
  - Reads window.openai.toolResponseMetadata (full state)
  - Renders interactive progress display
```

## State Management Strategy

### Three Tiers of State

| Tier | Location | Lifetime | Examples |
|------|----------|----------|----------|
| **Business Data** | SAGE Backend (SQLite) | Persistent | Outcomes, concepts, proofs, sessions |
| **Session State** | MCP Server (in-memory) | Session duration | Current dialogue mode, pending check-in data |
| **UI State** | Widget (`setWidgetState`) | Widget instance | Selected tab, expanded panels, scroll position |

### Cross-Session Continuity

Since SAGE stores all learning data in SQLite, users maintain full continuity:
- Start session on web app → continue in ChatGPT
- Earn proof in ChatGPT → visible in web app's graph
- Same outcomes, concepts, proofs across both interfaces

### Widget State Limits

Per Apps SDK guidelines:
- `setWidgetState` payload should be < 4K tokens
- Only store UI-specific state (selections, view modes)
- Business data always fetched fresh from tools

## Authentication Flow

### OAuth 2.1 Sequence

```
┌─────────┐     ┌─────────┐     ┌─────────────┐     ┌──────────────┐
│ ChatGPT │     │  User   │     │ SAGE OAuth  │     │ SAGE Backend │
└────┬────┘     └────┬────┘     └──────┬──────┘     └──────┬───────┘
     │               │                 │                   │
     │  1. Tool requires auth          │                   │
     │──────────────────────────────►  │                   │
     │                                 │                   │
     │  2. Show "Sign in to SAGE"      │                   │
     │◄──────────────────────────────  │                   │
     │               │                 │                   │
     │  3. Click sign in               │                   │
     │───────────────┼────────────────►│                   │
     │               │                 │                   │
     │               │  4. Login page  │                   │
     │               │◄────────────────│                   │
     │               │                 │                   │
     │               │  5. Credentials │                   │
     │               │────────────────►│                   │
     │               │                 │                   │
     │               │                 │  6. Verify user   │
     │               │                 │──────────────────►│
     │               │                 │                   │
     │               │                 │  7. user_id,      │
     │               │                 │     learner_id    │
     │               │                 │◄──────────────────│
     │               │                 │                   │
     │  8. Auth code │                 │                   │
     │◄──────────────┼─────────────────│                   │
     │               │                 │                   │
     │  9. Exchange code for token     │                   │
     │────────────────────────────────►│                   │
     │               │                 │                   │
     │  10. Access token (JWT)         │                   │
     │◄────────────────────────────────│                   │
     │               │                 │                   │
     │  11. MCP calls with Bearer token│                   │
     │────────────────────────────────────────────────────►│
     │               │                 │                   │
```

### Token Contents

The OAuth access token (JWT) contains:
```json
{
  "sub": "user_abc123",           // User ID
  "learner_id": "learner_xyz",    // SAGE learner ID
  "scope": "learner:read learner:write session:manage",
  "iss": "https://sage.app",
  "aud": "https://sage.app",
  "exp": 1704067200
}
```

### Account Linking

- **New ChatGPT user**: OAuth flow creates SAGE account, returns learner_id
- **Existing SAGE user**: OAuth flow looks up existing account, returns learner_id
- **Same learner_id** used across web app and ChatGPT

## MCP Response Structure

### Standard Tool Response

```python
{
    # Model sees this - keep concise (<4K tokens)
    "structuredContent": {
        "sessionId": "sess_abc123",
        "mode": "teaching",
        "conceptsDiscussed": ["value_anchoring"],
        "proofsEarned": []
    },

    # Optional text narration for model
    "content": [
        {"type": "text", "text": "SAGE is now teaching about value anchoring."}
    ],

    # Widget-only data - model never sees this
    "_meta": {
        "openai/outputTemplate": "ui://widget/progress.html",
        "openai/widgetAccessible": true,
        "fullResponse": {
            "message": "Let's talk about anchoring...",
            "transitions": [...],
            "insights": [...]
        }
    }
}
```

### Key Metadata Fields

| Field | Purpose |
|-------|---------|
| `openai/outputTemplate` | URI of widget to render |
| `openai/widgetAccessible` | Allow widget to call this tool |
| `openai/visibility` | "private" for widget-only tools |
| `openai/widgetSessionId` | Session ID for state continuity |
| `openai/widgetCSP` | Content Security Policy (allowed domains) |

## Technology Decisions

### MCP Server: FastMCP (Python)

**Rationale**:
- SAGE backend is Python/FastAPI
- Direct internal calls without HTTP overhead
- `FastMCP.from_fastapi()` can auto-expose existing endpoints
- Same deployment, simpler operations

**Alternative Considered**: Standalone Node.js MCP server
- Rejected: Would require HTTP calls to SAGE, separate deployment

### Widgets: React + apps-sdk-ui

**Rationale**:
- Official OpenAI component library
- Consistent ChatGPT styling
- Tailwind 4 integration
- Accessible (Radix primitives)

**Build**: Vite with `vite-plugin-singlefile` for self-contained HTML

### Conversation Handling: Pass-through to SAGE Orchestrator

**Rationale**:
- Preserves SAGE's 8 dialogue modes
- Maintains teaching methodology (iterate/discover)
- Same quality tutoring in ChatGPT as web app
- No duplicate conversation logic

**Implication**: Need new REST endpoint since MCP doesn't support WebSocket

## New Endpoints Required

### For MCP Server Integration

```python
# POST /api/mcp/message
# REST equivalent of WebSocket /api/chat/{session_id}
@router.post("/api/mcp/message")
async def mcp_message(
    session_id: str,
    message: str,
    user: CurrentUser = Depends(get_mcp_user)  # OAuth token
) -> MCPMessageResponse:
    """Process message through SAGE orchestrator (REST version)."""
    response = await orchestrator.process_input(
        raw_input=message,
        source_modality=InputModality.CHAT,
        session_id=session_id,
    )
    return MCPMessageResponse(
        message=response.message,
        mode=response.current_mode.value,
        concepts=[...],
        proofs=[...],
    )
```

### For OAuth 2.1

See `api-mapping.md` for full OAuth endpoint specifications.

## Security Considerations

### Token Validation
- Every MCP tool call validates Bearer token
- Token signature verified against SAGE's signing key
- Expiration checked, refresh supported
- learner_id extracted from token, not from user input

### Scope Enforcement
- `learner:read` - View progress, graph, outcomes
- `learner:write` - Modify learning data
- `session:manage` - Create/end sessions

### Widget Security
- Widgets run in sandboxed iframes
- CSP restricts external requests
- No access to parent page or cookies
- API keys never in widget code

## Performance Considerations

### Response Size
- `structuredContent` kept under 4K tokens
- Large data (full graph) in `_meta` only
- Pagination for long lists

### Latency
- MCP server co-located with SAGE backend
- Widget assets cached at CDN
- OAuth tokens cached (1 hour TTL)

### Scalability
- Stateless MCP server (session state in SAGE backend)
- Can scale horizontally
- SQLite sufficient for current scale

## File Structure

```
src/sage/
├── mcp/                          # NEW: MCP Server
│   ├── __init__.py
│   ├── server.py                 # FastMCP setup
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── session.py            # sage_start_session, sage_checkin
│   │   ├── dialogue.py           # sage_message
│   │   ├── progress.py           # sage_progress, sage_graph
│   │   └── practice.py           # sage_practice_*
│   ├── widgets/
│   │   ├── src/                  # React source
│   │   │   ├── checkin/
│   │   │   ├── progress/
│   │   │   ├── graph/
│   │   │   └── practice/
│   │   └── dist/                 # Built HTML files
│   └── auth.py                   # MCP token validation
├── api/
│   ├── routes/
│   │   ├── oauth.py              # NEW: OAuth 2.1 endpoints
│   │   └── mcp_routes.py         # NEW: MCP-specific REST endpoints
│   └── main.py                   # Add OAuth router
└── ...existing files...
```

## References

- [OpenAI Apps SDK](https://developers.openai.com/apps-sdk/)
- [Build MCP Server](https://developers.openai.com/apps-sdk/build/mcp-server/)
- [Build ChatGPT UI](https://developers.openai.com/apps-sdk/build/chatgpt-ui/)
- [State Management](https://developers.openai.com/apps-sdk/build/state-management/)
- [Authentication](https://developers.openai.com/apps-sdk/build/auth/)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Apps SDK Examples](https://github.com/openai/openai-apps-sdk-examples)
- [apps-sdk-ui](https://github.com/openai/apps-sdk-ui)
