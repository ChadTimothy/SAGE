/**
 * SAGE API Client
 */

import type {
  Learner,
  LearnerCreate,
  LearnerState,
  LearnerGraph,
  Session,
  SessionCreate,
  Outcome,
  Proof,
  ApiError,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
      }));
      throw new Error(error.detail);
    }

    return response.json();
  }

  // Learner endpoints
  async createLearner(data: LearnerCreate): Promise<Learner> {
    return this.request<Learner>("/api/learners", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getLearner(id: string): Promise<Learner> {
    return this.request<Learner>(`/api/learners/${id}`);
  }

  async getLearnerState(id: string): Promise<LearnerState> {
    return this.request<LearnerState>(`/api/learners/${id}/state`);
  }

  async getLearnerOutcomes(id: string): Promise<Outcome[]> {
    return this.request<Outcome[]>(`/api/learners/${id}/outcomes`);
  }

  async getLearnerProofs(id: string): Promise<Proof[]> {
    return this.request<Proof[]>(`/api/learners/${id}/proofs`);
  }

  async getLearnerGraph(id: string): Promise<LearnerGraph> {
    return this.request<LearnerGraph>(`/api/learners/${id}/graph`);
  }

  // Session endpoints
  async createSession(data: SessionCreate): Promise<Session> {
    return this.request<Session>("/api/sessions", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getSession(id: string): Promise<Session> {
    return this.request<Session>(`/api/sessions/${id}`);
  }

  async endSession(id: string): Promise<Session> {
    return this.request<Session>(`/api/sessions/${id}/end`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  }

  // Health check
  async health(): Promise<{ status: string }> {
    return this.request<{ status: string }>("/health");
  }

  // Practice endpoints
  async startPractice(data: {
    scenario_id: string;
    title: string;
    sage_role: string;
    user_role: string;
    description?: string;
    learner_id?: string;
  }): Promise<{ session_id: string; initial_message: string }> {
    return this.request("/api/practice/start", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async sendPracticeMessage(
    sessionId: string,
    content: string
  ): Promise<{ message: string }> {
    return this.request(`/api/practice/${sessionId}/message`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
  }

  async getPracticeHint(sessionId: string): Promise<{ hint: string }> {
    return this.request(`/api/practice/${sessionId}/hint`, {
      method: "POST",
    });
  }

  async endPractice(sessionId: string): Promise<{
    positives: string[];
    improvements: string[];
    summary: string;
    revealed_gaps: string[];
  }> {
    return this.request(`/api/practice/${sessionId}/end`, {
      method: "POST",
    });
  }

  // ============================================
  // Cross-Modality State Sync Endpoints (#81)
  // ============================================

  async getSessionState(sessionId: string): Promise<UnifiedSessionState> {
    return this.request<UnifiedSessionState>(
      `/api/sessions/${sessionId}/state`
    );
  }

  async setModalityPreference(
    sessionId: string,
    modality: "chat" | "voice"
  ): Promise<{ status: string; modality: string }> {
    return this.request(`/api/sessions/${sessionId}/modality`, {
      method: "POST",
      body: JSON.stringify({ modality }),
    });
  }

  async mergeCollectedData(
    sessionId: string,
    data: Record<string, unknown>
  ): Promise<UnifiedSessionState> {
    return this.request<UnifiedSessionState>(
      `/api/sessions/${sessionId}/merge-data`,
      {
        method: "POST",
        body: JSON.stringify({ data }),
      }
    );
  }

  async getPrefillData(
    sessionId: string,
    intent: string
  ): Promise<Record<string, unknown>> {
    return this.request<Record<string, unknown>>(
      `/api/sessions/${sessionId}/prefill/${intent}`
    );
  }

  async clearSessionState(
    sessionId: string
  ): Promise<{ status: string }> {
    return this.request(`/api/sessions/${sessionId}/state`, {
      method: "DELETE",
    });
  }
}

// Type for unified session state from backend
export interface UnifiedSessionState {
  session_id: string;
  modality_preference: "chat" | "voice";
  pending_data_request: PendingDataRequest | null;
  check_in_data: CheckInData;
  check_in_complete: boolean;
  messages: TaggedMessage[];
  voice_enabled: boolean;
  last_activity: string;
}

export interface PendingDataRequest {
  intent: string;
  required_fields: string[];
  collected_data: Record<string, unknown>;
  voice_prompt: string;
}

export interface CheckInData {
  energy_level: number | null;
  time_available: string | null;
  mindset: string | null;
  physical_environment: string | null;
}

export interface TaggedMessage {
  role: string;
  content: string;
  source_modality: "chat" | "voice";
  timestamp: string;
}

// Export singleton instance
export const api = new ApiClient();

// Export class for testing/custom instances
export { ApiClient };
