# SAGE Widget Specifications

This document defines the widget components that provide rich UI experiences within ChatGPT.

## Widget Overview

| Widget | Purpose | Triggered By | Calls Tools |
|--------|---------|--------------|-------------|
| `checkin.html` | Gather Set/Setting/Intention | `sage_start_session` | `sage_checkin` |
| `progress.html` | Display learning progress | `sage_progress` | None |
| `graph.html` | Interactive knowledge graph | `sage_graph` | None |
| `practice.html` | Practice/roleplay interface | `sage_practice_start`, `sage_practice_end` | `sage_practice_message` |

---

## Widget Architecture

### Common Structure

All widgets share this base structure:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://cdn.openai.com/apps-sdk-ui/apps-sdk-ui.umd.js"></script>
  <link rel="stylesheet" href="https://cdn.openai.com/apps-sdk-ui/apps-sdk-ui.css">
  <style>
    /* Widget-specific styles */
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="module">
    import { createApp } from './widget.js';
    createApp(document.getElementById('root'));
  </script>
</body>
</html>
```

### window.openai API Usage

```typescript
// Send data back to MCP tool
window.openai.toolOutput({
  type: 'tool_result',
  tool_use_id: toolId,
  content: JSON.stringify(data)
});

// Call another MCP tool
const result = await window.openai.callTool('sage_checkin', {
  session_id: sessionId,
  energy: 'medium',
  time_available: 30,
  intention: 'Practice negotiation'
});

// Update widget state (persisted across renders)
window.openai.setWidgetState({ step: 2, data: partialData });

// Trigger follow-up message in chat
window.openai.sendFollowUpMessage('I completed the check-in');
```

---

## Widget Specifications

### `checkin.html`

Collects Set/Setting/Intention data at session start.

#### Layout

```
┌─────────────────────────────────────────┐
│           Session Check-in              │
├─────────────────────────────────────────┤
│                                         │
│  How are you feeling?                   │
│  ○ Low energy   ○ Medium   ○ High      │
│                                         │
│  Time available?                        │
│  [________] minutes                     │
│                                         │
│  What's your focus today?               │
│  [_____________________________]        │
│                                         │
│  Where are you?                         │
│  ○ Quiet space  ○ Some noise  ○ Busy   │
│                                         │
│  [    Start Session    ]                │
│                                         │
└─────────────────────────────────────────┘
```

#### Data Schema

```typescript
interface CheckinData {
  energy: 'low' | 'medium' | 'high';
  time_available: number; // minutes
  intention: string;
  environment: 'quiet' | 'some_noise' | 'busy';
}
```

#### Implementation

```typescript
// checkin-widget.tsx
import React, { useState } from 'react';
import { Button, RadioGroup, Input, Card } from '@openai/apps-sdk-ui';

interface CheckinWidgetProps {
  sessionId: string;
  suggestedGoal?: string;
  hasActiveOutcome: boolean;
  activeOutcome?: { id: string; description: string };
}

