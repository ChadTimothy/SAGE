# SAGE API to MCP Tool Mapping

This document maps existing SAGE REST/WebSocket API endpoints to MCP tools for the ChatGPT App integration.

## Mapping Overview

| MCP Tool | SAGE API Endpoint(s) | Method | Notes |
|----------|---------------------|--------|-------|
| `sage_start_session` | `/api/sessions` | POST | Create session |
| | `/api/learners/{id}` | GET | Get learner info |
| `sage_checkin` | `/api/sessions/{id}/merge-data` | POST | Merge check-in data |
| `sage_message` | `/api/mcp/message` | POST | **NEW** - REST version of WebSocket |
| `sage_progress` | `/api/learners/{id}/state` | GET | Full learner state |
| `sage_graph` | `/api/learners/{id}/graph` | GET | Graph data |
| `sage_practice_start` | `/api/practice/start` | POST | Start practice session |
| `sage_practice_message` | `/api/practice/{id}/message` | POST | Send practice message |
| `sage_practice_end` | `/api/practice/{id}/end` | POST | End and get feedback |
| `sage_end_session` | `/api/sessions/{id}/end` | POST | End session |

---

## Detailed Mapping

### `sage_start_session`

**MCP Input:**
```json
{
  "goal": "negotiate pricing confidently"
}
```

**SAGE API Calls:**

1. Create session:
```http
POST /api/sessions
Authorization: Bearer {oauth_token}
Content-Type: application/json

{
  "learner_id": "{from_oauth_user}"
}
```

Response:
```json
{
  "id": "sess_abc123",
  "learner_id": "learner_xyz",
  "active_outcome_id": "out_123",
  "created_at": "2024-01-15T10:00:00Z"
}
```

2. Get learner info:
```http
GET /api/learners/{learner_id}
Authorization: Bearer {oauth_token}
```

Response:
```json
{
  "id": "learner_xyz",
  "name": "User Name",
  "active_outcome": {
    "id": "out_123",
    "description": "Price freelance services confidently"
  }
}
```

**MCP Output:**
```json
{
  "structuredContent": {
    "sessionId": "sess_abc123",
    "learnerId": "learner_xyz",
    "suggestedGoal": "negotiate pricing confidently",
    "hasActiveOutcome": true,
    "activeOutcome": {
      "id": "out_123",
      "description": "Price freelance services confidently"
    }
  }
}
```

---

### `sage_checkin`

**MCP Input:**
```json
{
  "session_id": "sess_abc123",
  "energy": "medium",
  "time_available": 30,
  "intention": "Practice pricing conversations",
  "environment": "quiet office"
}
```

**SAGE API Call:**
```http
POST /api/sessions/sess_abc123/merge-data
Authorization: Bearer {oauth_token}
Content-Type: application/json

{
  "context": {
    "set": {
      "energy_level": "medium",
      "mindset": "focused"
    },
    "setting": {
      "time_available": 30,
      "environment": "quiet office",
      "can_speak": true
    },
    "intention": {
      "focus": "Practice pricing conversations",
      "strength": "learning"
    }
  }
}
```

**Existing Endpoint:** `src/sage/api/routes/sessions.py:merge_session_data`

```python
@router.post("/{session_id}/merge-data")
async def merge_session_data(
    session_id: str,
    request: MergeDataRequest,
    graph: Graph,
    user: User,
    verifier: Verifier,
) -> MergeDataResponse:
```

---

### `sage_message`

**MCP Input:**
```json
{
  "session_id": "sess_abc123",
  "message": "I want to learn about value-based pricing"
}
```

**NEW SAGE API Endpoint Required:**

The existing chat uses WebSocket (`/api/ws/chat/{session_id}`), but MCP requires REST.

```http
POST /api/mcp/message
Authorization: Bearer {oauth_token}
Content-Type: application/json

{
  "session_id": "sess_abc123",
  "message": "I want to learn about value-based pricing"
}
```

**Implementation Reference:** `src/sage/api/routes/chat.py:websocket_chat`

The new endpoint will:
1. Receive message via REST
2. Use same `ConversationEngine` as WebSocket handler
3. Return full response (no streaming for MCP)
4. Include structured output for model consumption

