"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { PracticeScenario, PracticeFeedbackData } from "@/components/practice";

export interface PracticeMessage {
  id: string;
  role: "user" | "sage-character" | "sage-hint";
  content: string;
  timestamp: string;
}

export interface UsePracticeModeOptions {
  onPracticeStart?: (scenario: PracticeScenario) => void;
  onPracticeEnd?: (feedback: PracticeFeedbackData) => void;
  onHintRequest?: () => void;
}

export interface UsePracticeModeReturn {
  isActive: boolean;
  isLoading: boolean;
  scenario: PracticeScenario | null;
  sessionId: string | null;
  messages: PracticeMessage[];
  showSetup: boolean;
  showFeedback: boolean;
  feedback: PracticeFeedbackData | null;
  error: string | null;
  openSetup: () => void;
  closeSetup: () => void;
  startPractice: (scenario: PracticeScenario) => Promise<void>;
  endPractice: () => Promise<void>;
  requestHint: () => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  closeFeedback: () => void;
  practiceAgain: () => void;
}

export function usePracticeMode({
  onPracticeStart,
  onPracticeEnd,
  onHintRequest,
}: UsePracticeModeOptions = {}): UsePracticeModeReturn {
  const [isActive, setIsActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [scenario, setScenario] = useState<PracticeScenario | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<PracticeMessage[]>([]);
  const [showSetup, setShowSetup] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState<PracticeFeedbackData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const openSetup = useCallback(() => {
    setShowSetup(true);
    setError(null);
  }, []);

  const closeSetup = useCallback(() => {
    setShowSetup(false);
  }, []);

  const startPractice = useCallback(
    async (newScenario: PracticeScenario) => {
      setIsLoading(true);
      setError(null);

      try {
        // Call backend to start practice session
        // Backend extracts learner_id from JWT token
        const response = await api.startPractice({
          scenario_id: newScenario.id,
          title: newScenario.title,
          sage_role: newScenario.sageRole,
          user_role: newScenario.userRole,
          description: newScenario.description,
        });

        setScenario(newScenario);
        setSessionId(response.session_id);
        setIsActive(true);
        setShowSetup(false);
        setFeedback(null);

        // Add initial character message
        const initialMessage: PracticeMessage = {
          id: `practice-${Date.now()}`,
          role: "sage-character",
          content: response.initial_message,
          timestamp: new Date().toISOString(),
        };
        setMessages([initialMessage]);

        onPracticeStart?.(newScenario);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to start practice");
      } finally {
        setIsLoading(false);
      }
    },
    [onPracticeStart]
  );

  const sendMessage = useCallback(
    async (content: string) => {
      if (!isActive || !sessionId) return;

      setIsLoading(true);
      setError(null);

      // Add user message immediately
      const userMessage: PracticeMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      try {
        // Get character response from backend
        const response = await api.sendPracticeMessage(sessionId, content);

        const characterMessage: PracticeMessage = {
          id: `character-${Date.now()}`,
          role: "sage-character",
          content: response.message,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, characterMessage]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to send message");
      } finally {
        setIsLoading(false);
      }
    },
    [isActive, sessionId]
  );

  const endPractice = useCallback(async () => {
    if (!scenario || !sessionId) return;

    setIsLoading(true);
    setError(null);

    try {
      // Get feedback from backend
      const response = await api.endPractice(sessionId);

      const generatedFeedback: PracticeFeedbackData = {
        scenario,
        positives: response.positives,
        improvements: response.improvements,
        summary: response.summary,
      };

      setFeedback(generatedFeedback);
      setIsActive(false);
      setShowFeedback(true);
      onPracticeEnd?.(generatedFeedback);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to end practice");
    } finally {
      setIsLoading(false);
    }
  }, [scenario, sessionId, onPracticeEnd]);

  const requestHint = useCallback(async () => {
    if (!isActive || !sessionId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.getPracticeHint(sessionId);

      const hintMessage: PracticeMessage = {
        id: `hint-${Date.now()}`,
        role: "sage-hint",
        content: response.hint,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, hintMessage]);
      onHintRequest?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get hint");
    } finally {
      setIsLoading(false);
    }
  }, [isActive, sessionId, onHintRequest]);

  const closeFeedback = useCallback(() => {
    setShowFeedback(false);
    setScenario(null);
    setSessionId(null);
    setMessages([]);
  }, []);

  const practiceAgain = useCallback(() => {
    if (scenario) {
      setShowFeedback(false);
      startPractice(scenario);
    }
  }, [scenario, startPractice]);

  return {
    isActive,
    isLoading,
    scenario,
    sessionId,
    messages,
    showSetup,
    showFeedback,
    feedback,
    error,
    openSetup,
    closeSetup,
    startPractice,
    endPractice,
    requestHint,
    sendMessage,
    closeFeedback,
    practiceAgain,
  };
}
