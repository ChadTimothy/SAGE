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

// TODO: Replace with backend Assessment module for capability-based evaluation.
// The Assessment module (M5) can analyze actual skill demonstration through
// proofs and verification. This MVP uses pattern-matching as a placeholder.
function generatePositives(messages: PracticeMessage[]): string[] {
  const userMessages = messages.filter((m) => m.role === "user");
  if (userMessages.length === 0) return ["You took the first step by starting practice!"];

  // Analyze for demonstrated communication skills (capability indicators)
  const positives: string[] = [];
  const allContent = userMessages.map((m) => m.content.toLowerCase()).join(" ");

  // Value articulation - key skill in pricing/negotiation
  if (allContent.includes("value") || allContent.includes("benefit") || allContent.includes("roi") || allContent.includes("worth")) {
    positives.push("You articulated value effectively—a key persuasion skill");
  }
  // Active listening - asking clarifying questions
  if ((allContent.match(/\?/g) || []).length >= 2) {
    positives.push("You demonstrated active listening by asking clarifying questions");
  }
  // Confidence indicators - assertive language
  if (allContent.includes("i can") || allContent.includes("i will") || allContent.includes("i believe")) {
    positives.push("You communicated with confidence and conviction");
  }
  // Empathy/rapport - acknowledging the other party
  if (allContent.includes("understand") || allContent.includes("appreciate") || allContent.includes("i see")) {
    positives.push("You showed empathy by acknowledging their perspective");
  }
  // Solution-oriented - proposing alternatives
  if (allContent.includes("what if") || allContent.includes("how about") || allContent.includes("alternatively")) {
    positives.push("You proposed solutions rather than just responding");
  }

  return positives.length > 0
    ? positives
    : ["You practiced the scenario—repetition builds skill"];
}

function generateImprovements(messages: PracticeMessage[]): string[] {
  const userMessages = messages.filter((m) => m.role === "user");
  if (userMessages.length === 0)
    return ["Jump in and respond—practice builds confidence"];

  // Analyze for skill gaps (capability-focused suggestions)
  const improvements: string[] = [];
  const allContent = userMessages.map((m) => m.content.toLowerCase()).join(" ");

  // Missing discovery questions
  if (!(allContent.match(/\?/g) || []).length) {
    improvements.push("Ask discovery questions to understand their real needs");
  }
  // Missing value framing
  if (!allContent.includes("value") && !allContent.includes("benefit") && !allContent.includes("help")) {
    improvements.push("Frame your points in terms of value to the other party");
  }
  // Defensive or apologetic language
  if (allContent.includes("sorry") || allContent.includes("just") || allContent.includes("maybe")) {
    improvements.push("Reduce hedging language—speak with more conviction");
  }
  // Missing acknowledgment
  if (!allContent.includes("understand") && !allContent.includes("hear") && !allContent.includes("appreciate")) {
    improvements.push("Acknowledge their position before presenting yours");
  }

  return improvements;
}

function generateSummary(
  scenario: PracticeScenario,
  messages: PracticeMessage[]
): string {
  const userMessages = messages.filter((m) => m.role === "user");
  const allContent = userMessages.map((m) => m.content.toLowerCase()).join(" ");

  if (userMessages.length === 0) {
    return `Ready to practice ${scenario.title.toLowerCase()}? Skill comes from doing, not just knowing.`;
  }

  // Assess overall capability demonstration
  const hasQuestions = (allContent.match(/\?/g) || []).length > 0;
  const hasValueLanguage = /value|benefit|roi|worth|help/.test(allContent);
  const hasConfidence = /i can|i will|i believe|we can/.test(allContent);
  const skillsShown = [hasQuestions, hasValueLanguage, hasConfidence].filter(Boolean).length;

  if (skillsShown >= 2) {
    return `Strong practice session! You demonstrated key ${scenario.title.toLowerCase()} skills. Keep practicing to make them automatic.`;
  }
  if (skillsShown === 1) {
    return `Good foundation in ${scenario.title.toLowerCase()}. Focus on integrating more techniques in your next practice.`;
  }
  return `You've started building ${scenario.title.toLowerCase()} skills. Each practice session makes the next one easier.`;
}
