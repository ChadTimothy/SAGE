"use client";

/**
 * Image Primitive - Display images with optional caption
 */

import { cn } from "@/lib/utils";
import type { PrimitiveProps } from "../../types";

interface ImageProps extends PrimitiveProps {
  /** Image source URL */
  src: string;
  /** Alt text for accessibility */
  alt: string;
  /** Optional caption */
  caption?: string;
  /** Image size */
  size?: "small" | "medium" | "large" | "full";
  /** Additional CSS classes */
  className?: string;
}

const sizeClasses: Record<string, string> = {
  small: "max-w-xs",
  medium: "max-w-md",
  large: "max-w-lg",
  full: "w-full",
};

export function ImageDisplay({
  src,
  alt,
  caption,
  size = "medium",
  className,
}: ImageProps): React.ReactElement {
  return (
    <figure className={cn("space-y-2", sizeClasses[size], className)}>
      <img
        src={src}
        alt={alt}
        className="rounded-lg shadow-sm w-full h-auto object-cover"
        loading="lazy"
      />
      {caption && (
        <figcaption className="text-xs text-slate-500 dark:text-slate-400 text-center">
          {caption}
        </figcaption>
      )}
    </figure>
  );
}
