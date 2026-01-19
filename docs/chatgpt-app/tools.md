# SAGE MCP Tool Specifications

This document defines the MCP tools that expose SAGE functionality to ChatGPT.

## Tool Overview

| Tool | Purpose | Widget | Auth Required |
|------|---------|--------|---------------|
| `sage_start_session` | Begin tutoring session | checkin.html | Yes |
| `sage_checkin` | Submit check-in data | None | Yes |
| `sage_message` | Send message to SAGE | None | Yes |
| `sage_progress` | Show learning progress | progress.html | Yes |
| `sage_graph` | Show knowledge graph | graph.html | Yes |
| `sage_practice_start` | Begin practice scenario | practice.html | Yes |
| `sage_practice_message` | Continue practice | None | Yes |
| `sage_practice_end` | End practice with feedback | practice.html | Yes |
| `sage_end_session` | End current session | None | Yes |

---

## Tool Specifications

### `sage_start_session`

Begins a new tutoring session. Triggers the check-in widget to gather context.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "goal": {
      "type": "string",
      "description": "What the user wants to learn (optional, from conversation)"
    }
  }
}
```

**Output**:
```python
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
    },
    "content": [
        {"type": "text", "text": "Starting a new SAGE session. Please complete the check-in."}
    ],
    "_meta": {
        "openai/outputTemplate": "ui://widget/checkin.html",
        "openai/widgetAccessible": true,
        "openai/widgetSessionId": "sess_abc123"
    }
}
```

**Backend Calls**:
- `POST /api/sessions` - Create session
- `GET /api/learners/{id}` - Get learner info

**Widget Interaction**:
- Widget displays check-in form
- On submit, widget calls `sage_checkin`

---

### `sage_checkin`

Submits check-in data (Set/Setting/Intention) collected by widget.

**Input Schema**:
```json
{
  "type": "object",
  "required": ["session_id"],
  "properties": {
    "session_id": {
      "type": "string",
      "description": "Session ID from sage_start_session"
    },
    "energy": {
      "type": "string",
      "enum": ["low", "medium", "high"],
      "description": "User's current energy level"
    },
    "time_available": {
      "type": "integer",
      "description": "Minutes available for session"
    },
    "intention": {
      "type": "string",
      "description": "What user wants to focus on this session"
    },
    "environment": {
      "type": "string",
      "description": "Physical environment (quiet office, commuting, etc.)"
    }
  }
}
```

**Output**:
```python
{
    "structuredContent": {
        "status": "ready",
        "sessionId": "sess_abc123",
        "adaptations": {
            "pace": "moderate",
            "depth": "standard",
            "practiceEnabled": true
        }
    },
    "content": [
        {"type": "text", "text": "Check-in complete. SAGE will adapt to your current state."}
    ]
}
```

**Backend Calls**:
- `POST /api/sessions/{id}/merge-data` - Merge check-in data

**Security**:
- `_meta["openai/widgetAccessible"]: true` on `sage_start_session`
- Only callable from checkin widget

---

### `sage_message`

Sends a message to SAGE and receives the tutoring response.

**Input Schema**:
```json
{
  "type": "object",
  "required": ["session_id", "message"],
  "properties": {
    "session_id": {
      "type": "string",
      "description": "Active session ID"
    },
    "message": {
      "type": "string",
      "description": "User's message to SAGE"
    }
  }
}
```

**Output**:
```python
{
    "structuredContent": {
        "response": "Let's explore what you already know about pricing...",
        "mode": "probing",
        "modeDescription": "Finding gaps in knowledge",
        "conceptsDiscussed": ["value_pricing", "cost_plus_pricing"],
        "gapIdentified": {
            "name": "anchoring_techniques",
            "displayName": "Anchoring Techniques"
        },
        "proofEarned": null,
        "outcomeProgress": 0.35
    },
    "content": [
        {"type": "text", "text": "Let's explore what you already know about pricing..."}
    ],
    "_meta": {
        "fullResponse": {
            "message": "...",
            "currentMode": "probing",
            "transitionTo": null,
            "insights": [...],
            "uiTree": {...}
        }
    }
}
```

**Backend Calls**:
- `POST /api/mcp/message` (NEW endpoint - REST version of WebSocket)

**Notes**:
- This is the core conversation tool
- Model sees summary in `structuredContent`
- Full SAGE response in `_meta` for potential widget use

---

### `sage_progress`

Shows the user's learning progress with outcomes, proofs, and stats.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {}
}
```

