"use client";

import { useState, useCallback } from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";
import { Loader2, AlertCircle, RefreshCw, Download, ZoomIn, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export interface GeneratedImageProps {
  prompt: string;
  className?: string;
  autoGenerate?: boolean;
}

interface ImageData {
  url: string;
  revised_prompt?: string;
}

export function GeneratedImage({
  prompt,
  className,
  autoGenerate = true,
}: GeneratedImageProps): JSX.Element {
  const [isLoading, setIsLoading] = useState(autoGenerate);
  const [error, setError] = useState<string | null>(null);
  const [imageData, setImageData] = useState<ImageData | null>(null);
  const [showFullscreen, setShowFullscreen] = useState(false);
  const [hasGenerated, setHasGenerated] = useState(false);

  const generateImage = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/generate-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || "Failed to generate image");
      }

      if (data.images && data.images.length > 0) {
        setImageData(data.images[0]);
        setHasGenerated(true);
      } else {
        throw new Error("No image generated");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate image");
    } finally {
      setIsLoading(false);
    }
  }, [prompt]);

  // Auto-generate on mount if enabled
  useState(() => {
    if (autoGenerate && !hasGenerated) {
      generateImage();
    }
  });

  const handleDownload = useCallback(async () => {
    if (!imageData?.url) return;

    try {
      const response = await fetch(imageData.url);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sage-illustration-${Date.now()}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download failed:", err);
    }
  }, [imageData]);

  // Loading state
  if (isLoading) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center p-8 rounded-xl",
          "bg-gradient-to-br from-sage-50 to-slate-50 dark:from-sage-900/20 dark:to-slate-800/50",
          "border border-sage-200 dark:border-sage-800",
          "min-h-[200px]",
          className
        )}
      >
        <div className="relative">
          <div className="absolute inset-0 bg-sage-500/20 rounded-full animate-ping" />
          <Loader2 className="w-8 h-8 text-sage-500 animate-spin relative" />
        </div>
        <p className="mt-4 text-sm text-slate-600 dark:text-slate-400">
          Creating illustration...
        </p>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-500 max-w-xs text-center">
          {prompt.length > 50 ? `${prompt.slice(0, 50)}...` : prompt}
        </p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className={cn(
          "flex flex-col items-center gap-4 p-6 rounded-xl",
          "bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800",
          className
        )}
      >
        <div className="flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-500" />
          <span className="text-sm font-medium text-red-700 dark:text-red-400">
            Image Generation Failed
          </span>
        </div>
        <p className="text-xs text-red-600 dark:text-red-500 text-center">
          {error}
        </p>
        <button
          onClick={generateImage}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg text-sm",
            "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400",
            "hover:bg-red-200 dark:hover:bg-red-800/50 transition-colors"
          )}
        >
          <RefreshCw className="w-4 h-4" />
          Try Again
        </button>
      </div>
    );
  }

  // No image yet (autoGenerate disabled)
  if (!imageData) {
    return (
      <div
        className={cn(
          "flex flex-col items-center gap-4 p-6 rounded-xl",
          "bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700",
          className
        )}
      >
        <p className="text-sm text-slate-600 dark:text-slate-400 text-center">
          {prompt}
        </p>
        <button
          onClick={generateImage}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium",
            "bg-sage-500 text-white",
            "hover:bg-sage-600 transition-colors"
          )}
        >
          Generate Illustration
        </button>
      </div>
    );
  }

  // Image display
  return (
    <>
      <div
        className={cn(
          "group relative overflow-hidden rounded-xl",
          "bg-white dark:bg-slate-800",
          "border border-slate-200 dark:border-slate-700",
          "shadow-sm hover:shadow-md transition-shadow",
          className
        )}
      >
        <div className="relative aspect-square w-full max-w-md mx-auto">
          <Image
            src={imageData.url}
            alt={imageData.revised_prompt || prompt}
            fill
            className="object-contain"
            sizes="(max-width: 768px) 100vw, 400px"
          />
        </div>

        {/* Overlay actions */}
        <div
          className={cn(
            "absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100",
            "flex items-center justify-center gap-3 transition-opacity"
          )}
        >
          <button
            onClick={() => setShowFullscreen(true)}
            className="p-3 rounded-full bg-white/20 hover:bg-white/30 transition-colors"
            title="View fullscreen"
          >
            <ZoomIn className="w-5 h-5 text-white" />
          </button>
          <button
            onClick={handleDownload}
            className="p-3 rounded-full bg-white/20 hover:bg-white/30 transition-colors"
            title="Download"
          >
            <Download className="w-5 h-5 text-white" />
          </button>
          <button
            onClick={generateImage}
            className="p-3 rounded-full bg-white/20 hover:bg-white/30 transition-colors"
            title="Regenerate"
          >
            <RefreshCw className="w-5 h-5 text-white" />
          </button>
        </div>

        {/* Caption */}
        {imageData.revised_prompt && (
          <div className="p-3 border-t border-slate-200 dark:border-slate-700">
            <p className="text-xs text-slate-500 dark:text-slate-400 italic">
              {imageData.revised_prompt}
            </p>
          </div>
        )}
      </div>

      {/* Fullscreen modal */}
      <AnimatePresence>
        {showFullscreen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4"
            onClick={() => setShowFullscreen(false)}
          >
            <button
              className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
              onClick={() => setShowFullscreen(false)}
            >
              <X className="w-6 h-6 text-white" />
            </button>
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="relative max-w-4xl max-h-[90vh] w-full h-full"
              onClick={(e) => e.stopPropagation()}
            >
              <Image
                src={imageData.url}
                alt={imageData.revised_prompt || prompt}
                fill
                className="object-contain"
                sizes="100vw"
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
