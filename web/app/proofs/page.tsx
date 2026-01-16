"use client";

import { Award, FileCheck, Star, History } from "lucide-react";
import { StubPage } from "@/components/ui/StubPage";

const features = [
  { icon: Award, label: "View earned proofs" },
  { icon: FileCheck, label: "Review proof details" },
  { icon: Star, label: "Track proof confidence" },
  { icon: History, label: "See verification history" },
];

export default function ProofsPage(): JSX.Element {
  return (
    <StubPage
      title="Proofs"
      subtitle="Your demonstrated understanding"
      icon={Award}
      features={features}
    />
  );
}
