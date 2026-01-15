"use client";

/**
 * Markdown Primitive - Rich text rendering
 *
 * Wraps the existing MarkdownContent component for use in UI trees.
 */

import { MarkdownContent } from "@/components/chat/MarkdownContent";
import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface MarkdownProps extends PrimitiveProps {
  /** Markdown content to render */
  content: string;
  /** Additional CSS classes */
  className?: string;
}

export function Markdown({
  content,
  className,
}: MarkdownProps): React.ReactElement {
  return (
    <MarkdownContent
      content={content}
      className={cn("text-sm", className)}
    />
  );
}
