/**
 * useUnifiedState - Cross-Modality State Synchronization Hook
 *
 * Manages state synchronization between voice and UI modalities.
 * Provides unified access to session state with automatic backend sync.
 *
 * Part of #81 - Cross-Modality State Synchronization
 */

import { useState, useEffect, useCallback, useRef } from "react";
import {
  api,
  UnifiedSessionState,
  PendingDataRequest,
  CheckInData,
} from "@/lib/api";
import { sessionPersistence } from "@/lib/session-persistence";

export type ModalityPreference = "chat" | "voice";

export interface UseUnifiedStateOptions {
  /** Sync with backend on every state change (default: true) */
  syncWithBackend?: boolean;
  /** Auto-recover state on mount (default: true) */
  autoRecover?: boolean;
}

export interface UseUnifiedStateReturn {
  /** Current session state from backend */
  state: UnifiedSessionState | null;
  /** Loading state */
  loading: boolean;
  /** Error if any */
  error: Error | null;
  /** Current modality preference */
  modality: ModalityPreference;
  /** Whether voice is enabled */
  voiceEnabled: boolean;
  /** Pending data collection request */
  pendingRequest: PendingDataRequest | null;
  /** Check-in data */
  checkInData: CheckInData | null;
  /** Switch modality preference */
  setModality: (modality: ModalityPreference) => Promise<void>;
  /** Toggle voice enabled state */
  setVoiceEnabled: (enabled: boolean) => void;
  /** Merge newly collected data into state */
  mergeData: (data: Record<string, unknown>) => Promise<void>;
  /** Get prefill data for a specific intent */
  getPrefillData: (intent: string) => Promise<Record<string, unknown>>;
  /** Refresh state from backend */
  refresh: () => Promise<void>;
  /** Clear all session state */
  clearState: () => Promise<void>;
  /** Check if there's recoverable state */
  hasRecoverableState: boolean;
}

/**
 * Hook for cross-modality state synchronization.
 *
 * Keeps voice and UI modalities in sync, enabling seamless
 * switching mid-session without losing context or collected data.
 *
 * @example
 * ```tsx
 * function ChatPage() {
 *   const { state, modality, setModality, mergeData } = useUnifiedState(sessionId);
 *
 *   // Switch to voice mode
 *   const enableVoice = () => setModality('voice');
 *
 *   // Merge data from UI form
 *   const handleFormData = (data) => mergeData(data);
 *
 *   return (
 *     <div>
 *       <button onClick={enableVoice}>Switch to Voice</button>
 *       {state?.pending_data_request && (
 *         <Form initialData={state.pending_data_request.collected_data} />
 *       )}
 *     </div>
 *   );
 * }
 * ```
 */
export function useUnifiedState(
  sessionId: string | null,
  options: UseUnifiedStateOptions = {}
): UseUnifiedStateReturn {
  const { syncWithBackend = true, autoRecover = true } = options;

  const [state, setState] = useState<UnifiedSessionState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [modality, setModalityState] = useState<ModalityPreference>("chat");
  const [voiceEnabled, setVoiceEnabledState] = useState(false);

  // Track if we've done initial load
  const initialLoadDone = useRef(false);

  // Check for recoverable state
  const hasRecoverableState = sessionPersistence.hasRecoverableState();

  // Fetch state from backend
  const fetchState = useCallback(async () => {
    if (!sessionId) return;

    setLoading(true);
    setError(null);

    try {
      const backendState = await api.getSessionState(sessionId);
      setState(backendState);

      // Sync local state with backend
      setModalityState(backendState.modality_preference);
      setVoiceEnabledState(backendState.voice_enabled);

      // Also update localStorage for persistence
      sessionPersistence.setModalityPreference(backendState.modality_preference);
      sessionPersistence.setVoiceEnabled(backendState.voice_enabled);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to fetch state"));
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // Initialize on mount
  useEffect(() => {
    if (!sessionId || initialLoadDone.current) return;

    initialLoadDone.current = true;

    // Recover local state first
    if (autoRecover) {
      const storedModality = sessionPersistence.getModalityPreference();
      const storedVoice = sessionPersistence.getVoiceEnabled();
      setModalityState(storedModality);
      setVoiceEnabledState(storedVoice);
    }

    // Sync with backend
    if (syncWithBackend) {
      fetchState();
    }
  }, [sessionId, autoRecover, syncWithBackend, fetchState]);

  // Update session ID in persistence
  useEffect(() => {
    if (sessionId) {
      sessionPersistence.setSessionId(sessionId);
    }
  }, [sessionId]);

  // Set modality preference
  const setModality = useCallback(
    async (newModality: ModalityPreference) => {
      setModalityState(newModality);
      sessionPersistence.setModalityPreference(newModality);

      if (sessionId && syncWithBackend) {
        try {
          await api.setModalityPreference(sessionId, newModality);
        } catch (err) {
          console.error("Failed to sync modality preference:", err);
        }
      }
    },
    [sessionId, syncWithBackend]
  );

  // Set voice enabled
  const setVoiceEnabled = useCallback((enabled: boolean) => {
    setVoiceEnabledState(enabled);
    sessionPersistence.setVoiceEnabled(enabled);
  }, []);

  // Merge collected data
  const mergeData = useCallback(
    async (data: Record<string, unknown>) => {
      // Update local pending data
      const currentPending = sessionPersistence.getPendingData();
      if (currentPending) {
        sessionPersistence.updatePendingDataFields(data);
      }

      // Sync with backend
      if (sessionId && syncWithBackend) {
        try {
          const updatedState = await api.mergeCollectedData(sessionId, data);
          setState(updatedState);
        } catch (err) {
          console.error("Failed to merge data with backend:", err);
          throw err;
        }
      }
    },
    [sessionId, syncWithBackend]
  );

  // Get prefill data for intent
  const getPrefillData = useCallback(
    async (intent: string): Promise<Record<string, unknown>> => {
      if (!sessionId) return {};

      try {
        return await api.getPrefillData(sessionId, intent);
      } catch (err) {
        console.error("Failed to get prefill data:", err);
        return {};
      }
    },
    [sessionId]
  );

  // Refresh state from backend
  const refresh = useCallback(async () => {
    await fetchState();
  }, [fetchState]);

  // Clear all state
  const clearState = useCallback(async () => {
    // Clear local storage
    sessionPersistence.clearAll();

    // Reset local state
    setState(null);
    setModalityState("chat");
    setVoiceEnabledState(false);

    // Clear backend state
    if (sessionId) {
      try {
        await api.clearSessionState(sessionId);
      } catch (err) {
        console.error("Failed to clear backend state:", err);
      }
    }
  }, [sessionId]);

  return {
    state,
    loading,
    error,
    modality,
    voiceEnabled,
    pendingRequest: state?.pending_data_request ?? null,
    checkInData: state?.check_in_data ?? null,
    setModality,
    setVoiceEnabled,
    mergeData,
    getPrefillData,
    refresh,
    clearState,
    hasRecoverableState,
  };
}

export default useUnifiedState;
