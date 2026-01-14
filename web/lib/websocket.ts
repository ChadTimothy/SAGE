/**
 * SAGE WebSocket Client for streaming chat
 */

import type { WSMessage } from "@/types";

type MessageHandler = (message: WSMessage) => void;
type StatusHandler = (status: "connecting" | "connected" | "disconnected" | "error") => void;

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export class ChatWebSocket {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private messageHandlers: Set<MessageHandler> = new Set();
  private statusHandlers: Set<StatusHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.notifyStatus("connecting");
    const url = `${WS_BASE}/api/chat/${this.sessionId}`;

    try {
      this.ws = new WebSocket(url);
      this.setupHandlers();
    } catch (error) {
      console.error("WebSocket connection error:", error);
      this.notifyStatus("error");
      this.scheduleReconnect();
    }
  }

  private setupHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.notifyStatus("connected");
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        this.notifyMessage(message);
      } catch {
        // Handle plain text messages
        this.notifyMessage({
          type: "assistant",
          content: event.data,
        });
      }
    };

    this.ws.onclose = () => {
      this.notifyStatus("disconnected");
      this.scheduleReconnect();
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      this.notifyStatus("error");
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("Max reconnection attempts reached");
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    setTimeout(() => {
      console.log(`Reconnection attempt ${this.reconnectAttempts}...`);
      this.connect();
    }, delay);
  }

  send(content: string, isVoice: boolean = false): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket is not connected");
    }

    const message = JSON.stringify({
      content,
      is_voice: isVoice,
    });

    this.ws.send(message);
  }

  disconnect(): void {
    this.maxReconnectAttempts = 0; // Prevent reconnection
    this.ws?.close();
    this.ws = null;
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  private notifyMessage(message: WSMessage): void {
    this.messageHandlers.forEach((handler) => handler(message));
  }

  private notifyStatus(status: "connecting" | "connected" | "disconnected" | "error"): void {
    this.statusHandlers.forEach((handler) => handler(status));
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Factory function for creating chat connections
export function createChatConnection(sessionId: string): ChatWebSocket {
  return new ChatWebSocket(sessionId);
}
