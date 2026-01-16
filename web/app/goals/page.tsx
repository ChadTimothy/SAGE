"use client";

import { Target, CheckCircle, Circle, Clock } from "lucide-react";
import { StubPage } from "@/components/ui/StubPage";

const features = [
  { icon: Target, label: "View all learning goals" },
  { icon: CheckCircle, label: "Track completed outcomes" },
  { icon: Circle, label: "Monitor active goals" },
  { icon: Clock, label: "See goal history" },
];

export default function GoalsPage(): JSX.Element {
  return (
    <StubPage
      title="Goals"
      subtitle="Track your learning outcomes"
      icon={Target}
      features={features}
    />
  );
}
