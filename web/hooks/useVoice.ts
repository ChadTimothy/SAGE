"use client";

import { useState, useCallback, useEffect, useRef } from "react";

export type VoiceStatus = "idle" | "listening" | "processing" | "speaking" | "error";

export interface UseVoiceOptions {
  onTranscript?: (text: string, isFinal: boolean) => void;
  onError?: (error: string) => void;
  continuous?: boolean;
  language?: string;
}

export interface UseVoiceReturn {
  status: VoiceStatus;
  isListening: boolean;
  isSpeaking: boolean;
  transcript: string;
  interimTranscript: string;
  error: string | null;
  isSupported: boolean;
  startListening: () => void;
  stopListening: () => void;
  speak: (text: string) => void;
  stopSpeaking: () => void;
  audioLevel: number;
}

// Check if Web Speech API is supported
function getSpeechRecognition(): typeof SpeechRecognition | null {
  if (typeof window === "undefined") return null;
  return (
    (window as unknown as { SpeechRecognition?: typeof SpeechRecognition }).SpeechRecognition ||
    (window as unknown as { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition ||
    null
  );
}

export function useVoice({
  onTranscript,
  onError,
  continuous = false,
  language = "en-US",
}: UseVoiceOptions = {}): UseVoiceReturn {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const SpeechRecognitionAPI = getSpeechRecognition();
  const isSupported = SpeechRecognitionAPI !== null && typeof window !== "undefined";

  // Audio level analysis for waveform visualization
  const startAudioAnalysis = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      audioContextRef.current = new AudioContext();
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;

      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);

      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);

      const updateLevel = () => {
        if (!analyserRef.current) return;

        analyserRef.current.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
        setAudioLevel(average / 255);

        animationFrameRef.current = requestAnimationFrame(updateLevel);
      };

      updateLevel();
    } catch {
      // Silently fail - audio analysis is optional
      console.warn("Could not start audio analysis");
    }
  }, []);

  const stopAudioAnalysis = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setAudioLevel(0);
  }, []);

  // Start speech recognition
  const startListening = useCallback(() => {
    if (!SpeechRecognitionAPI) {
      setError("Speech recognition not supported in this browser");
      onError?.("Speech recognition not supported");
      return;
    }

    setError(null);
    setTranscript("");
    setInterimTranscript("");

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = continuous;
    recognition.interimResults = true;
    recognition.lang = language;

    recognition.onstart = () => {
      setStatus("listening");
      startAudioAnalysis();
    };

    recognition.onresult = (event) => {
      let finalTranscript = "";
      let interim = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }

      if (finalTranscript) {
        setTranscript((prev) => prev + finalTranscript);
        onTranscript?.(finalTranscript, true);
      }
      setInterimTranscript(interim);
      if (interim) {
        onTranscript?.(interim, false);
      }
    };

    recognition.onerror = (event) => {
      const errorMessage = event.error === "no-speech"
        ? "No speech detected"
        : `Speech recognition error: ${event.error}`;
      setError(errorMessage);
      setStatus("error");
      onError?.(errorMessage);
      stopAudioAnalysis();
    };

    recognition.onend = () => {
      if (status !== "error") {
        setStatus("idle");
      }
      stopAudioAnalysis();
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [SpeechRecognitionAPI, continuous, language, onTranscript, onError, startAudioAnalysis, stopAudioAnalysis, status]);

  // Stop speech recognition
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setStatus("idle");
    setInterimTranscript("");
    stopAudioAnalysis();
  }, [stopAudioAnalysis]);

  // Text-to-speech
  const speak = useCallback((text: string) => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      console.warn("Speech synthesis not supported");
      return;
    }

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    // Try to find a good voice
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(
      (v) => v.lang.startsWith("en") && v.name.includes("Google") || v.name.includes("Samantha")
    ) || voices.find((v) => v.lang.startsWith("en"));

    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }

    utterance.onstart = () => setStatus("speaking");
    utterance.onend = () => setStatus("idle");
    utterance.onerror = () => setStatus("idle");

    window.speechSynthesis.speak(utterance);
  }, []);

  // Stop text-to-speech
  const stopSpeaking = useCallback(() => {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setStatus("idle");
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopListening();
      stopSpeaking();
    };
  }, [stopListening, stopSpeaking]);

  return {
    status,
    isListening: status === "listening",
    isSpeaking: status === "speaking",
    transcript,
    interimTranscript,
    error,
    isSupported,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
    audioLevel,
  };
}
