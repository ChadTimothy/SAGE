"use client";

import { Settings, Moon, Mic, Key, User } from "lucide-react";
import { StubPage } from "@/components/ui/StubPage";

const features = [
  { icon: Moon, label: "Dark mode toggle" },
  { icon: Mic, label: "Voice preferences" },
  { icon: Key, label: "API configuration" },
  { icon: User, label: "Learner profile" },
];

export default function SettingsPage(): JSX.Element {
  return (
    <StubPage
      title="Settings"
      subtitle="Customize your SAGE experience"
      icon={Settings}
      features={features}
    />
  );
}
