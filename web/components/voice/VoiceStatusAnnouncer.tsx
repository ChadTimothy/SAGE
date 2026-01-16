"use client";

/**
 * VoiceStatusAnnouncer - Screen reader announcements for voice status
 *
 * Part of #87 - Accessibility for Voice/UI Parity
 *
 * This component provides ARIA live regions to announce voice status
 * changes to screen reader users.
 */

import { useEffect, useRef } from "react";
import type { VoiceStatus } from "@/hooks/useGrokVoice";

export interface VoiceStatusAnnouncerProps {
  status: VoiceStatus;
  isSupported: boolean;
  isFallbackMode?: boolean;
}

const STATUS_MESSAGES: Record<VoiceStatus, string> = {
  idle: "",
  connecting: "Connecting to voice service",
  connected: "Voice service connected",
  listening: "Listening for voice input",
  speaking: "SAGE is speaking",
  error: "Voice error occurred",
};

export function VoiceStatusAnnouncer({
  status,
  isSupported,
  isFallbackMode = false,
}: VoiceStatusAnnouncerProps): JSX.Element {
  const previousStatus = useRef<VoiceStatus>(status);
  const announcerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Only announce when status changes
    if (status === previousStatus.current) return;

    const message = STATUS_MESSAGES[status];
    if (message && announcerRef.current) {
      // Clear and set to trigger announcement
      announcerRef.current.textContent = "";
      setTimeout(() => {
        if (announcerRef.current) {
          announcerRef.current.textContent = message;
        }
      }, 100);
    }

    previousStatus.current = status;
  }, [status]);

  return (
    <>
      {/* Polite announcer for status changes */}
      <div
        ref={announcerRef}
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      />

      {/* Assertive announcer for critical messages */}
      {!isSupported && (
        <div role="alert" className="sr-only">
          Voice features are not supported in this browser. Using text input.
        </div>
      )}

      {isFallbackMode && status === "error" && (
        <div role="alert" className="sr-only">
          Voice is temporarily unavailable. You can continue using text input.
        </div>
      )}
    </>
  );
}

export default VoiceStatusAnnouncer;