**Output**:
```python
{
    "structuredContent": {
        "activeOutcome": {
            "id": "out_123",
            "description": "Price freelance services confidently",
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
        "recentProofs": [
            {"concept": "Value Anchoring", "earnedAt": "2024-01-15"},
            {"concept": "Handling Objections", "earnedAt": "2024-01-14"}
        ]
    },
    "content": [
        {"type": "text", "text": "Here's your learning progress."}
    ],
    "_meta": {
        "openai/outputTemplate": "ui://widget/progress.html",
        "fullState": {
            "learner": {...},
            "outcomes": [...],
            "concepts": [...],
            "proofs": [...],
            "pendingFollowups": [...]
        }
    }
}
```

**Backend Calls**:
- `GET /api/learners/{id}/state` - Full learner state

---

### `sage_graph`

Shows the knowledge graph visualization.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "filters": {
      "type": "object",
      "properties": {
        "showProvenOnly": {"type": "boolean"},
        "showOutcomes": {"type": "boolean"},
        "showConcepts": {"type": "boolean"},
        "outcomeId": {"type": "string"}
      }
    }
  }
}
```

**Output**:
```python
{
    "structuredContent": {
        "nodeCount": 23,
        "edgeCount": 31,
        "provenConcepts": 8,
        "activeOutcome": "Price freelance services confidently"
    },
    "content": [
        {"type": "text", "text": "Here's your knowledge graph."}
    ],
    "_meta": {
        "openai/outputTemplate": "ui://widget/graph.html",
        "graphData": {
            "nodes": [
                {"id": "out_123", "type": "outcome", "label": "...", "data": {...}},
                {"id": "con_456", "type": "concept", "label": "...", "data": {...}},
                ...
            ],
            "edges": [
                {"from": "out_123", "to": "con_456", "type": "requires"},
                ...
            ]
        }
    }
}
```

**Backend Calls**:
- `GET /api/learners/{id}/graph` - Full graph data

---

### `sage_practice_start`

Begins a practice/roleplay scenario.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "scenario_id": {
      "type": "string",
      "description": "ID of preset scenario (optional)"
    },
    "custom_scenario": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "sage_role": {"type": "string"},
        "user_role": {"type": "string"}
      }
    }
  }
}
```

**Output**:
```python
{
    "structuredContent": {
        "practiceSessionId": "prac_abc123",
        "scenario": {
            "title": "Price Negotiation with Skeptical Client",
            "sageRole": "Skeptical potential client",
            "userRole": "Freelance consultant",
            "description": "The client thinks your rates are too high"
        },
        "initialMessage": "So, $150 per hour? That seems quite steep for this kind of work..."
    },
    "content": [
        {"type": "text", "text": "Practice scenario started. I'll play the skeptical client."}
    ],
    "_meta": {
        "openai/outputTemplate": "ui://widget/practice.html",
        "openai/widgetAccessible": true,
        "openai/widgetSessionId": "prac_abc123"
    }
}
```

**Backend Calls**:
- `POST /api/practice/start` - Start practice session
- `GET /api/scenarios/presets` - List available scenarios (if browsing)

---

### `sage_practice_message`

Continues practice conversation with the character.

**Input Schema**:
```json
{
  "type": "object",
  "required": ["session_id", "message"],
  "properties": {
    "session_id": {
      "type": "string",
      "description": "Practice session ID"
    },
    "message": {
      "type": "string",
      "description": "User's response in the roleplay"
    }
  }
}
```

**Output**:
```python
{
    "structuredContent": {
        "characterResponse": "Hmm, I see your point about the value, but...",
        "turnNumber": 4,
        "hintAvailable": true
    },
    "content": [
        {"type": "text", "text": "Hmm, I see your point about the value, but..."}
    ]
}
```

**Backend Calls**:
- `POST /api/practice/{session_id}/message`

**Widget Callable**: Yes (via `openai/widgetAccessible`)

---