**Proposed Implementation:**

```python
# src/sage/api/routes/mcp.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sage.api.deps import Graph, User, Verifier, Engine

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

class MCPMessageRequest(BaseModel):
    session_id: str
    message: str

class MCPMessageResponse(BaseModel):
    response: str
    mode: str
    mode_description: str
    concepts_discussed: list[str]
    gap_identified: dict | None
    proof_earned: dict | None
    outcome_progress: float

@router.post("/message", response_model=MCPMessageResponse)
async def mcp_message(
    request: MCPMessageRequest,
    graph: Graph,
    user: User,
    verifier: Verifier,
    engine: Engine,
) -> MCPMessageResponse:
    """REST endpoint for MCP message handling."""

    # Verify session ownership
    verifier.verify_session(user, request.session_id)

    # Get session
    session = graph.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Process message through conversation engine
    result = await engine.process_message(
        session=session,
        message=request.message,
    )

    # Build MCP-friendly response
    return MCPMessageResponse(
        response=result.message,
        mode=result.current_mode.value,
        mode_description=get_mode_description(result.current_mode),
        concepts_discussed=[c.name for c in result.concepts_discussed],
        gap_identified=result.gap_identified.model_dump() if result.gap_identified else None,
        proof_earned=result.proof_earned.model_dump() if result.proof_earned else None,
        outcome_progress=result.outcome_progress,
    )
```

---

### `sage_progress`

**MCP Input:**
```json
{}
```

**SAGE API Call:**
```http
GET /api/learners/{learner_id}/state
Authorization: Bearer {oauth_token}
```

**Existing Endpoint:** `src/sage/api/routes/learners.py:get_learner_state`

```python
@router.get("/{learner_id}/state", response_model=LearnerStateResponse)
async def get_learner_state(
    learner_id: str,
    graph: Graph,
    user: User,
    verifier: Verifier,
) -> LearnerStateResponse:
```

**Response Transformation:**

SAGE API returns:
```json
{
  "learner": { ... },
  "active_outcome": { ... },
  "concepts": [ ... ],
  "proofs": [ ... ],
  "sessions": [ ... ]
}
```

MCP tool transforms to:
```json
{
  "structuredContent": {
    "activeOutcome": {
      "id": "out_123",
      "description": "...",
      "progress": 0.65,
      "conceptsRequired": 5,
      "conceptsProven": 3
    },
    "stats": {
      "totalSessions": 12,
      "totalProofs": 8,
      "totalConcepts": 15,
      "streakDays": 3
    },
    "recentProofs": [ ... ]
  }
}
```

---

### `sage_graph`

**MCP Input:**
```json
{
  "filters": {
    "showProvenOnly": false,
    "showOutcomes": true,
    "showConcepts": true
  }
}
```

**SAGE API Call:**
```http
GET /api/learners/{learner_id}/graph
Authorization: Bearer {oauth_token}
```

**Existing Endpoint:** `src/sage/api/routes/learners.py:get_learner_graph`

```python
@router.get("/{learner_id}/graph", response_model=GraphDataResponse)
async def get_learner_graph(
    learner_id: str,
    graph: Graph,
    user: User,
    verifier: Verifier,
) -> GraphDataResponse:
```

**Note:** Filtering is applied client-side in the widget. The API returns full graph data.

---

### `sage_practice_start`

**MCP Input:**
```json
{
  "scenario_id": "price_negotiation",
  "title": "Price Negotiation with Skeptical Client",
  "description": "The client thinks your rates are too high",
  "sage_role": "Skeptical potential client",
  "user_role": "Freelance consultant"
}
```

**SAGE API Call:**
```http
POST /api/practice/start
Authorization: Bearer {oauth_token}
Content-Type: application/json

{
  "scenario_id": "price_negotiation",
  "title": "Price Negotiation with Skeptical Client",
  "description": "The client thinks your rates are too high",
  "sage_role": "Skeptical potential client",
  "user_role": "Freelance consultant"
}
```

**Existing Endpoint:** `src/sage/api/routes/practice.py:start_practice`

