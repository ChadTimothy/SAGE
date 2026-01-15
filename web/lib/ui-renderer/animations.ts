/**
 * Shared Animation Variants for UI Renderer
 *
 * Consistent framer-motion animations for all rendered UI components.
 */

import type { Variants } from "framer-motion";

/**
 * Container animation - used for wrapping entire UI trees.
 */
export const containerVariants: Variants = {
  initial: { opacity: 0, y: 10 },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3,
      ease: "easeOut",
    },
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: {
      duration: 0.2,
      ease: "easeIn",
    },
  },
};

/**
 * Item animation - used for list items and child elements.
 */
export const itemVariants: Variants = {
  initial: { opacity: 0, x: -10 },
  animate: {
    opacity: 1,
    x: 0,
    transition: {
      duration: 0.2,
      ease: "easeOut",
    },
  },
  exit: {
    opacity: 0,
    x: 10,
    transition: {
      duration: 0.15,
      ease: "easeIn",
    },
  },
};

/**
 * Stagger children animation - for lists of items.
 */
export const staggerVariants: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.05,
    },
  },
};

/**
 * Scale animation - used for buttons and interactive elements.
 */
export const scaleVariants: Variants = {
  initial: { scale: 0.95, opacity: 0 },
  animate: {
    scale: 1,
    opacity: 1,
    transition: {
      duration: 0.2,
      ease: "easeOut",
    },
  },
  exit: {
    scale: 0.95,
    opacity: 0,
    transition: {
      duration: 0.15,
    },
  },
};

/**
 * Fade animation - simple opacity transition.
 */
export const fadeVariants: Variants = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: {
      duration: 0.2,
    },
  },
  exit: {
    opacity: 0,
    transition: {
      duration: 0.15,
    },
  },
};

/**
 * Card animation - used for Card components.
 */
export const cardVariants: Variants = {
  initial: { opacity: 0, y: 5, scale: 0.98 },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.25,
      ease: "easeOut",
    },
  },
  exit: {
    opacity: 0,
    y: -5,
    scale: 0.98,
    transition: {
      duration: 0.2,
    },
  },
};

/**
 * Input focus animation - for input fields gaining focus.
 */
export const inputFocusVariants: Variants = {
  initial: { scale: 1 },
  focus: {
    scale: 1.01,
    transition: {
      duration: 0.15,
    },
  },
};

/**
 * Preset transition configurations.
 */
export const transitions = {
  /** Fast transition for micro-interactions */
  fast: { duration: 0.15, ease: "easeOut" },
  /** Default transition for most animations */
  default: { duration: 0.25, ease: "easeOut" },
  /** Slower transition for larger elements */
  slow: { duration: 0.35, ease: "easeOut" },
  /** Spring transition for playful interactions */
  spring: { type: "spring", stiffness: 300, damping: 25 },
} as const;
