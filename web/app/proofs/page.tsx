"use client";

import { Award, FileCheck, Star, History } from "lucide-react";

export default function ProofsPage(): JSX.Element {
  const plannedFeatures = [
    { icon: Award, label: "View earned proofs" },
    { icon: FileCheck, label: "Review proof details" },
    { icon: Star, label: "Track proof confidence" },
    { icon: History, label: "See verification history" },
  ];

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
            Proofs
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Your demonstrated understanding
          </p>
        </div>
      </header>

      <div className="flex-1 flex items-center justify-center">
        <div className="text-center max-w-md">
          <Award className="h-16 w-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
          <h2 className="text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">
            Coming Soon
          </h2>
          <p className="text-slate-500 dark:text-slate-400 mb-6">
            Proofs page is under development. Planned features include:
          </p>
          <ul className="space-y-3">
            {plannedFeatures.map(({ icon: Icon, label }) => (
              <li
                key={label}
                className="flex items-center gap-3 text-slate-600 dark:text-slate-400"
              >
                <Icon className="h-5 w-5 text-sage-500" />
                <span>{label}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