export function CheckinWidget({
  sessionId,
  suggestedGoal,
  hasActiveOutcome,
  activeOutcome
}: CheckinWidgetProps) {
  const [energy, setEnergy] = useState<string>('medium');
  const [time, setTime] = useState<number>(30);
  const [intention, setIntention] = useState(suggestedGoal || '');
  const [environment, setEnvironment] = useState<string>('quiet');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);

    try {
      await window.openai.callTool('sage_checkin', {
        session_id: sessionId,
        energy,
        time_available: time,
        intention,
        environment
      });

      window.openai.sendFollowUpMessage(
        `Ready to learn! Focus: ${intention}`
      );
    } catch (error) {
      console.error('Check-in failed:', error);
    }

    setSubmitting(false);
  };

  return (
    <Card>
      <h2>Session Check-in</h2>

      {hasActiveOutcome && activeOutcome && (
        <div className="active-outcome">
          <p>Continuing: {activeOutcome.description}</p>
        </div>
      )}

      <RadioGroup
        label="How's your energy?"
        value={energy}
        onChange={setEnergy}
        options={[
          { value: 'low', label: 'Low - Keep it light' },
          { value: 'medium', label: 'Medium - Ready to learn' },
          { value: 'high', label: 'High - Challenge me' }
        ]}
      />

      <Input
        label="Time available (minutes)"
        type="number"
        value={time}
        onChange={(e) => setTime(parseInt(e.target.value))}
        min={5}
        max={180}
      />

      <Input
        label="What do you want to focus on?"
        value={intention}
        onChange={(e) => setIntention(e.target.value)}
        placeholder="e.g., Practice pricing conversations"
      />

      <RadioGroup
        label="Your environment"
        value={environment}
        onChange={setEnvironment}
        options={[
          { value: 'quiet', label: 'Quiet space' },
          { value: 'some_noise', label: 'Some background noise' },
          { value: 'busy', label: 'Busy/distracting' }
        ]}
      />

      <Button
        onClick={handleSubmit}
        disabled={submitting || !intention}
        loading={submitting}
      >
        Start Session
      </Button>
    </Card>
  );
}
```

#### Tool Communication

1. Widget receives data from `sage_start_session` via `_meta`
2. On submit, widget calls `sage_checkin` tool
3. Widget triggers follow-up message to continue conversation

---

### `progress.html`

Displays learning progress, outcomes, and recent proofs.

#### Layout

```
┌─────────────────────────────────────────┐
│           Learning Progress             │
├─────────────────────────────────────────┤
│                                         │
│  Current Goal                           │
│  ┌─────────────────────────────────┐    │
│  │ Price freelance services        │    │
│  │ ████████████░░░░░░  65%         │    │
│  │ 3 of 5 concepts proven          │    │
│  └─────────────────────────────────┘    │
│                                         │
│  Stats                                  │
│  ┌──────────┬──────────┬──────────┐    │
│  │ Sessions │  Proofs  │  Streak  │    │
│  │    12    │    8     │  3 days  │    │
│  └──────────┴──────────┴──────────┘    │
│                                         │
│  Recent Proofs                          │
│  ✓ Value Anchoring (Jan 15)            │
│  ✓ Handling Objections (Jan 14)        │
│  ✓ Discovery Questions (Jan 12)        │
│                                         │
└─────────────────────────────────────────┘
```

#### Data Schema

```typescript
interface ProgressData {
  activeOutcome: {
    id: string;
    description: string;
    progress: number; // 0-1
    conceptsRequired: number;
    conceptsProven: number;
  } | null;
  stats: {
    totalSessions: number;
    totalProofs: number;
    totalConcepts: number;
    streakDays: number;
  };
  recentProofs: Array<{
    concept: string;
    earnedAt: string; // ISO date
  }>;
}
```

#### Implementation

```typescript
// progress-widget.tsx
import React from 'react';
import { Card, ProgressBar, StatCard, List } from '@openai/apps-sdk-ui';

interface ProgressWidgetProps {
  activeOutcome: {
    id: string;
    description: string;
    progress: number;
    conceptsRequired: number;
    conceptsProven: number;
  } | null;
  stats: {
    totalSessions: number;
    totalProofs: number;
    totalConcepts: number;
    streakDays: number;
  };
  recentProofs: Array<{
    concept: string;
    earnedAt: string;
  }>;
}

