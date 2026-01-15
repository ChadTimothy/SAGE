/**
 * UI Renderer TypeScript Types
 *
 * Core types for the composable UI rendering system.
 * Re-exports UITreeNode from main types for convenience.
 */

import type { UITreeNode } from "@/types";

// Re-export for convenience
export type { UITreeNode };

/**
 * Action dispatched when a user interacts with UI components.
 */
export interface UIAction {
  /** Action identifier (e.g., 'submit', 'select', 'click') */
  name: string;
  /** Data associated with the action */
  data: Record<string, unknown>;
}

/**
 * Form data state shared across input components.
 */
export type FormData = Record<string, unknown>;

/**
 * Function type for updating form data.
 */
export type SetFormData = (
  updater: FormData | ((prev: FormData) => FormData)
) => void;

/**
 * Props passed to all primitive components.
 */
export interface PrimitiveProps {
  /** Handler for user actions */
  onAction: (action: UIAction) => void;
  /** Current form data state */
  formData: FormData;
  /** Function to update form data */
  setFormData: SetFormData;
  /** Children (for container components) */
  children?: React.ReactNode;
}

/**
 * A primitive component in the registry.
 */
export type PrimitiveComponent<P = Record<string, unknown>> = React.ComponentType<
  P & PrimitiveProps
>;

/**
 * Registry mapping component names to implementations.
 */
export type PrimitiveRegistry = Record<string, PrimitiveComponent<any>>;

/**
 * Props for the core UIRenderer component.
 */
export interface UIRendererProps {
  /** The component tree to render */
  tree: UITreeNode;
  /** Handler for user actions */
  onAction: (action: UIAction) => void;
  /** Current form data state */
  formData: FormData;
  /** Function to update form data */
  setFormData: SetFormData;
}

/**
 * Props for the UITreeForm wrapper component.
 */
export interface UITreeFormProps {
  /** The component tree to render */
  tree: UITreeNode;
  /** Callback when form is submitted */
  onSubmit: (data: FormData) => void;
  /** Optional initial form data */
  initialData?: FormData;
  /** Optional form ID for tracking */
  formId?: string;
}
