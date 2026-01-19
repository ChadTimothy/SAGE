/**
 * Type definitions for ChatGPT Apps SDK (window.openai)
 * Based on https://developers.openai.com/apps-sdk
 */

export type DisplayMode = 'inline' | 'pip' | 'fullscreen';

export interface DisplayModeResult {
  mode: DisplayMode;
}

export interface FollowUpOptions {
  prompt: string;
}

export interface ExternalLinkOptions {
  href: string;
}

export interface ToolCallResult<T = unknown> {
  result: T;
  structuredContent?: Record<string, unknown>;
}

export interface OpenAIClient {
  /** Call an MCP tool */
  callTool<T = unknown>(name: string, args?: Record<string, unknown>): Promise<ToolCallResult<T>>;

  /** Set persistent widget state (exposed to ChatGPT model) */
  setWidgetState<T extends object>(payload: T): void;

  /** Hydrated widget state from host */
  widgetState?: unknown;

  /** Request display mode change (inline, pip, fullscreen) */
  requestDisplayMode(options: { mode: DisplayMode }): Promise<DisplayModeResult>;

  /** Close the widget */
  requestClose(): void;

  /** Send a follow-up message to ChatGPT */
  sendFollowUpMessage(options: FollowUpOptions): Promise<void>;

  /** Open an external link */
  openExternal(options: ExternalLinkOptions): void;
}

declare global {
  interface Window {
    openai?: OpenAIClient;
  }
}

// MCP Tool Response Types

export interface SessionStartResponse {
  session_id: string;
  message: string;
  widget_html?: string;
  learner_created?: boolean;
}

export interface CheckinResponse {
  adaptations: string[];
  session_context: {
    energy: string;
    time_available: string;
    mindset?: string;
    environment?: string;
  };
  message: string;
}

export interface ProgressResponse {
  total_sessions: number;
  total_proofs: number;
  recent_concepts: ConceptSummary[];
  active_outcomes: OutcomeSummary[];
  widget_html?: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
  widget_html?: string;
}

export interface PracticeStartResponse {
  practice_id: string;
  scenario: {
    title: string;
    description: string;
    sage_role: string;
    user_role: string;
  };
  concept: string;
  opening_message: string;
  widget_html?: string;
}

export interface PracticeRespondResponse {
  feedback: string;
  score: number;
  areas_good: string[];
  areas_improve: string[];
  suggestions: string[];
  continue_practice: boolean;
}

export interface PracticeEndResponse {
  practice_complete: boolean;
  summary: string;
  key_learnings: string[];
  proof_created?: boolean;
  proof_id?: string;
}

// Widget State Types

export interface CheckinState {
  energy?: 'low' | 'medium' | 'high';
  timeAvailable?: 'quick' | 'normal' | 'deep';
  mindset?: string;
  setting?: string;
  submitted?: boolean;
}

export interface ProgressState {
  lastFetched?: number;
  data?: ProgressResponse;
}

export interface GraphState {
  lastFetched?: number;
  data?: GraphResponse;
  selectedNodeId?: string;
  filters?: {
    nodeTypes: string[];
    showEdges: boolean;
  };
}

export interface PracticeState {
  practiceId?: string;
  scenario?: PracticeStartResponse['scenario'];
  messages: PracticeMessage[];
  score?: number;
  completed?: boolean;
}

export interface PracticeMessage {
  role: 'sage' | 'user';
  content: string;
  timestamp: number;
}

// Supporting Types

export interface ConceptSummary {
  id: string;
  name: string;
  display_name: string;
  status: string;
  proof_count: number;
}

export interface OutcomeSummary {
  id: string;
  description: string;
  status: string;
  progress_percentage: number;
}

export interface GraphNode {
  id: string;
  type: 'learner' | 'outcome' | 'concept' | 'proof' | 'session';
  label: string;
  data: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  from: string;
  to: string;
  type: string;
  label?: string;
}
