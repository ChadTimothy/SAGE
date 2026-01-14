"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { MessageSquare, Target, Award, ArrowRight } from "lucide-react";

export default function HomePage(): React.ReactElement {
  return (
    <div className="flex flex-col items-center justify-center min-h-full p-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center max-w-2xl"
      >
        <h1 className="text-4xl font-bold text-slate-900 dark:text-white mb-4">
          Welcome to <span className="text-sage-600">SAGE</span>
        </h1>
        <p className="text-lg text-slate-600 dark:text-slate-400 mb-8">
          Learn through conversation, not curriculum. Tell me what you want to
          be able to DO, and I&apos;ll help you get there.
        </p>

        <Link
          href="/chat"
          className="inline-flex items-center gap-2 px-6 py-3 bg-sage-600 text-white rounded-lg hover:bg-sage-700 transition-colors font-medium"
        >
          Start Learning
          <ArrowRight className="h-5 w-5" />
        </Link>
      </motion.div>

      {/* Feature cards */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.5 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 max-w-4xl"
      >
        <FeatureCard
          icon={<Target className="h-8 w-8 text-sage-600" />}
          title="Outcome-Driven"
          description="Focus on what you want to achieve, not steps to complete"
        />
        <FeatureCard
          icon={<MessageSquare className="h-8 w-8 text-sage-600" />}
          title="Conversational"
          description="Learn through natural dialogue that adapts to you"
        />
        <FeatureCard
          icon={<Award className="h-8 w-8 text-sage-600" />}
          title="Proof-Based"
          description="Demonstrate real understanding before moving on"
        />
      </motion.div>
    </div>
  );
}

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

function FeatureCard({ icon, title, description }: FeatureCardProps): React.ReactElement {
  return (
    <div className="p-6 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
      <div className="mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
        {title}
      </h3>
      <p className="text-slate-600 dark:text-slate-400 text-sm">{description}</p>
    </div>
  );
}
