"use client";

import { useState, useCallback } from "react";
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
  scenario: PracticeScenario | null;
  messages: PracticeMessage[];
  showSetup: boolean;
  showFeedback: boolean;
  feedback: PracticeFeedbackData | null;
  openSetup: () => void;
  closeSetup: () => void;
  startPractice: (scenario: PracticeScenario) => void;
  endPractice: () => void;
  requestHint: () => void;
  addMessage: (role: PracticeMessage["role"], content: string) => void;
  closeFeedback: () => void;
  practiceAgain: () => void;
}

export function usePracticeMode({
  onPracticeStart,
  onPracticeEnd,
  onHintRequest,
}: UsePracticeModeOptions = {}): UsePracticeModeReturn {
  const [isActive, setIsActive] = useState(false);
  const [scenario, setScenario] = useState<PracticeScenario | null>(null);
  const [messages, setMessages] = useState<PracticeMessage[]>([]);
  const [showSetup, setShowSetup] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState<PracticeFeedbackData | null>(null);

  const openSetup = useCallback(() => {
    setShowSetup(true);
  }, []);

  const closeSetup = useCallback(() => {
    setShowSetup(false);
  }, []);

  const startPractice = useCallback(
    (newScenario: PracticeScenario) => {
      setScenario(newScenario);
      setIsActive(true);
      setShowSetup(false);
      setMessages([]);
      setFeedback(null);
      onPracticeStart?.(newScenario);

      // Add initial character message
      const initialMessage: PracticeMessage = {
        id: `practice-${Date.now()}`,
        role: "sage-character",
        content: getInitialMessage(newScenario),
        timestamp: new Date().toISOString(),
      };
      setMessages([initialMessage]);
    },
    [onPracticeStart]
  );

  const endPractice = useCallback(() => {
    if (!scenario) return;

    // Generate feedback based on practice messages
    const generatedFeedback: PracticeFeedbackData = {
      scenario,
      positives: generatePositives(messages),
      improvements: generateImprovements(messages),
      summary: generateSummary(scenario, messages),
    };

    setFeedback(generatedFeedback);
    setIsActive(false);
    setShowFeedback(true);
    onPracticeEnd?.(generatedFeedback);
  }, [scenario, messages, onPracticeEnd]);

  const requestHint = useCallback(() => {
    if (!isActive) return;

    const hintMessage: PracticeMessage = {
      id: `hint-${Date.now()}`,
      role: "sage-hint",
      content: getHintForScenario(scenario),
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, hintMessage]);
    onHintRequest?.();
  }, [isActive, scenario, onHintRequest]);

  const addMessage = useCallback(
    (role: PracticeMessage["role"], content: string) => {
      const message: PracticeMessage = {
        id: `msg-${Date.now()}`,
        role,
        content,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, message]);
    },
    []
  );

  const closeFeedback = useCallback(() => {
    setShowFeedback(false);
    setScenario(null);
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
    scenario,
    messages,
    showSetup,
    showFeedback,
    feedback,
    openSetup,
    closeSetup,
    startPractice,
    endPractice,
    requestHint,
    addMessage,
    closeFeedback,
    practiceAgain,
  };
}

// Helper functions for generating practice content
function getInitialMessage(scenario: PracticeScenario): string {
  const messages: Record<string, string> = {
    "pricing-call":
      "Hi! I've looked at your portfolio and I really like your work. I'm interested in hiring you for a project, but I need to discuss the budget. What are your rates?",
    negotiation:
      "Thanks for meeting with me today. I've reviewed the proposal and while I see the value, I think we need to discuss some of the terms before moving forward.",
    presentation:
      "Thank you for that presentation. I have a few questions. Can you explain how this solution would scale as our company grows?",
    interview:
      "Thanks for coming in today. Before we dive into your experience, tell me a bit about yourself and why you're interested in this role.",
  };
  return (
    messages[scenario.id] ||
    `Hello! I'm playing the role of ${scenario.sageRole}. Let's begin our practice session.`
  );
}

function getHintForScenario(scenario: PracticeScenario | null): string {
  if (!scenario) return "Take a moment to think about your response.";

  const hints: Record<string, string[]> = {
    "pricing-call": [
      "Remember to focus on value, not just cost.",
      "Ask questions to understand their needs before discussing price.",
      "Don't be afraid to anchor high—you can always negotiate down.",
    ],
    negotiation: [
      "Look for win-win solutions rather than zero-sum outcomes.",
      "Ask clarifying questions before making concessions.",
      "Consider what you can offer that costs you little but has value to them.",
    ],
    presentation: [
      "Answer the question directly, then provide supporting details.",
      "It's okay to say 'That's a great question' to buy thinking time.",
      "Use specific examples or data to support your points.",
    ],
    interview: [
      "Use the STAR method: Situation, Task, Action, Result.",
      "Connect your experience to what they need.",
      "Show enthusiasm without overselling.",
    ],
  };

  const scenarioHints = hints[scenario.id] || [
    "Take your time and think through your response.",
  ];
  return scenarioHints[Math.floor(Math.random() * scenarioHints.length)];
}

function generatePositives(messages: PracticeMessage[]): string[] {
  const userMessages = messages.filter((m) => m.role === "user");
  if (userMessages.length === 0) return ["You started the practice session!"];

  // Simple analysis based on message content
  const positives: string[] = [];
  const allContent = userMessages.map((m) => m.content.toLowerCase()).join(" ");

  if (allContent.includes("value") || allContent.includes("benefit")) {
    positives.push("You focused on value rather than just features");
  }
  if (allContent.includes("?")) {
    positives.push("You asked questions to understand their perspective");
  }
  if (userMessages.length >= 2) {
    positives.push("You engaged in a back-and-forth dialogue");
  }
  if (allContent.length > 100) {
    positives.push("You provided detailed, thoughtful responses");
  }

  return positives.length > 0
    ? positives
    : ["You completed the practice session"];
}

function generateImprovements(messages: PracticeMessage[]): string[] {
  const userMessages = messages.filter((m) => m.role === "user");
  if (userMessages.length === 0)
    return ["Try responding to build your confidence"];

  const improvements: string[] = [];
  const allContent = userMessages.map((m) => m.content.toLowerCase()).join(" ");

  if (!allContent.includes("?")) {
    improvements.push("Try asking more questions to understand their needs");
  }
  if (userMessages.some((m) => m.content.length < 20)) {
    improvements.push("Expand on your responses with more detail or examples");
  }
  if (userMessages.length < 3) {
    improvements.push("Practice longer conversations to build stamina");
  }

  return improvements;
}

function generateSummary(
  scenario: PracticeScenario,
  messages: PracticeMessage[]
): string {
  const userMessages = messages.filter((m) => m.role === "user");
  const responseCount = userMessages.length;

  if (responseCount === 0) {
    return `Ready to try the ${scenario.title.toLowerCase()} scenario? The best way to improve is through practice.`;
  }

  if (responseCount < 3) {
    return `Good start with the ${scenario.title.toLowerCase()}! With more practice, you'll feel more confident handling these situations.`;
  }

  return `Nice work on the ${scenario.title.toLowerCase()} practice! You're building the skills to handle these situations with confidence.`;
}
