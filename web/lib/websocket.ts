/**
 * SAGE WebSocket Client for streaming chat
 */

import type { WSMessage, WSCompleteMessage } from "@/types";

type CompleteHandler = (message: WSCompleteMessage) => void;
type ChunkHandler = (content: string) => void;
type ErrorHandler = (message: string) => void;
type StatusHandler = (status: "connecting" | "connected" | "disconnected" | "error") => void;

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export class ChatWebSocket {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private completeHandlers: Set<CompleteHandler> = new Set();
  private chunkHandlers: Set<ChunkHandler> = new Set();
  private errorHandlers: Set<ErrorHandler> = new Set();
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

        switch (message.type) {
          case "chunk":
            // Notify chunk handlers for streaming indicator
            this.chunkHandlers.forEach((handler) => handler(message.content));
            break;

          case "complete":
            // Notify complete handlers with the full response
            this.completeHandlers.forEach((handler) => handler(message));
            break;

          case "error":
            // Notify error handlers
            this.errorHandlers.forEach((handler) => handler(message.message));
            break;

          default:
            console.warn("Unknown message type:", message);
        }
      } catch {
        console.error("Failed to parse WebSocket message:", event.data);
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

  /** Subscribe to complete messages (full SAGE responses) */
  onComplete(handler: CompleteHandler): () => void {
    this.completeHandlers.add(handler);
    return () => this.completeHandlers.delete(handler);
  }

  /** Subscribe to streaming chunks (for typing indicator) */
  onChunk(handler: ChunkHandler): () => void {
    this.chunkHandlers.add(handler);
    return () => this.chunkHandlers.delete(handler);
  }

  /** Subscribe to error messages */
  onError(handler: ErrorHandler): () => void {
    this.errorHandlers.add(handler);
    return () => this.errorHandlers.delete(handler);
  }

  /** Subscribe to connection status changes */
  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
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
