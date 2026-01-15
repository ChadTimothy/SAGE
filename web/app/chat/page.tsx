"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { AnimatePresence } from "framer-motion";
import { Wifi, WifiOff, RefreshCw, Theater } from "lucide-react";
import { cn } from "@/lib/utils";
import { useChat } from "@/hooks/useChat";
import { useGrokVoice } from "@/hooks/useGrokVoice";
import { usePracticeMode } from "@/hooks/usePracticeMode";
import {
  MessageBubble,
  ChatInput,
  StreamingIndicator,
  EmptyState,
} from "@/components/chat";
import { CheckInModal } from "@/components/sidebar";
import { VoiceOutputToggle, VoiceSelector } from "@/components/voice";
import {
  PracticeModeContainer,
  PracticeScenarioSetup,
  PracticeFeedback,
  PracticeMessageBubble,
} from "@/components/practice";
import type { SessionContext } from "@/types";

type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

interface StatusDisplay {
  icon: React.ReactNode;
  text: string;
  className: string;
}

const STATUS_CONFIG: Record<ConnectionStatus, StatusDisplay> = {
  connecting: {
    icon: <RefreshCw className="h-4 w-4 animate-spin" />,
    text: "Connecting...",
    className: "text-yellow-600 dark:text-yellow-400",
  },
  connected: {
    icon: <Wifi className="h-4 w-4" />,
    text: "Connected",
    className: "text-green-600 dark:text-green-400",
  },
  error: {
    icon: <WifiOff className="h-4 w-4" />,
    text: "Connection error",
    className: "text-red-600 dark:text-red-400",
  },
  disconnected: {
    icon: <WifiOff className="h-4 w-4" />,
    text: "Disconnected",
    className: "text-slate-500 dark:text-slate-400",
  },
};

function generateSessionId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