export function ProgressWidget({
  activeOutcome,
  stats,
  recentProofs
}: ProgressWidgetProps) {
  return (
    <div className="progress-widget">
      {activeOutcome && (
        <Card className="outcome-card">
          <h3>Current Goal</h3>
          <p className="outcome-description">{activeOutcome.description}</p>
          <ProgressBar
            value={activeOutcome.progress}
            label={`${Math.round(activeOutcome.progress * 100)}%`}
          />
          <p className="concept-count">
            {activeOutcome.conceptsProven} of {activeOutcome.conceptsRequired} concepts proven
          </p>
        </Card>
      )}

      <div className="stats-row">
        <StatCard label="Sessions" value={stats.totalSessions} />
        <StatCard label="Proofs" value={stats.totalProofs} />
        <StatCard
          label="Streak"
          value={`${stats.streakDays} day${stats.streakDays !== 1 ? 's' : ''}`}
        />
      </div>

      {recentProofs.length > 0 && (
        <Card className="proofs-card">
          <h3>Recent Proofs</h3>
          <List>
            {recentProofs.map((proof, i) => (
              <List.Item key={i} icon="checkmark">
                <span className="proof-concept">{proof.concept}</span>
                <span className="proof-date">
                  {new Date(proof.earnedAt).toLocaleDateString()}
                </span>
              </List.Item>
            ))}
          </List>
        </Card>
      )}
    </div>
  );
}
```

#### Tool Communication

- Widget receives data from `sage_progress` via `structuredContent` and `_meta`
- Read-only widget, no tool calls

---

### `graph.html`

Interactive knowledge graph visualization.

#### Layout

```
┌─────────────────────────────────────────┐
│           Knowledge Graph               │
├─────────────────────────────────────────┤
│  Filters: [Outcomes] [Concepts] [Proven]│
├─────────────────────────────────────────┤
│                                         │
│         ┌──────────┐                    │
│         │ Outcome  │                    │
│         │ (Goal)   │                    │
│         └────┬─────┘                    │
│              │                          │
│     ┌────────┼────────┐                 │
│     │        │        │                 │
│  ┌──▼──┐  ┌──▼──┐  ┌──▼──┐             │
│  │ C1  │  │ C2  │  │ C3  │             │
│  │ ✓   │  │ ✓   │  │     │             │
│  └─────┘  └──┬──┘  └─────┘             │
│              │                          │
│           ┌──▼──┐                       │
│           │ C4  │                       │
│           │ ✓   │                       │
│           └─────┘                       │
│                                         │
├─────────────────────────────────────────┤
│  23 nodes • 31 edges • 8 proven         │
└─────────────────────────────────────────┘
```

#### Data Schema

```typescript
interface GraphData {
  nodes: Array<{
    id: string;
    type: 'outcome' | 'concept';
    label: string;
    data: {
      proven?: boolean;
      progress?: number;
      description?: string;
    };
  }>;
  edges: Array<{
    from: string;
    to: string;
    type: 'requires' | 'relates_to' | 'demonstrated_by';
  }>;
}

interface GraphFilters {
  showProvenOnly: boolean;
  showOutcomes: boolean;
  showConcepts: boolean;
  outcomeId?: string;
}
```

#### Implementation

```typescript
// graph-widget.tsx
import React, { useState, useEffect, useRef } from 'react';
import { Card, Checkbox, Select } from '@openai/apps-sdk-ui';
import { Network } from 'vis-network';

interface GraphNode {
  id: string;
  type: 'outcome' | 'concept';
  label: string;
  data: {
    proven?: boolean;
    progress?: number;
    description?: string;
  };
}

interface GraphEdge {
  from: string;
  to: string;
  type: string;
}

interface GraphWidgetProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  activeOutcome?: string;
}

export function GraphWidget({ nodes, edges, activeOutcome }: GraphWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);

  const [filters, setFilters] = useState({
    showProvenOnly: false,
    showOutcomes: true,
    showConcepts: true,
  });

  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Filter nodes based on current filters
    const filteredNodes = nodes.filter(node => {
      if (filters.showProvenOnly && node.type === 'concept' && !node.data.proven) {
        return false;
      }
      if (!filters.showOutcomes && node.type === 'outcome') return false;
      if (!filters.showConcepts && node.type === 'concept') return false;
      return true;
    });

    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = edges.filter(
      e => nodeIds.has(e.from) && nodeIds.has(e.to)
    );

    // Transform for vis-network
    const visNodes = filteredNodes.map(node => ({
      id: node.id,
      label: node.label,
      color: getNodeColor(node),
      shape: node.type === 'outcome' ? 'diamond' : 'dot',
      size: node.type === 'outcome' ? 30 : 20,
    }));

    const visEdges = filteredEdges.map(edge => ({
      from: edge.from,
      to: edge.to,
      arrows: 'to',
      color: { color: '#666' },
    }));

    // Create or update network
    const options = {
      physics: {
        stabilization: { iterations: 100 },
        barnesHut: { gravitationalConstant: -2000 },
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
      },
    };

    if (networkRef.current) {
      networkRef.current.setData({ nodes: visNodes, edges: visEdges });
    } else {
      networkRef.current = new Network(
        containerRef.current,
        { nodes: visNodes, edges: visEdges },
        options
      );

      networkRef.current.on('click', (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          const node = nodes.find(n => n.id === nodeId);
          setSelectedNode(node || null);
        } else {
          setSelectedNode(null);
        }
      });
    }
  }, [nodes, edges, filters]);

  return (
    <div className="graph-widget">
      <div className="graph-filters">
        <Checkbox
          label="Outcomes"
          checked={filters.showOutcomes}
          onChange={(checked) =>
            setFilters(f => ({ ...f, showOutcomes: checked }))
          }
        />
        <Checkbox
          label="Concepts"
          checked={filters.showConcepts}
          onChange={(checked) =>
            setFilters(f => ({ ...f, showConcepts: checked }))
          }
        />
        <Checkbox
          label="Proven only"
          checked={filters.showProvenOnly}
          onChange={(checked) =>
            setFilters(f => ({ ...f, showProvenOnly: checked }))
          }
        />
      </div>

      <div ref={containerRef} className="graph-container" />

      {selectedNode && (
        <Card className="node-detail">
          <h4>{selectedNode.label}</h4>
          <p className="node-type">{selectedNode.type}</p>
          {selectedNode.data.description && (
            <p>{selectedNode.data.description}</p>
          )}
          {selectedNode.data.proven !== undefined && (
            <p className={selectedNode.data.proven ? 'proven' : 'not-proven'}>
              {selectedNode.data.proven ? '✓ Proven' : 'Not yet proven'}
            </p>
          )}
        </Card>
      )}

      <div className="graph-stats">
        {nodes.length} nodes • {edges.length} edges •
        {nodes.filter(n => n.data.proven).length} proven
      </div>
    </div>
  );
}

