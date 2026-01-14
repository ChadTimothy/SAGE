"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { createChatConnection, type ChatWebSocket } from "@/lib/websocket";
import type { ChatMessage, WSMessage } from "@/types";

interface UseChatOptions {
  sessionId: string;
  onMessage?: (message: ChatMessage) => void;
}

type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

export function useChat({ sessionId, onMessage }: UseChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [isTyping, setIsTyping] = useState(false);
  const wsRef = useRef<ChatWebSocket | null>(null);
  const onMessageRef = useRef(onMessage);

  // Keep onMessage ref in sync
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  // Connect to WebSocket
  useEffect(() => {
    if (!sessionId) return;

    const ws = createChatConnection(sessionId);
    wsRef.current = ws;

    // Handle incoming messages
    const unsubMessage = ws.onMessage((wsMessage: WSMessage) => {
      const chatMessage: ChatMessage = {
        role: wsMessage.type === "user" ? "user" : "assistant",
        content: wsMessage.content,
        timestamp: wsMessage.timestamp || new Date().toISOString(),
        mode: wsMessage.mode,
      };

      setMessages((prev) => [...prev, chatMessage]);
      setIsTyping(false);
      onMessageRef.current?.(chatMessage);
    });

    // Handle status changes
    const unsubStatus = ws.onStatus((newStatus) => {
      setStatus(newStatus);
    });

    // Connect
    ws.connect();

    // Cleanup
    return () => {
      unsubMessage();
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

  return {
    messages,
    status,
    isTyping,
    sendMessage,
    clearMessages,
    isConnected: status === "connected",
  };
}
