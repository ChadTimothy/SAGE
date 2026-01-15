"use client";

import { useState, useCallback, useRef, useEffect } from "react";

export type GrokVoice = "ara" | "rex" | "sal" | "eve" | "leo";
export type VoiceStatus = "idle" | "connecting" | "connected" | "listening" | "speaking" | "error";

export interface UseGrokVoiceOptions {
  sessionId: string;
  voice?: GrokVoice;
  onTranscript?: (text: string, isFinal: boolean) => void;
  onResponse?: (text: string) => void;
  onError?: (error: string) => void;
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
  error: string | null;
}

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const getVoiceUrl = (sessionId: string) => `${WS_BASE}/api/voice/${sessionId}`;

export function useGrokVoice({
  sessionId,
  voice: initialVoice = "ara",
  onTranscript,
  onResponse,
  onError,
}: UseGrokVoiceOptions): UseGrokVoiceReturn {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [currentVoice, setCurrentVoice] = useState<GrokVoice>(initialVoice);
  const [audioLevel, setAudioLevel] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);

  // Connect to voice backend proxy
  const connect = useCallback(async () => {
    if (!sessionId) {
      const err = "Session ID is required for voice";
      setError(err);
      onError?.(err);
      return;
    }

    try {
      setStatus("connecting");
      setError(null);

      // Connect to backend voice proxy (API key stays on server)
      const ws = new WebSocket(getVoiceUrl(sessionId));

      ws.onopen = () => {
        // Send initial voice preference (backend handles session config and auth)
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
        const err = "WebSocket connection error";
        setError(err);
        setStatus("error");
        onError?.(err);
      };

      ws.onclose = () => {
        setStatus("idle");
        wsRef.current = null;
      };

      wsRef.current = ws;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Connection failed";
      setError(errorMsg);
      setStatus("error");
      onError?.(errorMsg);
    }
  }, [sessionId, currentVoice, onError]);

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

      // Convert PCM16 to Float32
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
  const handleServerMessage = useCallback((message: Record<string, unknown>) => {
    switch (message.type) {
      case "session.ready":
        // Backend connected to Grok successfully
        setStatus("connected");
        break;

      case "session.created":
      case "session.updated":
        console.log("Session configured:", message);
        break;

      case "input_audio_buffer.speech_started":
        setStatus("listening");
        break;

      case "input_audio_buffer.speech_stopped":
        setStatus("connected");
        break;

      case "conversation.item.input_audio_transcription.completed": {
        const inputTranscript = (message as { transcript?: string }).transcript || "";
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
        const errorMsg = (message as { error?: { message?: string } }).error?.message || "Unknown error";
        setError(errorMsg);
        onError?.(errorMsg);
        break;
      }
    }
  }, [onTranscript, onResponse, onError, playAudio]);

  // Start listening (capture microphone)
  const startListening = useCallback(async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error("WebSocket not connected");
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

      processor.onaudioprocess = (event) => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) return;

        const inputData = event.inputBuffer.getChannelData(0);

        // Calculate audio level (RMS)
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);
        const level = Math.min(1, rms * 5); // Scale and clamp
        setAudioLevel(level);

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
        wsRef.current.send(JSON.stringify({
          type: "input_audio_buffer.append",
          audio: base64,
        }));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setStatus("listening");
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Microphone access failed";
      setError(errorMsg);
      onError?.(errorMsg);
    }
  }, [onError]);

  // Stop listening
  const stopListening = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "input_audio_buffer.commit",
      }));
    }

    setStatus("connected");
  }, []);

  // Send text message
  const sendText = useCallback((text: string) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      console.error("WebSocket not connected");
      return;
    }

    wsRef.current.send(JSON.stringify({
      type: "conversation.item.create",
      item: {
        type: "message",
        role: "user",
        content: [{ type: "input_text", text }],
      },
    }));

    wsRef.current.send(JSON.stringify({
      type: "response.create",
    }));
  }, []);

  // Disconnect
  const disconnect = useCallback(() => {
    stopListening();

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    setStatus("idle");
  }, [stopListening]);

  // Update voice
  const setVoice = useCallback((voice: GrokVoice) => {
    setCurrentVoice(voice);

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "session.update",
        session: { voice },
      }));
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    status,
    isConnected: status === "connected" || status === "listening" || status === "speaking",
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
  };
}
