"use client";

/**
 * Core UI Renderer
 *
 * Recursively renders component trees using primitive components.
 * Handles form state, actions, and graceful fallbacks for unknown components.
 */

import { primitiveRegistry } from "./primitives";
import type { UIRendererProps, UITreeNode, UIAction, FormData, SetFormData } from "./types";

/**
 * Recursively render a UI component tree.
 *
 * @param tree - The component tree node to render
 * @param onAction - Handler for user actions
 * @param formData - Current form data state
 * @param setFormData - Function to update form data
 */
export function UIRenderer({
  tree,
  onAction,
  formData,
  setFormData,
}: UIRendererProps): React.ReactElement | null {
  const Component = primitiveRegistry[tree.component];

  if (!Component) {
    console.warn(`UIRenderer: Unknown component "${tree.component}"`);
    return null;
  }

  // Recursively render children
  const childElements = tree.children?.map((child, index) => (
    <UIRenderer
      key={`${child.component}-${index}`}
      tree={child}
      onAction={onAction}
      formData={formData}
      setFormData={setFormData}
    />
  ));

  return (
    <Component
      {...tree.props}
      onAction={onAction}
      formData={formData}
      setFormData={setFormData}
    >
      {childElements}
    </Component>
  );
}

/**
 * Render a UI tree with default no-op handlers.
 * Useful for read-only rendering without form state.
 */
export function UIRendererStatic({
  tree,
}: {
  tree: UITreeNode;
}): React.ReactElement | null {
  const noopAction = () => {};
  const noopSetFormData = () => {};

  return (
    <UIRenderer
      tree={tree}
      onAction={noopAction}
      formData={{}}
      setFormData={noopSetFormData}
    />
  );
}
