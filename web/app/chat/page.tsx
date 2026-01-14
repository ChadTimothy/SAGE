"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { AnimatePresence } from "framer-motion";
import { Wifi, WifiOff, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { useChat } from "@/hooks/useChat";
import {
  MessageBubble,
  ChatInput,
  StreamingIndicator,
  EmptyState,
} from "@/components/chat";
import { CheckInModal } from "@/components/sidebar";
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
  const [isListening, setIsListening] = useState(false);
  const [showCheckIn, setShowCheckIn] = useState(true);
  const [sessionContext, setSessionContext] = useState<SessionContext | null>(null);

  const { messages, status, isTyping, sendMessage, isConnected } = useChat({
    sessionId,
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

  const handleVoiceStart = useCallback(() => {
    setIsListening(true);
  }, []);

  const handleVoiceEnd = useCallback(() => {
    setIsListening(false);
  }, []);

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
        <div className={cn("flex items-center gap-2 text-sm", statusDisplay.className)}>
          {statusDisplay.icon}
          <span>{statusDisplay.text}</span>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 && !isTyping ? (
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

      <ChatInput
        onSend={handleSend}
        onVoiceStart={handleVoiceStart}
        onVoiceEnd={handleVoiceEnd}
        isListening={isListening}
        disabled={!isConnected}
        placeholder={
          isConnected
            ? "Type a message..."
            : "Connecting to SAGE..."
        }
      />
    </div>
  );
}