export default function ChatPage(): JSX.Element {
  const [sessionId] = useState(generateSessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showCheckIn, setShowCheckIn] = useState(true);
  const [sessionContext, setSessionContext] = useState<SessionContext | null>(null);
  const [voiceOutputEnabled, setVoiceOutputEnabled] = useState(false);
  const lastVoicedMessageIdRef = useRef<string | null>(null);

  const { messages, status, isTyping, sendMessage, isConnected } = useChat({
    sessionId,
  });

  const practice = usePracticeMode({
    onPracticeStart: (scenario) => {
      console.log("Practice started:", scenario.title);
    },
    onPracticeEnd: (feedback) => {
      console.log("Practice ended with feedback:", feedback);
    },
  });

  const {
    status: voiceStatus,
    isConnected: voiceConnected,
    isListening,
    isSpeaking,
    transcript,
    audioLevel,
    connect: connectVoice,
    disconnect: disconnectVoice,
    startListening,
    stopListening,
    sendText: sendVoiceText,
    setVoice,
    currentVoice,
    error: voiceError,
  } = useGrokVoice({
    sessionId,
    onTranscript: (text, isFinal) => {
      if (isFinal && text.trim()) {
        sendMessage(text.trim(), true);
      }
    },
    onResponse: (text) => {
      // Response text is streamed from Grok voice
      console.log("Grok voice response:", text);
    },
    onError: (error) => {
      console.error("Grok voice error:", error);
    },
  });

  const handleCheckInComplete = useCallback((context: SessionContext) => {
    setSessionContext(context);
    setShowCheckIn(false);
  }, []);

  const statusDisplay = STATUS_CONFIG[status];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = useCallback(
    (content: string) => {
      sendMessage(content, isListening);
    },
    [sendMessage, isListening]
  );

  const handleSuggestionClick = useCallback(
    (suggestion: string) => {
      sendMessage(suggestion, false);
    },
    [sendMessage]
  );

  // Practice mode handlers
  const handlePracticeSend = useCallback(
    (content: string) => {
      practice.sendMessage(content);
    },
    [practice]
  );

  const handleVoiceStart = useCallback(async () => {
    if (!voiceConnected) {
      await connectVoice();
    }
    startListening();
  }, [voiceConnected, connectVoice, startListening]);

  const handleVoiceEnd = useCallback(() => {
    stopListening();
  }, [stopListening]);

  const handleVoiceOutputToggle = useCallback(async () => {
    const newEnabled = !voiceOutputEnabled;
    setVoiceOutputEnabled(newEnabled);

    // Connect to Grok Voice when enabling voice output
    if (newEnabled && !voiceConnected) {
      await connectVoice();
    }
  }, [voiceOutputEnabled, voiceConnected, connectVoice]);

  // Generate a stable ID for messages to track which have been voiced
  const lastAssistantMessageId = useMemo(() => {
    if (messages.length === 0) return null;
    const lastMessage = messages[messages.length - 1];
    if (lastMessage.role !== "assistant" || !lastMessage.content) return null;
    return `${messages.length}-${lastMessage.timestamp ?? "pending"}`;
  }, [messages]);

  // Send assistant messages through Grok Voice when voice output is enabled
  useEffect(() => {
    if (!voiceOutputEnabled || !voiceConnected || messages.length === 0) return;
    if (!lastAssistantMessageId) return;

    // Prevent duplicate sends by tracking already-voiced messages
    if (lastVoicedMessageIdRef.current === lastAssistantMessageId) return;

    const lastMessage = messages[messages.length - 1];
    if (lastMessage.role === "assistant" && lastMessage.content) {
      lastVoicedMessageIdRef.current = lastAssistantMessageId;
      sendVoiceText(lastMessage.content);
    }
  }, [messages, voiceOutputEnabled, voiceConnected, sendVoiceText, lastAssistantMessageId]);

  return (
    <div className="flex flex-col h-full">
      <CheckInModal
        isOpen={showCheckIn && !sessionContext}
        onClose={() => setShowCheckIn(false)}
        onComplete={handleCheckInComplete}
      />

      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
            Chat with SAGE
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Tell me what you want to learn
          </p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={practice.openSetup}
            disabled={practice.isActive}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm",
              "bg-amber-100 dark:bg-amber-900/30",
              "text-amber-700 dark:text-amber-300",
              "hover:bg-amber-200 dark:hover:bg-amber-800/50",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "transition-colors"
            )}
          >
            <Theater className="w-4 h-4" />
            <span className="hidden sm:inline">Practice</span>
          </button>
          <VoiceSelector
            value={currentVoice}
            onChange={setVoice}
            disabled={isSpeaking}
          />
          <VoiceOutputToggle
            enabled={voiceOutputEnabled}
            onToggle={handleVoiceOutputToggle}
            disabled={voiceStatus === "connecting"}
          />
          <div className={cn("flex items-center gap-2 text-sm", statusDisplay.className)}>
            {statusDisplay.icon}
            <span>{statusDisplay.text}</span>
          </div>
        </div>
      </header>

      <PracticeModeContainer
        isActive={practice.isActive}
        scenario={practice.scenario}
        onEnd={practice.endPractice}
        onHint={practice.requestHint}
      >
        <div className="flex-1 overflow-y-auto">
          {practice.isActive ? (
            // Practice mode messages
            <div className="p-6 space-y-4 max-w-4xl mx-auto">
              <AnimatePresence mode="popLayout">
                {practice.messages.map((message) => (
                  <PracticeMessageBubble
                    key={message.id}
                    role={message.role}
                    characterName={practice.scenario?.sageRole}
                    content={message.content}
                    timestamp={message.timestamp}
                  />
                ))}
              </AnimatePresence>
              <div ref={messagesEndRef} />
            </div>
          ) : messages.length === 0 && !isTyping ? (
            <EmptyState onSuggestionClick={handleSuggestionClick} />
          ) : (
            <div className="p-6 space-y-4 max-w-4xl mx-auto">
              <AnimatePresence mode="popLayout">
                {messages.map((message, index) => (
                  <MessageBubble
                    key={`msg-${index}-${message.timestamp ?? "pending"}`}
                    role={message.role}
                    content={message.content}
                    timestamp={message.timestamp || new Date().toISOString()}
                    mode={message.mode}
                  />
                ))}
              </AnimatePresence>

              <AnimatePresence>
                {isTyping && <StreamingIndicator key="streaming" />}
              </AnimatePresence>

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </PracticeModeContainer>

      <ChatInput
        onSend={practice.isActive ? handlePracticeSend : handleSend}
        onVoiceStart={handleVoiceStart}
        onVoiceEnd={handleVoiceEnd}
        isListening={isListening}
        disabled={practice.isActive ? false : !isConnected}
        placeholder={getPlaceholderText(practice.isActive, isConnected)}
        audioLevel={audioLevel}
        interimTranscript={transcript}
      />

      {/* Practice Mode Modals */}
      <PracticeScenarioSetup
        isOpen={practice.showSetup}
        onClose={practice.closeSetup}
        onStart={practice.startPractice}
      />

      <PracticeFeedback
        isOpen={practice.showFeedback}
        feedback={practice.feedback}
        onClose={practice.closeFeedback}
        onPracticeAgain={practice.practiceAgain}
        onBackToLearning={practice.closeFeedback}
      />
    </div>
  );
}

function getPlaceholderText(isPracticeActive: boolean, isConnected: boolean): string {
  if (isPracticeActive) {
    return "Respond to the scenario...";
  }
  if (isConnected) {
    return "Type a message...";
  }
  return "Connecting to SAGE...";
}

