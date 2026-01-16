/**
 * Session Persistence Layer
 *
 * Manages localStorage/sessionStorage for cross-modality state sync.
 * Enables recovery after browser refresh and state sharing across components.
 *
 * Part of #81 - Cross-Modality State Synchronization
 */

export const STORAGE_KEYS = {
  SESSION_ID: "sage:session_id",
  MODALITY_PREF: "sage:modality_preference",
  PENDING_DATA: "sage:pending_data",
  VOICE_ENABLED: "sage:voice_enabled",
  CHECK_IN_DATA: "sage:check_in_data",
} as const;

export type ModalityPreference = "chat" | "voice";

export interface CheckInData {
  energyLevel?: number;
  timeAvailable?: string;
  mindset?: string;
  physicalEnvironment?: string;
}

export interface PendingDataState {
  intent: string;
  collectedData: Record<string, unknown>;
  requiredFields: string[];
  timestamp: string;
}

/**
 * Session persistence utility for browser storage operations.
 */
export const sessionPersistence = {
  // ============================================
  // Session ID Management
  // ============================================

  getSessionId(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(STORAGE_KEYS.SESSION_ID);
  },

  setSessionId(sessionId: string): void {
    if (typeof window === "undefined") return;
    localStorage.setItem(STORAGE_KEYS.SESSION_ID, sessionId);
  },

  clearSessionId(): void {
    if (typeof window === "undefined") return;
    localStorage.removeItem(STORAGE_KEYS.SESSION_ID);
  },

  // ============================================
  // Modality Preference
  // ============================================

  getModalityPreference(): ModalityPreference {
    if (typeof window === "undefined") return "chat";
    const stored = localStorage.getItem(STORAGE_KEYS.MODALITY_PREF);
    return stored === "voice" ? "voice" : "chat";
  },

  setModalityPreference(modality: ModalityPreference): void {
    if (typeof window === "undefined") return;
    localStorage.setItem(STORAGE_KEYS.MODALITY_PREF, modality);
  },

  // ============================================
  // Voice Enabled State
  // ============================================

  getVoiceEnabled(): boolean {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(STORAGE_KEYS.VOICE_ENABLED) === "true";
  },

  setVoiceEnabled(enabled: boolean): void {
    if (typeof window === "undefined") return;
    localStorage.setItem(STORAGE_KEYS.VOICE_ENABLED, String(enabled));
  },

  // ============================================
  // Pending Data Collection State (Session Storage)
  // ============================================

  getPendingData(): PendingDataState | null {
    if (typeof window === "undefined") return null;
    const stored = sessionStorage.getItem(STORAGE_KEYS.PENDING_DATA);
    if (!stored) return null;
    try {
      return JSON.parse(stored) as PendingDataState;
    } catch {
      return null;
    }
  },

  setPendingData(data: PendingDataState): void {
    if (typeof window === "undefined") return;
    sessionStorage.setItem(STORAGE_KEYS.PENDING_DATA, JSON.stringify(data));
  },

  updatePendingDataFields(newData: Record<string, unknown>): void {
    if (typeof window === "undefined") return;
    const current = this.getPendingData();
    if (current) {
      current.collectedData = { ...current.collectedData, ...newData };
      current.timestamp = new Date().toISOString();
      this.setPendingData(current);
    }
  },

  clearPendingData(): void {
    if (typeof window === "undefined") return;
    sessionStorage.removeItem(STORAGE_KEYS.PENDING_DATA);
  },

  // ============================================
  // Check-in Data (Session Storage)
  // ============================================

  getCheckInData(): CheckInData | null {
    if (typeof window === "undefined") return null;
    const stored = sessionStorage.getItem(STORAGE_KEYS.CHECK_IN_DATA);
    if (!stored) return null;
    try {
      return JSON.parse(stored) as CheckInData;
    } catch {
      return null;
    }
  },

  setCheckInData(data: CheckInData): void {
    if (typeof window === "undefined") return;
    sessionStorage.setItem(STORAGE_KEYS.CHECK_IN_DATA, JSON.stringify(data));
  },

  updateCheckInData(updates: Partial<CheckInData>): void {
    if (typeof window === "undefined") return;
    const current = this.getCheckInData() || {};
    this.setCheckInData({ ...current, ...updates });
  },

  clearCheckInData(): void {
    if (typeof window === "undefined") return;
    sessionStorage.removeItem(STORAGE_KEYS.CHECK_IN_DATA);
  },

  // ============================================
  // Full State Management
  // ============================================

  /**
   * Clear all session-related storage (for logout or session end).
   */
  clearAll(): void {
    if (typeof window === "undefined") return;

    // Clear localStorage items
    localStorage.removeItem(STORAGE_KEYS.SESSION_ID);
    localStorage.removeItem(STORAGE_KEYS.MODALITY_PREF);
    localStorage.removeItem(STORAGE_KEYS.VOICE_ENABLED);

    // Clear sessionStorage items
    sessionStorage.removeItem(STORAGE_KEYS.PENDING_DATA);
    sessionStorage.removeItem(STORAGE_KEYS.CHECK_IN_DATA);
  },

  /**
   * Export current state for debugging or backend sync.
   */
  exportState(): {
    sessionId: string | null;
    modalityPreference: ModalityPreference;
    voiceEnabled: boolean;
    pendingData: PendingDataState | null;
    checkInData: CheckInData | null;
  } {
    return {
      sessionId: this.getSessionId(),
      modalityPreference: this.getModalityPreference(),
      voiceEnabled: this.getVoiceEnabled(),
      pendingData: this.getPendingData(),
      checkInData: this.getCheckInData(),
    };
  },

  /**
   * Check if there's an active session with recoverable state.
   */
  hasRecoverableState(): boolean {
    return !!(
      this.getSessionId() &&
      (this.getPendingData() || this.getCheckInData())
    );
  },
};

export default sessionPersistence;