```python
@router.post("/start", response_model=PracticeStartResponse)
async def start_practice(
    request: PracticeStartRequest,
    graph: Graph,
    user: User,
) -> PracticeStartResponse:
```

---

### `sage_practice_message`

**MCP Input:**
```json
{
  "session_id": "prac_abc123",
  "message": "I understand the concern. Let me explain the value..."
}
```

**SAGE API Call:**
```http
POST /api/practice/prac_abc123/message
Authorization: Bearer {oauth_token}
Content-Type: application/json

{
  "content": "I understand the concern. Let me explain the value..."
}
```

**Existing Endpoint:** `src/sage/api/routes/practice.py:send_practice_message`

---

### `sage_practice_end`

**MCP Input:**
```json
{
  "session_id": "prac_abc123"
}
```

**SAGE API Call:**
```http
POST /api/practice/prac_abc123/end
Authorization: Bearer {oauth_token}
```

**Existing Endpoint:** `src/sage/api/routes/practice.py:end_practice`

---

### `sage_end_session`

**MCP Input:**
```json
{
  "session_id": "sess_abc123"
}
```

**SAGE API Call:**
```http
POST /api/sessions/sess_abc123/end
Authorization: Bearer {oauth_token}
```

**Existing Endpoint:** `src/sage/api/routes/sessions.py:end_session`

```python
@router.post("/{session_id}/end", response_model=SessionSummaryResponse)
async def end_session(
    session_id: str,
    graph: Graph,
    user: User,
    verifier: Verifier,
) -> SessionSummaryResponse:
```

---

## New Endpoints Required

### 1. `/api/mcp/message` (Critical)

**Purpose:** REST equivalent of WebSocket chat for MCP tools

**Location:** `src/sage/api/routes/mcp.py` (new file)

**Details:** See `sage_message` section above

### 2. `/api/practice/{session_id}/hint`

**Purpose:** Get a hint during practice

**Status:** Already exists in `src/sage/api/routes/practice.py:get_practice_hint`

### 3. `/api/oauth/*` endpoints

**Purpose:** OAuth 2.1 flow for ChatGPT App authentication

**New endpoints needed:**
- `GET /api/oauth/authorize` - Authorization endpoint
- `POST /api/oauth/token` - Token endpoint
- `POST /api/oauth/register` - Dynamic Client Registration

**Location:** `src/sage/api/routes/oauth.py` (new file)

See `docs/chatgpt-app/architecture.md` for OAuth details.

---

## Authentication Flow

### Current (Web App)

```
NextAuth → JWT → SAGE API (Bearer token)
```

### ChatGPT App

```
ChatGPT → OAuth 2.1 → SAGE OAuth Endpoints → JWT → SAGE API
```

**Unified Pattern:**

Both flows result in a JWT that the API validates:

```python
# src/sage/api/deps.py

async def get_current_user(
    authorization: str = Header(...),
) -> AuthenticatedUser:
    """Validate JWT from either NextAuth or OAuth 2.1."""
    token = authorization.replace("Bearer ", "")

    # JWT validation works for both sources
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

    return AuthenticatedUser(
        user_id=payload["sub"],
        learner_id=payload["learner_id"],
        source=payload.get("source", "web"),  # "web" or "chatgpt"
    )
```

---

## Data Transformation Layer

The MCP server acts as a transformation layer between ChatGPT's MCP protocol and SAGE's REST API.

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Server                           │
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌────────────┐  │
│  │ MCP Input   │ → │ Transform   │ → │ SAGE API   │  │
│  │ (tool args) │    │ (mapping)   │    │ (REST)     │  │
│  └─────────────┘    └─────────────┘    └────────────┘  │
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌────────────┐  │
│  │ MCP Output  │ ← │ Transform   │ ← │ SAGE       │  │
│  │ (CallResult)│    │ (mapping)   │    │ Response   │  │
│  └─────────────┘    └─────────────┘    └────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Transformation Example

