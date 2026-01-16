"use client";

/**
 * useGrokVoice - Voice interaction hook with Grok API
 *
 * Updated for #85 - Voice Error Recovery & Graceful Degradation
 * - Reconnection with exponential backoff
 * - Voice timeout detection
 * - Browser support detection
 * - Enhanced error handling
 */

import { useState, useCallback, useRef, useEffect } from "react";
import type { VoiceErrorType, VoiceError } from "@/components/voice/VoiceErrorToast";
import { getAuthToken } from "@/lib/auth";

export type GrokVoice = "ara" | "rex" | "sal" | "eve" | "leo";
export type VoiceStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "listening"
  | "speaking"
  | "reconnecting"
  | "error"
  | "fallback";

export interface UseGrokVoiceOptions {
  sessionId: string;
  voice?: GrokVoice;
  onTranscript?: (text: string, isFinal: boolean) => void;
  onResponse?: (text: string) => void;
  onError?: (error: VoiceError) => void;
  onFallback?: () => void;
  /** Max reconnection attempts (default: 3) */
  maxReconnectAttempts?: number;
  /** Voice timeout in ms (default: 10000) */
  voiceTimeoutMs?: number;
}

export interface UseGrokVoiceReturn {
  status: VoiceStatus;
  isConnected: boolean;
  isListening: boolean;
  isSpeaking: boolean;
  transcript: string;
  audioLevel: number;
  connect: () => Promise<void>;
  disconnect: () => void;
  startListening: () => void;
  stopListening: () => void;
  sendText: (text: string) => void;
  setVoice: (voice: GrokVoice) => void;
  currentVoice: GrokVoice;
  error: VoiceError | null;
  isSupported: boolean;
  isFallbackMode: boolean;
  clearError: () => void;
  retry: () => Promise<void>;
}

// Configuration
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const getVoiceUrl = (sessionId: string, token?: string | null) => {
  let url = `${WS_BASE}/api/voice/${sessionId}`;
  if (token) {
    url += `?token=${encodeURIComponent(token)}`;
  }
  return url;
};
const DEFAULT_MAX_RECONNECT_ATTEMPTS = 3;
const DEFAULT_VOICE_TIMEOUT_MS = 10000;
const BASE_RECONNECT_DELAY_MS = 1000;

/**
 * Check if the browser supports voice features.
 */
function checkBrowserSupport(): { supported: boolean; reason?: string } {
  if (typeof window === "undefined") {
    return { supported: false, reason: "Server-side rendering" };
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    return { supported: false, reason: "getUserMedia not supported" };
  }

  if (!window.WebSocket) {
    return { supported: false, reason: "WebSocket not supported" };
  }

  if (!window.AudioContext && !(window as unknown as { webkitAudioContext?: unknown }).webkitAudioContext) {
    return { supported: false, reason: "AudioContext not supported" };
  }

  return { supported: true };
}

/**
 * Create a VoiceError from various error sources.
 */
function createVoiceError(
  error: unknown,
  defaultType: VoiceErrorType = "unknown"
): VoiceError {
  if (error instanceof DOMException) {
    if (error.name === "NotAllowedError") {
      return {
        type: "mic_denied",
        message: "Microphone access was denied. Please enable it in your browser settings.",
        recoverable: true,
      };
    }
    if (error.name === "NotFoundError") {
      return {
        type: "mic_not_found",
        message: "No microphone found. Please connect a microphone and try again.",
        recoverable: true,
      };
    }
  }

  const message = error instanceof Error ? error.message : String(error);

  return {
    type: defaultType,
    message,
    recoverable: defaultType !== "browser_unsupported",
  };
}

