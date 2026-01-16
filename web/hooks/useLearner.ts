"use client";

import { useState, useCallback, useEffect } from "react";
import { api } from "@/lib/api";
import type { Learner, LearnerState, LearnerCreate } from "@/types";

const LEARNER_ID_KEY = "sage_learner_id";

/**
 * @deprecated Use useSessionLearner instead for NextAuth integration.
 * This hook uses localStorage which is not tied to authentication state.
 */
export function useLearner() {
  // DEPRECATION WARNING
  if (process.env.NODE_ENV === "development") {
    console.warn(
      "useLearner is deprecated. Use useSessionLearner instead for NextAuth integration."
    );
  }

  const [learner, setLearner] = useState<Learner | null>(null);
  const [state, setState] = useState<LearnerState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load learner from localStorage on mount
  useEffect(() => {
    const loadLearner = async () => {
      const storedId = localStorage.getItem(LEARNER_ID_KEY);
      if (!storedId) {
        setIsLoading(false);
        return;
      }

      try {
        const learnerData = await api.getLearner(storedId);
        setLearner(learnerData);
        const stateData = await api.getLearnerState(storedId);
        setState(stateData);
      } catch (err) {
        // Learner not found, clear stored ID
        localStorage.removeItem(LEARNER_ID_KEY);
        setError(err instanceof Error ? err.message : "Failed to load learner");
      } finally {
        setIsLoading(false);
      }
    };

    loadLearner();
  }, []);

  // Create new learner
  const createLearner = useCallback(async (data: LearnerCreate) => {
    setIsLoading(true);
    setError(null);

    try {
      const newLearner = await api.createLearner(data);
      localStorage.setItem(LEARNER_ID_KEY, newLearner.id);
      setLearner(newLearner);
      const stateData = await api.getLearnerState(newLearner.id);
      setState(stateData);
      return newLearner;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create learner";
      setError(message);
      throw new Error(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Refresh learner state
  const refreshState = useCallback(async () => {
    if (!learner) return;

    try {
      const stateData = await api.getLearnerState(learner.id);
      setState(stateData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh state");
    }
  }, [learner]);

  // Clear learner (logout)
  const clearLearner = useCallback(() => {
    localStorage.removeItem(LEARNER_ID_KEY);
    setLearner(null);
    setState(null);
  }, []);

  return {
    learner,
    state,
    isLoading,
    error,
    createLearner,
    refreshState,
    clearLearner,
    hasLearner: !!learner,
  };
}
