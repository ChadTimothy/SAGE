"use client";

import type { LucideIcon } from "lucide-react";

interface PlannedFeature {
  icon: LucideIcon;
  label: string;
}

interface StubPageProps {
  title: string;
  subtitle: string;
  icon: LucideIcon;
  features: PlannedFeature[];
}

export function StubPage({
  title,
  subtitle,
  icon: Icon,
  features,
}: StubPageProps): JSX.Element {
  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
            {title}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {subtitle}
          </p>
        </div>
      </header>

      <div className="flex-1 flex items-center justify-center">
        <div className="text-center max-w-md">
          <Icon className="h-16 w-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
          <h2 className="text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">
            Coming Soon
          </h2>
          <p className="text-slate-500 dark:text-slate-400 mb-6">
            {title} page is under development. Planned features include:
          </p>
          <ul className="space-y-3">
            {features.map(({ icon: FeatureIcon, label }) => (
              <li
                key={label}
                className="flex items-center gap-3 text-slate-600 dark:text-slate-400"
              >
                <FeatureIcon className="h-5 w-5 text-sage-500" />
                <span>{label}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
