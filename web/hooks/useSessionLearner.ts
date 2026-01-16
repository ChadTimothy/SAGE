"use client";

/**
 * Hook to get learner data from NextAuth session.
 *
 * This hook replaces useLearner for authenticated contexts.
 * It sources the learner_id from the NextAuth session rather than localStorage,
 * ensuring the learner data is always in sync with authentication state.
 */

import { useSession } from "next-auth/react";
import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { Learner, LearnerState } from "@/types";

function getErrorMessage(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export function useSessionLearner() {
  const { data: session, status } = useSession();
  const [learner, setLearner] = useState<Learner | null>(null);
  const [state, setState] = useState<LearnerState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const learnerId = session?.user?.learner_id;

  const loadAll = useCallback(async (id: string) => {
    const [learnerData, stateData] = await Promise.all([
      api.getLearner(id),
      api.getLearnerState(id),
    ]);
    setLearner(learnerData);
    setState(stateData);
  }, []);

  useEffect(() => {
    if (status === "loading") return;

    if (status !== "authenticated" || !learnerId) {
      setIsLoading(false);
      setLearner(null);
      setState(null);
      return;
    }

    setIsLoading(true);
    setError(null);
    loadAll(learnerId)
      .catch((err) => setError(getErrorMessage(err, "Failed to load learner")))
      .finally(() => setIsLoading(false));
  }, [learnerId, status, loadAll]);

  const refreshState = useCallback(async () => {
    if (!learnerId) return;
    try {
      setState(await api.getLearnerState(learnerId));
    } catch (err) {
      setError(getErrorMessage(err, "Failed to refresh state"));
    }
  }, [learnerId]);

  const refreshLearner = useCallback(async () => {
    if (!learnerId) return;
    try {
      await loadAll(learnerId);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to refresh learner"));
    }
  }, [learnerId, loadAll]);

  return {
    learner,
    state,
    isLoading,
    error,
    learnerId,
    hasLearner: !!learner,
    isAuthenticated: status === "authenticated",
    authStatus: status,
    refreshState,
    refreshLearner,
  };
}
