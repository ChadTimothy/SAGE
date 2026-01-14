"use client";

import { motion } from "framer-motion";
import { Network, ZoomIn, ZoomOut, RefreshCw } from "lucide-react";

export default function GraphPage(): React.ReactElement {
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
            Knowledge Graph
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Visualize your learning journey
          </p>
        </div>
        <div className="flex gap-2">
          <button className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
            <ZoomIn className="h-5 w-5 text-slate-600 dark:text-slate-400" />
          </button>
          <button className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
            <ZoomOut className="h-5 w-5 text-slate-600 dark:text-slate-400" />
          </button>
          <button className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
            <RefreshCw className="h-5 w-5 text-slate-600 dark:text-slate-400" />
          </button>
        </div>
      </header>

      {/* Graph area */}
      <div className="flex-1 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <Network className="h-16 w-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
          <h2 className="text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">
            No knowledge graph yet
          </h2>
          <p className="text-slate-500 dark:text-slate-400 max-w-md">
            Start learning through conversation, and your knowledge graph will
            grow as you prove understanding of new concepts.
          </p>
        </motion.div>
      </div>
    </div>
  );
}