function getNodeColor(node: GraphNode): string {
  if (node.type === 'outcome') return '#7c3aed'; // Purple
  if (node.data.proven) return '#10b981'; // Green
  return '#6b7280'; // Gray
}
```

#### Tool Communication

- Widget receives data from `sage_graph` via `_meta.graphData`
- Read-only widget, no tool calls
- Filtering happens client-side

---

### `practice.html`

Practice/roleplay interface with real-time conversation.

#### Layout

```
┌─────────────────────────────────────────┐
│           Practice Mode                 │
│  "Price Negotiation with Skeptical      │
│   Client"                               │
├─────────────────────────────────────────┤
│  You are: Freelance consultant          │
│  SAGE plays: Skeptical potential client │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ Client: "So, $150 per hour?     │    │
│  │ That seems quite steep for this │    │
│  │ kind of work..."                │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ You: "I understand the concern. │    │
│  │ Let me explain the value..."    │    │
│  └─────────────────────────────────┘    │
│                                         │
│  [________________________] [Send]      │
│                                         │
│  [Get Hint]              [End Practice] │
│                                         │
└─────────────────────────────────────────┘

--- After ending ---

┌─────────────────────────────────────────┐
│           Practice Feedback             │
├─────────────────────────────────────────┤
│                                         │
│  What went well:                        │
│  ✓ Strong opening with value prop       │
│  ✓ Good use of anchoring technique      │
│                                         │
│  Areas to improve:                      │
│  → Could ask more discovery questions   │
│  → Rushed to discount too quickly       │
│                                         │
│  Summary:                               │
│  Good effort! You showed improvement    │
│  in value framing.                      │
│                                         │
│  Gaps revealed:                         │
│  • handling_discount_requests           │
│                                         │
│  [Continue Learning]                    │
│                                         │
└─────────────────────────────────────────┘
```

#### Data Schema

```typescript
// Start state
interface PracticeStartData {
  practiceSessionId: string;
  scenario: {
    title: string;
    sageRole: string;
    userRole: string;
    description?: string;
  };
  initialMessage: string;
}

// Message state
interface PracticeMessageData {
  characterResponse: string;
  turnNumber: number;
  hintAvailable: boolean;
}

// Feedback state
interface PracticeFeedbackData {
  summary: string;
  positives: string[];
  improvements: string[];
  revealedGaps: string[];
}
```

#### Implementation

```typescript
// practice-widget.tsx
import React, { useState, useEffect } from 'react';
import { Card, Button, Input, List } from '@openai/apps-sdk-ui';

type PracticePhase = 'active' | 'feedback';

interface Message {
  role: 'user' | 'character';
  content: string;
}

interface Scenario {
  title: string;
  sageRole: string;
  userRole: string;
  description?: string;
}

interface Feedback {
  summary: string;
  positives: string[];
  improvements: string[];
  revealedGaps: string[];
}

interface PracticeWidgetProps {
  practiceSessionId: string;
  scenario: Scenario;
  initialMessage: string;
  feedback?: Feedback;
}

