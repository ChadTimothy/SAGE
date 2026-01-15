/**
 * SAGE WebSocket Client for streaming chat
 *
 * Supports:
 * - Text messages (chat)
 * - Form submissions (UI parity)
 * - Voice messages
 */

import type { WSMessage, WSCompleteMessage } from "@/types";

type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";
type CompleteHandler = (message: WSCompleteMessage) => void;
type ChunkHandler = (content: string) => void;
type ErrorHandler = (message: string) => void;
type StatusHandler = (status: ConnectionStatus) => void;

/**
 * Outgoing message types for WebSocket communication.
 */
interface WSOutgoingTextMessage {
  type: "text";
  content: string;
  is_voice: boolean;
}

interface WSOutgoingFormMessage {
  type: "form_submission";
  form_id: string;
  data: Record<string, unknown>;
}

type WSOutgoingMessage = WSOutgoingTextMessage | WSOutgoingFormMessage;

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
        this.handleMessage(message);
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

  private handleMessage(message: WSMessage): void {
    switch (message.type) {
      case "chunk":
        this.chunkHandlers.forEach((handler) => handler(message.content));
        break;
      case "complete":
        this.completeHandlers.forEach((handler) => handler(message));
        break;
      case "error":
        this.errorHandlers.forEach((handler) => handler(message.message));
        break;
      default:
        console.warn("Unknown message type:", message);
    }
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

  /**
   * Send a text message (chat or voice transcription).
   */
  send(content: string, isVoice: boolean = false): void {
    this.sendMessage({
      type: "text",
      content,
      is_voice: isVoice,
    });
  }

  /**
   * Send a form submission from UI components.
   *
   * @param formId - Identifier for the form type (e.g., "check-in-abc123")
   * @param data - Form field values
   */
  sendFormSubmission(formId: string, data: Record<string, unknown>): void {
    this.sendMessage({
      type: "form_submission",
      form_id: formId,
      data,
    });
  }

  /**
   * Internal method to send any message type.
   */
  private sendMessage(message: WSOutgoingMessage): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket is not connected");
    }
    this.ws.send(JSON.stringify(message));
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

  private notifyStatus(status: ConnectionStatus): void {
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
