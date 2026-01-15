"use client";

import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import DOMPurify from "dompurify";
import { cn } from "@/lib/utils";
import { AlertCircle, Loader2 } from "lucide-react";

export interface MermaidDiagramProps {
  chart: string;
  className?: string;
}

// Custom SAGE theme for light mode
const lightThemeVariables = {
  primaryColor: "#22c55e",        // sage-500
  primaryTextColor: "#ffffff",
  primaryBorderColor: "#16a34a",  // sage-600
  secondaryColor: "#f0fdf4",      // sage-50
  secondaryTextColor: "#166534",  // sage-800
  secondaryBorderColor: "#bbf7d0", // sage-200
  tertiaryColor: "#f8fafc",       // slate-50
  tertiaryTextColor: "#334155",   // slate-700
  tertiaryBorderColor: "#e2e8f0", // slate-200
  lineColor: "#64748b",           // slate-500
  textColor: "#1e293b",           // slate-800
  mainBkg: "#ffffff",
  nodeBorder: "#16a34a",
  clusterBkg: "#f0fdf4",
  titleColor: "#166534",
  edgeLabelBackground: "#ffffff",
  nodeTextColor: "#1e293b",
};

// Custom SAGE theme for dark mode
const darkThemeVariables = {
  primaryColor: "#16a34a",        // sage-600
  primaryTextColor: "#ffffff",
  primaryBorderColor: "#22c55e",  // sage-500
  secondaryColor: "#14532d",      // sage-900
  secondaryTextColor: "#bbf7d0",  // sage-200
  secondaryBorderColor: "#166534", // sage-800
  tertiaryColor: "#1e293b",       // slate-800
  tertiaryTextColor: "#e2e8f0",   // slate-200
  tertiaryBorderColor: "#334155", // slate-700
  lineColor: "#94a3b8",           // slate-400
  textColor: "#f1f5f9",           // slate-100
  mainBkg: "#0f172a",             // slate-900
  nodeBorder: "#22c55e",
  clusterBkg: "#14532d",
  titleColor: "#86efac",          // sage-300
  edgeLabelBackground: "#1e293b",
  nodeTextColor: "#f1f5f9",
};

let diagramId = 0;

export function MermaidDiagram({ chart, className }: MermaidDiagramProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const idRef = useRef(`mermaid-${++diagramId}`);

  useEffect(() => {
    const renderDiagram = async () => {
      if (!chart.trim()) {
        setError("Empty diagram");
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError(null);

        // Detect dark mode
        const isDark = document.documentElement.classList.contains("dark");

        // Initialize mermaid with SAGE theme
        mermaid.initialize({
          startOnLoad: false,
          theme: "base",
          themeVariables: isDark ? darkThemeVariables : lightThemeVariables,
          fontFamily: "Inter, system-ui, sans-serif",
          flowchart: {
            htmlLabels: true,
            curve: "basis",
            padding: 15,
            nodeSpacing: 50,
            rankSpacing: 50,
            useMaxWidth: true,
          },
          sequence: {
            diagramMarginX: 20,
            diagramMarginY: 20,
            actorMargin: 50,
            width: 150,
            height: 65,
            boxMargin: 10,
            boxTextMargin: 5,
            noteMargin: 10,
            messageMargin: 35,
            mirrorActors: true,
            useMaxWidth: true,
          },
          mindmap: {
            useMaxWidth: true,
            padding: 10,
          },
          securityLevel: "strict",
        });

        // Render the diagram
        const { svg: renderedSvg } = await mermaid.render(idRef.current, chart);

        // Sanitize the SVG output for security
        const sanitizedSvg = DOMPurify.sanitize(renderedSvg, {
          USE_PROFILES: { svg: true, svgFilters: true },
          ADD_TAGS: ["foreignObject"],
        });

        setSvg(sanitizedSvg);
      } catch (err) {
        console.error("Mermaid render error:", err);
        setError(err instanceof Error ? err.message : "Failed to render diagram");
      } finally {
        setIsLoading(false);
      }
    };

    renderDiagram();
  }, [chart]);

  // Re-render on theme change
  useEffect(() => {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === "class") {
          // Theme changed, increment ID to force re-render
          idRef.current = `mermaid-${++diagramId}`;
          setSvg(""); // Clear to trigger re-render
        }
      });
    });

    observer.observe(document.documentElement, { attributes: true });
    return () => observer.disconnect();
  }, [chart]);

  if (isLoading) {
    return (
      <div
        className={cn(
          "flex items-center justify-center p-8 rounded-xl",
          "bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700",
          className
        )}
      >
        <Loader2 className="w-6 h-6 text-sage-500 animate-spin" />
        <span className="ml-2 text-sm text-slate-500 dark:text-slate-400">
          Rendering diagram...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={cn(
          "flex items-center gap-3 p-4 rounded-xl",
          "bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800",
          className
        )}
      >
        <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
        <div>
          <p className="text-sm font-medium text-red-700 dark:text-red-400">
            Diagram Error
          </p>
          <p className="text-xs text-red-600 dark:text-red-500 mt-0.5">
            {error}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn(
        "mermaid-container overflow-x-auto p-4 rounded-xl",
        "bg-white dark:bg-slate-800/50",
        "border border-slate-200 dark:border-slate-700",
        "shadow-sm",
        className
      )}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
