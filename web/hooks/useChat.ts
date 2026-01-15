"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { createChatConnection, type ChatWebSocket } from "@/lib/websocket";
import type { ChatMessage, DialogueMode, WSCompleteMessage } from "@/types";

interface UseChatOptions {
  sessionId: string;
  onMessage?: (message: ChatMessage) => void;
  onError?: (error: string) => void;
}

type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

export function useChat({ sessionId, onMessage, onError }: UseChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [isTyping, setIsTyping] = useState(false);
  const wsRef = useRef<ChatWebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  const onErrorRef = useRef(onError);

  // Keep refs in sync
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  // Connect to WebSocket
  useEffect(() => {
    if (!sessionId) return;

    const ws = createChatConnection(sessionId);
    wsRef.current = ws;

    // Handle complete messages (full SAGE responses)
    const unsubComplete = ws.onComplete((wsMessage: WSCompleteMessage) => {
      const response = wsMessage.response;

      const chatMessage: ChatMessage = {
        role: "assistant",
        content: response.message,
        timestamp: new Date().toISOString(),
        mode: response.mode as DialogueMode,
        ui_tree: response.ui_tree ?? undefined,
        pending_data_request: response.pending_data_request ?? undefined,
      };

      setMessages((prev) => [...prev, chatMessage]);
      setIsTyping(false);
      onMessageRef.current?.(chatMessage);
    });

    // Handle streaming chunks (for typing indicator)
    const unsubChunk = ws.onChunk(() => {
      // Each chunk confirms SAGE is still responding
      setIsTyping(true);
    });

    // Handle errors
    const unsubError = ws.onError((errorMessage: string) => {
      console.error("Chat error:", errorMessage);
      setIsTyping(false);
      onErrorRef.current?.(errorMessage);
    });

    // Handle status changes
    const unsubStatus = ws.onStatus((newStatus) => {
      setStatus(newStatus);
    });

    // Connect
    ws.connect();

    // Cleanup
    return () => {
      unsubComplete();
      unsubChunk();
      unsubError();
      unsubStatus();
      ws.disconnect();
    };
  }, [sessionId]);

  // Send message
  const sendMessage = useCallback(
    (content: string, isVoice: boolean = false) => {
      if (!wsRef.current?.isConnected) {
        console.error("Not connected to chat");
        return;
      }

      // Add user message immediately
      const userMessage: ChatMessage = {
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsTyping(true);

      // Send to server
      wsRef.current.send(content, isVoice);
    },
    []
  );

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  // Send form submission from UI components
  const sendFormSubmission = useCallback(
    (formId: string, data: Record<string, unknown>) => {
      if (!wsRef.current?.isConnected) {
        console.error("Not connected to chat");
        return;
      }

      setIsTyping(true);
      wsRef.current.sendFormSubmission(formId, data);
    },
    []
  );

  return {
    messages,
    status,
    isTyping,
    sendMessage,
    sendFormSubmission,
    clearMessages,
    isConnected: status === "connected",
  };
}