export function PracticeWidget({
  practiceSessionId,
  scenario,
  initialMessage,
  feedback: initialFeedback,
}: PracticeWidgetProps) {
  const [phase, setPhase] = useState<PracticePhase>(
    initialFeedback ? 'feedback' : 'active'
  );
  const [messages, setMessages] = useState<Message[]>([
    { role: 'character', content: initialMessage }
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [feedback, setFeedback] = useState<Feedback | null>(
    initialFeedback || null
  );

  const sendMessage = async () => {
    if (!input.trim() || sending) return;

    setSending(true);
    const userMessage = input;
    setInput('');

    // Add user message optimistically
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    try {
      const result = await window.openai.callTool('sage_practice_message', {
        session_id: practiceSessionId,
        message: userMessage
      });

      // Add character response
      const response = JSON.parse(result.content);
      setMessages(prev => [...prev, {
        role: 'character',
        content: response.characterResponse
      }]);
    } catch (error) {
      console.error('Failed to send message:', error);
    }

    setSending(false);
  };

  const getHint = async () => {
    try {
      const result = await window.openai.callTool('sage_practice_hint', {
        session_id: practiceSessionId
      });
      const hint = JSON.parse(result.content).hint;

      // Show hint as a special message
      setMessages(prev => [...prev, {
        role: 'character',
        content: `💡 Hint: ${hint}`
      }]);
    } catch (error) {
      console.error('Failed to get hint:', error);
    }
  };

  const endPractice = async () => {
    try {
      const result = await window.openai.callTool('sage_practice_end', {
        session_id: practiceSessionId
      });

      const feedbackData = JSON.parse(result.content);
      setFeedback(feedbackData);
      setPhase('feedback');
    } catch (error) {
      console.error('Failed to end practice:', error);
    }
  };

  const continueLearning = () => {
    window.openai.sendFollowUpMessage(
      "I finished the practice session. What should I focus on next?"
    );
  };

  if (phase === 'feedback' && feedback) {
    return (
      <Card className="practice-feedback">
        <h2>Practice Feedback</h2>

        <div className="feedback-section">
          <h3>What went well</h3>
          <List>
            {feedback.positives.map((item, i) => (
              <List.Item key={i} icon="checkmark">{item}</List.Item>
            ))}
          </List>
        </div>

        <div className="feedback-section">
          <h3>Areas to improve</h3>
          <List>
            {feedback.improvements.map((item, i) => (
              <List.Item key={i} icon="arrow-right">{item}</List.Item>
            ))}
          </List>
        </div>

        <div className="feedback-summary">
          <p>{feedback.summary}</p>
        </div>

        {feedback.revealedGaps.length > 0 && (
          <div className="revealed-gaps">
            <h4>Gaps to work on:</h4>
            <ul>
              {feedback.revealedGaps.map((gap, i) => (
                <li key={i}>{gap.replace(/_/g, ' ')}</li>
              ))}
            </ul>
          </div>
        )}

        <Button onClick={continueLearning}>Continue Learning</Button>
      </Card>
    );
  }

  return (
    <Card className="practice-active">
      <div className="practice-header">
        <h2>{scenario.title}</h2>
        <p className="roles">
          You: <strong>{scenario.userRole}</strong> |
          SAGE: <strong>{scenario.sageRole}</strong>
        </p>
      </div>

      <div className="practice-messages">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`message ${msg.role}`}
          >
            <span className="role-label">
              {msg.role === 'character' ? scenario.sageRole : 'You'}:
            </span>
            <p>{msg.content}</p>
          </div>
        ))}
      </div>

      <div className="practice-input">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Your response..."
          disabled={sending}
        />
        <Button onClick={sendMessage} disabled={sending || !input.trim()}>
          Send
        </Button>
      </div>

      <div className="practice-actions">
        <Button variant="secondary" onClick={getHint}>
          Get Hint
        </Button>
        <Button variant="danger" onClick={endPractice}>
          End Practice
        </Button>
      </div>
    </Card>
  );
}
```

#### Tool Communication

1. Widget receives initial data from `sage_practice_start`
2. During practice, calls `sage_practice_message` for each user turn
3. Can call `sage_practice_hint` for hints (not shown in main conversation)
4. On end, calls `sage_practice_end` and displays feedback
5. Triggers follow-up message to continue learning

---

## Widget Security

### Sandboxing

Widgets run in sandboxed iframes with:
- No direct DOM access to parent
- Limited network access (only to approved origins)
- No localStorage/sessionStorage persistence
- Communication only via `window.openai` API

### Tool Access Control

```python
# MCP server controls which tools widgets can call
@mcp.tool(
    annotations={
        "openai/widgetAccessible": True  # Allow widget to call
    }
)
async def sage_checkin(...):
    ...