```python
# MCP tool implementation
@mcp.tool()
async def sage_progress() -> types.CallToolResult:
    """Get learning progress."""

    # Get user from OAuth
    user = await get_authenticated_user()

    # Call SAGE API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SAGE_API_URL}/api/learners/{user.learner_id}/state",
            headers={"Authorization": f"Bearer {user.token}"}
        )
        state = response.json()

    # Transform to MCP output
    active = state.get("active_outcome")
    proofs = state.get("proofs", [])

    structured = {
        "activeOutcome": {
            "id": active["id"],
            "description": active["description"],
            "progress": calculate_progress(active, proofs),
            "conceptsRequired": len(active.get("required_concepts", [])),
            "conceptsProven": len([p for p in proofs if p["outcome_id"] == active["id"]])
        } if active else None,
        "stats": {
            "totalSessions": len(state.get("sessions", [])),
            "totalProofs": len(proofs),
            "totalConcepts": len(state.get("concepts", [])),
            "streakDays": calculate_streak(state.get("sessions", []))
        },
        "recentProofs": [
            {"concept": p["concept_name"], "earnedAt": p["created_at"]}
            for p in sorted(proofs, key=lambda x: x["created_at"], reverse=True)[:5]
        ]
    }

    return types.CallToolResult(
        structuredContent=structured,
        content=[types.TextContent(type="text", text="Here's your learning progress.")],
        _meta={
            "openai/outputTemplate": "ui://widget/progress.html",
            "fullState": state  # Full data for widget
        }
    )
```

---

## Error Handling

### SAGE API Errors → MCP Errors

| SAGE Error | HTTP Code | MCP Response |
|------------|-----------|--------------|
| Not authenticated | 401 | `isError: true`, `_meta.mcp/www_authenticate` |
| Not authorized | 403 | `isError: true`, error message |
| Not found | 404 | `isError: true`, resource not found |
| Validation error | 422 | `isError: true`, validation details |
| Server error | 500 | `isError: true`, generic error |

### Example Error Response

```python
# Session not found
return types.CallToolResult(
    content=[types.TextContent(type="text", text="Session not found")],
    isError=True,
    structuredContent={
        "error": "SESSION_NOT_FOUND",
        "sessionId": session_id,
        "message": "The requested session does not exist or has expired"
    }
)
```

---

## Rate Limiting

MCP tools should respect SAGE API rate limits:

```python
# Rate limit configuration
RATE_LIMITS = {
    "sage_message": "20/minute",      # Main conversation
    "sage_practice_message": "30/minute",  # Practice mode
    "sage_progress": "10/minute",     # Read-only
    "sage_graph": "5/minute",         # Expensive query
}
```

The MCP server should:
1. Track request counts per user
2. Return `429 Too Many Requests` style error when exceeded
3. Include `Retry-After` in response

---

## Testing Strategy

### Unit Tests

```python
# Test MCP tool → API mapping
async def test_sage_start_session_mapping():
    with respx.mock:
        # Mock SAGE API
        respx.post(f"{SAGE_API_URL}/api/sessions").mock(
            return_value=Response(200, json={"id": "sess_123", "learner_id": "learn_456"})
        )
        respx.get(f"{SAGE_API_URL}/api/learners/learn_456").mock(
            return_value=Response(200, json={"id": "learn_456", "name": "Test"})
        )

        # Call MCP tool
        result = await sage_start_session(goal="test goal")

        # Verify transformation
        assert result.structuredContent["sessionId"] == "sess_123"
        assert result._meta["openai/outputTemplate"] == "ui://widget/checkin.html"
```

### Integration Tests

```python
# Test full flow through actual SAGE API
async def test_full_session_flow():
    # Start session
    start_result = await sage_start_session()
    session_id = start_result.structuredContent["sessionId"]

    # Check in
    checkin_result = await sage_checkin(
        session_id=session_id,
        energy="medium",
        time_available=30,
        intention="Test session"
    )
    assert checkin_result.structuredContent["status"] == "ready"

    # Send message
    msg_result = await sage_message(
        session_id=session_id,
        message="Hello SAGE"
    )
    assert msg_result.structuredContent["response"]

    # End session
    end_result = await sage_end_session(session_id=session_id)
    assert end_result.structuredContent["summary"]
```