### `sage_practice_end`

Ends practice session and provides feedback.

**Input Schema**:
```json
{
  "type": "object",
  "required": ["session_id"],
  "properties": {
    "session_id": {
      "type": "string"
    }
  }
}
```

**Output**:
```python
{
    "structuredContent": {
        "summary": "Good effort! You showed improvement in value framing.",
        "positives": [
            "Strong opening with value proposition",
            "Good use of anchoring technique"
        ],
        "improvements": [
            "Could have asked more discovery questions",
            "Rushed to discount too quickly"
        ],
        "revealedGaps": ["handling_discount_requests"]
    },
    "content": [
        {"type": "text", "text": "Practice complete! Here's your feedback..."}
    ],
    "_meta": {
        "openai/outputTemplate": "ui://widget/practice.html",
        "fullFeedback": {...}
    }
}
```

**Backend Calls**:
- `POST /api/practice/{session_id}/end`

---

### `sage_end_session`

Ends the current tutoring session.

**Input Schema**:
```json
{
  "type": "object",
  "required": ["session_id"],
  "properties": {
    "session_id": {
      "type": "string"
    }
  }
}
```

**Output**:
```python
{
    "structuredContent": {
        "summary": {
            "duration": 25,
            "conceptsExplored": 3,
            "proofsEarned": 1,
            "modeBreakdown": {
                "teaching": 0.4,
                "probing": 0.3,
                "verification": 0.3
            }
        },
        "nextSteps": [
            "Practice the anchoring technique before your call Tuesday",
            "Review the objection handling concept"
        ]
    },
    "content": [
        {"type": "text", "text": "Session complete. Great progress today!"}
    ]
}
```

**Backend Calls**:
- `POST /api/sessions/{session_id}/end`

---

## Implementation Pattern

```python
from mcp.server import McpServer
from mcp import types
from pydantic import BaseModel
import httpx

# Pydantic models for type safety
class StartSessionInput(BaseModel):
    goal: str | None = None

class StartSessionOutput(BaseModel):
    sessionId: str
    learnerId: str
    suggestedGoal: str | None
    hasActiveOutcome: bool

# Tool registration
@mcp.tool()
async def sage_start_session(
    goal: str | None = None,
) -> types.CallToolResult:
    """Begin a new SAGE tutoring session."""

    # Get user from OAuth token
    token = get_bearer_token_from_request()
    user = await validate_oauth_token(token)

    # Create session via SAGE API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SAGE_API_URL}/api/sessions",
            json={"learner_id": user.learner_id},
            headers={"Authorization": f"Bearer {token}"}
        )
        session = response.json()

    # Build MCP response
    output = StartSessionOutput(
        sessionId=session["id"],
        learnerId=user.learner_id,
        suggestedGoal=goal,
        hasActiveOutcome=session.get("active_outcome_id") is not None
    )

    return types.CallToolResult(
        structuredContent=output.model_dump(),
        content=[types.TextContent(
            type="text",
            text="Starting a new SAGE session. Please complete the check-in."
        )],
        _meta={
            "openai/outputTemplate": "ui://widget/checkin.html",
            "openai/widgetAccessible": True,
            "openai/widgetSessionId": session["id"]
        }
    )
```

## Security Annotations

All tools use OAuth 2.1 security:

```python
OAUTH_SECURITY_SCHEME = [
    {"type": "oauth2", "scopes": ["learner:read", "learner:write", "session:manage"]}
]

@mcp.tool(
    annotations={
        "readOnlyHint": False,  # Tool modifies data
        "destructiveHint": False,  # Not destructive
        "openWorldHint": False  # Closed system
    },
    security=OAUTH_SECURITY_SCHEME
)
async def sage_message(...):
    ...
```

## Error Handling

Tools return structured errors:

```python
# Authentication error
return types.CallToolResult(
    content=[types.TextContent(type="text", text="Authentication required")],
    isError=True,
    _meta={
        "mcp/www_authenticate": build_www_authenticate_header()
    }
)

# Validation error
return types.CallToolResult(
    content=[types.TextContent(type="text", text="Session not found")],
    isError=True,
    structuredContent={"error": "SESSION_NOT_FOUND", "sessionId": session_id}
)
```