```

### Session Validation

Widgets receive session IDs but must still authenticate:
- Session ID passed via `_meta.openai/widgetSessionId`
- Backend validates session ownership on every tool call
- OAuth token passed through from MCP server

---

## Widget State Management

### Persistent State

```typescript
// Save state that survives widget re-renders
window.openai.setWidgetState({
  step: 2,
  partialData: { energy: 'medium' }
});

// State is restored on next render
const savedState = window.openai.getWidgetState();
```

### Sync with MCP Server

```typescript
// Widget reports data back
await window.openai.callTool('sage_checkin', data);

// Server updates UnifiedSessionState
// Next widget render receives updated data
```

---

## Widget Styling

### Design Tokens

```css
:root {
  /* SAGE brand colors */
  --sage-primary: #7c3aed;    /* Purple */
  --sage-success: #10b981;    /* Green - proven */
  --sage-warning: #f59e0b;    /* Amber - in progress */
  --sage-muted: #6b7280;      /* Gray - unproven */

  /* Spacing */
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;

  /* Typography */
  --font-family: system-ui, -apple-system, sans-serif;
  --font-size-sm: 14px;
  --font-size-base: 16px;
  --font-size-lg: 20px;
}
```

### Responsive Design

```css
/* Widgets should work in various container sizes */
.widget-container {
  max-width: 100%;
  padding: var(--spacing-md);
}

@media (max-width: 400px) {
  .graph-container {
    height: 250px;
  }

  .stats-row {
    flex-direction: column;
  }
}
```

---

## Build & Deployment

### Widget Build Process

```bash
# Build widgets for production
cd chatgpt-app/widgets
npm run build

# Output structure
dist/
├── checkin.html
├── progress.html
├── graph.html
├── practice.html
└── assets/
    ├── widget.js
    └── widget.css
```

### Resource Registration

```python
# MCP server registers widget resources
from mcp.server import McpServer

mcp = McpServer("sage")

@mcp.resource("ui://widget/checkin.html")
async def get_checkin_widget():
    return load_widget("checkin.html")

@mcp.resource("ui://widget/progress.html")
async def get_progress_widget():
    return load_widget("progress.html")
```

### CDN Hosting

Widgets are served from:
- Development: Local dev server
- Production: CDN (e.g., Cloudflare, Vercel Edge)

---

## Testing Widgets

### Unit Testing

```typescript
// widget.test.tsx
import { render, fireEvent, waitFor } from '@testing-library/react';
import { CheckinWidget } from './checkin-widget';

// Mock window.openai
const mockOpenai = {
  callTool: jest.fn(),
  sendFollowUpMessage: jest.fn(),
};
window.openai = mockOpenai;

describe('CheckinWidget', () => {
  it('calls sage_checkin on submit', async () => {
    const { getByText, getByLabelText } = render(
      <CheckinWidget sessionId="test-123" />
    );

    fireEvent.change(getByLabelText(/focus/i), {
      target: { value: 'Test intention' }
    });
    fireEvent.click(getByText('Start Session'));

    await waitFor(() => {
      expect(mockOpenai.callTool).toHaveBeenCalledWith(
        'sage_checkin',
        expect.objectContaining({
          session_id: 'test-123',
          intention: 'Test intention'
        })
      );
    });
  });
});
```

### Integration Testing

```python
# Test widget + MCP tool integration
async def test_checkin_flow():
    # Start session (returns widget)
    result = await mcp.call_tool("sage_start_session", {})
    assert result._meta["openai/outputTemplate"] == "ui://widget/checkin.html"

    session_id = result.structuredContent["sessionId"]

    # Simulate widget calling checkin
    checkin_result = await mcp.call_tool("sage_checkin", {
        "session_id": session_id,
        "energy": "medium",
        "time_available": 30,
        "intention": "Learn pricing"
    })

    assert checkin_result.structuredContent["status"] == "ready"
```