export function useGrokVoice({
  sessionId,
  voice: initialVoice = "ara",
  onTranscript,
  onResponse,
  onError,
  onFallback,
  maxReconnectAttempts = DEFAULT_MAX_RECONNECT_ATTEMPTS,
  voiceTimeoutMs = DEFAULT_VOICE_TIMEOUT_MS,
}: UseGrokVoiceOptions): UseGrokVoiceReturn {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<VoiceError | null>(null);
  const [currentVoice, setCurrentVoice] = useState<GrokVoice>(initialVoice);
  const [audioLevel, setAudioLevel] = useState(0);
  const [isFallbackMode, setIsFallbackMode] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const voiceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastSpeechTimeRef = useRef<number>(0);

  // Check browser support (memoized to avoid recalculation)
  const browserSupport = useRef(checkBrowserSupport()).current;
  const isSupported = browserSupport.supported;

  // Set error and notify callback
  const handleError = useCallback(
    (voiceError: VoiceError) => {
      setError(voiceError);
      setStatus("error");
      onError?.(voiceError);
    },
    [onError]
  );

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
    if (status === "error") {
      setStatus("idle");
    }
  }, [status]);

  // Enter fallback mode
  const enterFallbackMode = useCallback(() => {
    setIsFallbackMode(true);
    setStatus("fallback");
    onFallback?.();
  }, [onFallback]);

  // Clear voice timeout
  const clearVoiceTimeout = useCallback(() => {
    if (voiceTimeoutRef.current) {
      clearTimeout(voiceTimeoutRef.current);
      voiceTimeoutRef.current = null;
    }
  }, []);

  // Reset voice timeout - uses statusRef to avoid stale closure
  const statusRef = useRef(status);
  statusRef.current = status;

  const resetVoiceTimeout = useCallback(() => {
    clearVoiceTimeout();
    lastSpeechTimeRef.current = Date.now();
    voiceTimeoutRef.current = setTimeout(() => {
      if (statusRef.current === "listening") {
        handleError({
          type: "timeout",
          message: "No speech detected. Type your message instead.",
          recoverable: true,
        });
      }
    }, voiceTimeoutMs);
  }, [clearVoiceTimeout, handleError, voiceTimeoutMs]);

  // Play received audio
  const playAudio = useCallback((base64Audio: string) => {
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext({ sampleRate: 24000 });
      }

      const audioContext = audioContextRef.current;
      const binaryString = atob(base64Audio);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      const pcm16 = new Int16Array(bytes.buffer);
      const float32 = new Float32Array(pcm16.length);
      for (let i = 0; i < pcm16.length; i++) {
        float32[i] = pcm16[i] / 32768;
      }

      const audioBuffer = audioContext.createBuffer(1, float32.length, 24000);
      audioBuffer.getChannelData(0).set(float32);

      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);
      source.start();
    } catch (err) {
      console.error("Failed to play audio:", err);
    }
  }, []);

  // Handle incoming messages from backend/Grok
  const handleServerMessage = useCallback(
    (message: Record<string, unknown>) => {
      switch (message.type) {
        case "session.ready":
          setStatus("connected");
          reconnectAttemptsRef.current = 0;
          break;

        case "session.created":
        case "session.updated":
          console.log("Session configured:", message);
          break;

        case "input_audio_buffer.speech_started":
          setStatus("listening");
          clearVoiceTimeout();
          break;

        case "input_audio_buffer.speech_stopped":
          setStatus("connected");
          break;

        case "conversation.item.input_audio_transcription.completed": {
          const inputTranscript =
            (message as { transcript?: string }).transcript || "";
          setTranscript(inputTranscript);
          onTranscript?.(inputTranscript, true);
          break;
        }

        case "response.audio_transcript.delta": {
          const delta = (message as { delta?: string }).delta || "";
          onResponse?.(delta);
          break;
        }

        case "response.audio.delta": {
          const audioData = (message as { delta?: string }).delta;
          if (audioData) {
            playAudio(audioData);
            setStatus("speaking");
          }
          break;
        }

        case "response.audio.done":
          setStatus("connected");
          break;

        case "error": {
          const errorMsg =
            (message as { error?: { message?: string } }).error?.message ||
            "Voice service error";
          handleError({
            type: "api_error",
            message: errorMsg,
            recoverable: true,
          });
          break;
        }
      }
    },
    [onTranscript, onResponse, playAudio, handleError, clearVoiceTimeout]
  );

  // Schedule reconnection with exponential backoff
  const scheduleReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      handleError({
        type: "connection_error",
        message: "Voice connection failed after multiple attempts.",
        recoverable: false,
      });
      enterFallbackMode();
      return;
    }

    const delay =
      BASE_RECONNECT_DELAY_MS * Math.pow(2, reconnectAttemptsRef.current);
    reconnectAttemptsRef.current++;

    setStatus("reconnecting");

    reconnectTimeoutRef.current = setTimeout(() => {
      connectInternal();
    }, delay);
  }, [maxReconnectAttempts, handleError, enterFallbackMode]);

  // Internal connect function
  const connectInternal = useCallback(async () => {
    if (!sessionId) {
      handleError({
        type: "unknown",
        message: "Session ID is required for voice",
        recoverable: false,
      });
      return;
    }

    if (!isSupported) {
      handleError({
        type: "browser_unsupported",
        message:
          browserSupport.reason ||
          "Voice features are not supported in this browser.",
        recoverable: false,
      });
      enterFallbackMode();
      return;
    }

    try {
      setStatus("connecting");
      clearError();

      // Get auth token for WebSocket connection
      const token = await getAuthToken();
      const ws = new WebSocket(getVoiceUrl(sessionId, token));

      ws.onopen = () => {
        ws.send(JSON.stringify({ voice: currentVoice }));
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleServerMessage(message);
        } catch {
          console.error("Failed to parse message:", event.data);
        }
      };

      ws.onerror = () => {
        // onerror is always followed by onclose, handle there
      };

      ws.onclose = (event) => {
        wsRef.current = null;

        const wasActive =
          status === "connected" ||
          status === "listening" ||
          status === "speaking";
        const wasConnecting =
          status === "connecting" || status === "reconnecting";
        const canRetry = reconnectAttemptsRef.current < maxReconnectAttempts;

        // Try to reconnect if connection dropped unexpectedly or initial connect failed
        if (canRetry && ((wasActive && !event.wasClean) || wasConnecting)) {
          scheduleReconnect();
          return;
        }

        // Max reconnects reached while trying to connect
        if (wasConnecting && !canRetry) {
          handleError({
            type: "connection_error",
            message: "Unable to connect to voice service.",
            recoverable: true,
          });
          return;
        }

        setStatus("idle");
      };

      wsRef.current = ws;
    } catch (err) {
      handleError(createVoiceError(err, "connection_error"));
    }
  }, [
    sessionId,
    currentVoice,
    isSupported,
    browserSupport.reason,
    handleServerMessage,
    handleError,
    clearError,
    enterFallbackMode,
    scheduleReconnect,
    status,
    maxReconnectAttempts,
  ]);

  // Public connect function (also used for retry)
  const connect = useCallback(async () => {
    clearError();
    reconnectAttemptsRef.current = 0;
    setIsFallbackMode(false);
    await connectInternal();
  }, [clearError, connectInternal]);

  // Start listening (capture microphone)
  const startListening = useCallback(async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      handleError({
        type: "connection_error",
        message: "Voice connection not ready. Please try reconnecting.",
        recoverable: true,
      });
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const audioContext = new AudioContext({ sampleRate: 24000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      // Start voice timeout
      resetVoiceTimeout();

      processor.onaudioprocess = (event) => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) return;

        const inputData = event.inputBuffer.getChannelData(0);

        // Calculate audio level (RMS)
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);
        const level = Math.min(1, rms * 5);
        setAudioLevel(level);

        // Detect speech activity for timeout reset
        if (level > 0.05) {
          lastSpeechTimeRef.current = Date.now();
          clearVoiceTimeout();
        } else if (
          Date.now() - lastSpeechTimeRef.current > 2000 &&
          !voiceTimeoutRef.current
        ) {
          // Start timeout if no speech for 2 seconds
          resetVoiceTimeout();
        }

        // Convert Float32 to PCM16
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          pcm16[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
        }

        // Convert to base64
        const bytes = new Uint8Array(pcm16.buffer);
        let binary = "";
        for (let i = 0; i < bytes.length; i++) {
          binary += String.fromCharCode(bytes[i]);
        }
        const base64 = btoa(binary);

        // Send audio to Grok
        wsRef.current.send(
          JSON.stringify({
            type: "input_audio_buffer.append",
            audio: base64,
          })
        );
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setStatus("listening");
    } catch (err) {
      handleError(createVoiceError(err, "mic_denied"));
    }
  }, [handleError, resetVoiceTimeout, clearVoiceTimeout]);

  // Stop listening
  const stopListening = useCallback(() => {
    clearVoiceTimeout();

    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "input_audio_buffer.commit",
        })
      );
    }

    setAudioLevel(0);
    setStatus("connected");
  }, [clearVoiceTimeout]);

  // Send text message
  const sendText = useCallback((text: string) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      console.error("WebSocket not connected");
      return;
    }

    wsRef.current.send(
      JSON.stringify({
        type: "conversation.item.create",
        item: {
          type: "message",
          role: "user",
          content: [{ type: "input_text", text }],
        },
      })
    );

    wsRef.current.send(
      JSON.stringify({
        type: "response.create",
      })
    );
  }, []);

  // Disconnect
  const disconnect = useCallback(() => {
    clearVoiceTimeout();

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    stopListening();

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    reconnectAttemptsRef.current = 0;
    setStatus("idle");
  }, [stopListening, clearVoiceTimeout]);

  // Update voice
  const setVoice = useCallback((voice: GrokVoice) => {
    setCurrentVoice(voice);

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "session.update",
          session: { voice },
        })
      );
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Set fallback mode on mount if browser unsupported
  useEffect(() => {
    if (!isSupported) {
      setError({
        type: "browser_unsupported",
        message:
          browserSupport.reason ||
          "Voice features are not supported in this browser.",
        recoverable: false,
      });
      setIsFallbackMode(true);
    }
  }, []);

  const isConnected =
    status === "connected" ||
    status === "listening" ||
    status === "speaking";

  return {
    status,
    isConnected,
    isListening: status === "listening",
    isSpeaking: status === "speaking",
    transcript,
    audioLevel,
    connect,
    disconnect,
    startListening,
    stopListening,
    sendText,
    setVoice,
    currentVoice,
    error,
    isSupported,
    isFallbackMode,
    clearError,
    retry: connect,
  };
}
