"use client";

/**
 * VoiceStatusAnnouncer - Screen reader announcements for voice status
 *
 * Part of #87 - Accessibility for Voice/UI Parity
 *
 * This component provides ARIA live regions to announce voice status
 * changes to screen reader users.
 */

import type { VoiceStatus } from "@/hooks/useGrokVoice";
import { useVoiceStatusAnnouncement } from "@/hooks/useAccessibility";

export interface VoiceStatusAnnouncerProps {
  status: VoiceStatus;
  isSupported: boolean;
  isFallbackMode?: boolean;
}

export function VoiceStatusAnnouncer({
  status,
  isSupported,
  isFallbackMode = false,
}: VoiceStatusAnnouncerProps): JSX.Element {
  useVoiceStatusAnnouncement(status);

  return (
    <>
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
