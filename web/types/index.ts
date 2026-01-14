/**
 * SAGE Frontend TypeScript Types
 */

// Learner types
export interface Learner {
  id: string;
  name: string;
  age_group: "child" | "teen" | "adult";
  skill_level: "beginner" | "intermediate" | "advanced";
  active_outcome_id: string | null;
  total_sessions: number;
  total_proofs: number;
  created_at: string;
}

export interface LearnerCreate {
  name: string;
  age_group: "child" | "teen" | "adult";
  skill_level: "beginner" | "intermediate" | "advanced";
}

// Session types
export interface Session {
  id: string;
  learner_id: string;
  outcome_id: string | null;
  started_at: string;
  ended_at: string | null;
  message_count: number;
}

export interface SessionCreate {
  learner_id: string;
  outcome_id?: string;
}

// Chat types
export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
  mode?: DialogueMode;
}

export type DialogueMode =
  | "check_in"
  | "followup"
  | "outcome_discovery"
  | "framing"
  | "probing"
  | "teaching"
  | "verification"
  | "outcome_check";

// Outcome types
export interface Outcome {
  id: string;
  learner_id: string;
  description: string;
  status: "active" | "achieved" | "paused" | "abandoned";
  created_at: string;
  achieved_at: string | null;
}

// Proof types
export interface Proof {
  id: string;
  concept_id: string;
  learner_id: string;
  demonstration_type: "explanation" | "application" | "both";
  confidence: number;
  earned_at: string;
}

// Graph visualization types
export interface GraphNode {
  id: string;
  type: "learner" | "outcome" | "concept" | "proof";
  label: string;
  data: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  from_id: string;
  to_id: string;
  edge_type: string;
}

export interface LearnerGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// Learner state (full UI state)
export interface LearnerState {
  learner: Learner;
  active_outcome: {
    id: string;
    description: string;
    status: string;
  } | null;
  recent_concepts: Array<{
    id: string;
    name: string;
    display_name: string;
    status: string;
  }>;
  recent_proofs: Array<{
    id: string;
    concept_id: string;
    demonstration_type: string;
    confidence: number;
    earned_at: string;
  }>;
  pending_followups: Array<{
    id: string;
    context: string;
    planned_date: string | null;
  }>;
}

// WebSocket message types
export interface WSMessage {
  type: "user" | "assistant" | "error" | "status";
  content: string;
  mode?: DialogueMode;
  timestamp?: string;
}

// Session context types (Set/Setting/Intention)
export interface SessionContext {
  timeAvailable: "quick" | "focused" | "deep";
  energyLevel: number;
  mindset: string;
}

// Concept snapshot with status
export interface ConceptSnapshot {
  id: string;
  name: string;
  display_name: string;
  status: "proven" | "in_progress" | "identified";
}

// Application event for upcoming applications
export interface ApplicationSnapshot {
  id: string;
  context: string;
  planned_date: string | null;
}

// Outcome snapshot for sidebar
export interface OutcomeSnapshot {
  id: string;
  description: string;
  status: "active" | "achieved" | "paused" | "abandoned";
  concepts: ConceptSnapshot[];
}

// Learner stats for sidebar
export interface LearnerStats {
  total_proofs: number;
  completed_goals: number;
  total_sessions: number;
}

// API response types
export interface ApiError {
  detail: string;
}
