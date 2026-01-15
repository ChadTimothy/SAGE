"use client";

import { Children, isValidElement } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeHighlight from "rehype-highlight";
import { cn } from "@/lib/utils";
import { MermaidDiagram } from "./MermaidDiagram";
import { GeneratedImage } from "./GeneratedImage";

import "katex/dist/katex.min.css";

export interface MarkdownContentProps {
  content: string;
  className?: string;
}

// Extract text content from React children
function getTextContent(children: React.ReactNode): string {
  let text = "";
  Children.forEach(children, (child) => {
    if (typeof child === "string") {
      text += child;
    } else if (isValidElement(child) && child.props.children) {
      text += getTextContent(child.props.children);
    }
  });
  return text;
}

export function MarkdownContent({
  content,
  className,
}: MarkdownContentProps): JSX.Element {
  return (
    <div className={cn("prose prose-sm dark:prose-invert max-w-none", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex, rehypeHighlight]}
        components={{
          pre: ({ children }) => {
            // Check for special code blocks
            const child = Children.only(children);
            if (isValidElement(child)) {
              const langClass = child.props.className || "";

              // Mermaid diagrams
              if (langClass.includes("language-mermaid")) {
                const chart = getTextContent(child.props.children);
                return <MermaidDiagram chart={chart} className="my-4 not-prose" />;
              }

              // AI-generated illustrations
              if (langClass.includes("language-illustration")) {
                const prompt = getTextContent(child.props.children).trim();
                return <GeneratedImage prompt={prompt} className="my-4 not-prose" />;
              }
            }

            return (
              <pre className="bg-slate-900 dark:bg-slate-950 rounded-lg p-4 overflow-x-auto text-sm">
                {children}
              </pre>
            );
          },
          code: ({ className: codeClassName, children }) => {
            // Inline code (no language class)
            if (!codeClassName) {
              return (
                <code className="bg-slate-200 dark:bg-slate-700 px-1.5 py-0.5 rounded text-sm font-mono">
                  {children}
                </code>
              );
            }
            // Code block with language class - let pre handle mermaid, others get default styling
            return <code className={codeClassName}>{children}</code>;
          },
          a: ({ href, children }) => (
            <a
              href={href}
              className="text-sage-600 dark:text-sage-400 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto">
              <table className="border-collapse border border-slate-300 dark:border-slate-600">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-slate-300 dark:border-slate-600 px-3 py-2 bg-slate-100 dark:bg-slate-800">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-slate-300 dark:border-slate-600 px-3 py-2">
              {children}
            </td>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-sage-500 pl-4 italic text-slate-600 dark:text-slate-400">
              {children}
            </blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
