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
  /** UI tree for ad-hoc UI generation (assistant messages only) */
  ui_tree?: UITreeNode;
  /** Pending data request for multi-turn collection (assistant messages only) */
  pending_data_request?: PendingDataRequest;
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

// =============================================================================
// Voice/UI Parity Types (Ad-hoc UI Generation)
// =============================================================================

/**
 * A node in the composable UI component tree.
 * Rendered recursively by the frontend using primitive components.
 */
export interface UITreeNode {
  /** Primitive component name (Stack, Text, Button, RadioGroup, etc.) */
  component: string;
  /** Component properties */
  props: Record<string, unknown>;
  /** Child nodes for container components */
  children?: UITreeNode[];
}

/**
 * Hints for text-to-speech optimization.
 */
export interface VoiceHints {
  /** Full voice alternative for UI-based content */
  voice_fallback?: string;
  /** Words to emphasize in speech */
  emphasis?: string[];
  /** Words after which to pause */
  pause_after?: string[];
  /** Suggested emotional tone */
  tone?: string;
  /** Request slower speech rate */
  slower?: boolean;
}

/**
 * Tracks incomplete data collection across conversation turns.
 * Enables multi-turn data collection and cross-modality state sync.
 */
export interface PendingDataRequest {
  /** What we're trying to collect (e.g., 'session_check_in') */
  intent: string;
  /** Data collected so far */
  collected_data: Record<string, unknown>;
  /** Fields still needed */
  missing_fields: string[];
  /** Validation errors to show user */
  validation_errors: string[];
}

// =============================================================================
// WebSocket Message Types
// =============================================================================

export type WSMessageType = "chunk" | "complete" | "error";

export interface WSChunkMessage {
  type: "chunk";
  content: string;
}

export interface WSCompleteMessage {
  type: "complete";
  response: {
    message: string;
    mode: string;
    transition_to: string | null;
    transition_reason: string | null;
    gap_identified: {
      name: string;
      display_name: string;
      description: string;
    } | null;
    proof_earned: {
      concept_id: string;
      demonstration_type: string;
      evidence: string;
    } | null;
    outcome_achieved: boolean;

    // Voice/UI Parity fields (ad-hoc UI generation)
    ui_tree: UITreeNode | null;
    voice_hints: VoiceHints | null;
    pending_data_request: PendingDataRequest | null;
    ui_purpose: string | null;
    estimated_interaction_time: number | null;
  };
}

export interface WSErrorMessage {
  type: "error";
  message: string;
}

export type WSMessage = WSChunkMessage | WSCompleteMessage | WSErrorMessage;

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

// Knowledge Graph Visualization Types
export type KnowledgeNodeType = "outcome" | "concept";
export type KnowledgeNodeStatus = "proven" | "in_progress" | "identified" | "active" | "achieved";
export type KnowledgeEdgeType = "requires" | "relates_to" | "builds_on";

export interface KnowledgeNode {
  id: string;
  type: KnowledgeNodeType;
  label: string;
  status: KnowledgeNodeStatus;
  description?: string;
  proofCount?: number;
}

export interface KnowledgeEdge {
  id: string;
  from: string;
  to: string;
  type: KnowledgeEdgeType;
}

export interface KnowledgeGraphData {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}

export interface GraphFilterState {
  selectedOutcome: string | null;
  showProvenOnly: boolean;
  showConcepts: boolean;
  showOutcomes: boolean;
}
