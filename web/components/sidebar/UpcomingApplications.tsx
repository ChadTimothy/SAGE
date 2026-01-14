"use client";

import { CalendarDays, Briefcase } from "lucide-react";
import { formatDate } from "@/lib/utils";
import type { ApplicationSnapshot } from "@/types";

export interface UpcomingApplicationsProps {
  applications: ApplicationSnapshot[];
  collapsed?: boolean;
}

function getRelativeDate(dateStr: string | null): string {
  if (!dateStr) return "Date TBD";

  const date = new Date(dateStr);
  const today = new Date();

  date.setHours(0, 0, 0, 0);
  today.setHours(0, 0, 0, 0);

  const diffDays = Math.round((date.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Tomorrow";
  if (diffDays > 1 && diffDays <= 7) return `In ${diffDays} days`;

  return formatDate(date);
}

function SectionHeader(): JSX.Element {
  return (
    <div className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
      <CalendarDays className="h-4 w-4 text-sage-600" />
      <span>Upcoming</span>
    </div>
  );
}

export function UpcomingApplications({
  applications,
  collapsed,
}: UpcomingApplicationsProps): JSX.Element {
  if (collapsed) {
    return (
      <div className="flex justify-center p-2">
        <CalendarDays className="h-5 w-5 text-sage-600" />
      </div>
    );
  }

  if (applications.length === 0) {
    return (
      <div className="p-4 space-y-3">
        <SectionHeader />
        <p className="text-sm text-slate-500 dark:text-slate-400 italic">
          No upcoming applications scheduled.
        </p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      <SectionHeader />
      <ul className="space-y-2">
        {applications.slice(0, 3).map((app) => (
          <li key={app.id} className="space-y-0.5">
            <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
              {getRelativeDate(app.planned_date)}
            </div>
            <div className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <Briefcase className="h-3 w-3 text-slate-400" />
              <span>{app.context}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
