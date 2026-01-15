"use client";

/**
 * UITreeForm - Form state wrapper for UI trees
 *
 * Manages form data state across all input components and handles
 * form submission with action detection.
 */

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { UIRenderer } from "./Renderer";
import { containerVariants } from "./animations";
import type { UITreeFormProps, UIAction, FormData } from "./types";

/**
 * Wrapper component that manages form state for UI trees.
 *
 * Provides:
 * - Shared form data state across all input components
 * - Action handling with automatic submit detection
 * - Animated mount/unmount transitions
 */
export function UITreeForm({
  tree,
  onSubmit,
  initialData = {},
  formId,
}: UITreeFormProps): React.ReactElement {
  const [formData, setFormData] = useState<FormData>(initialData);

  const handleAction = useCallback(
    (action: UIAction) => {
      // Submit actions trigger form submission
      if (action.name === "submit" || action.name.startsWith("submit_")) {
        onSubmit({
          ...formData,
          ...action.data,
          _action: action.name,
          _formId: formId,
        });
        return;
      }

      // Other actions just propagate their data
      if (action.data && Object.keys(action.data).length > 0) {
        setFormData((prev) => ({ ...prev, ...action.data }));
      }
    },
    [formData, onSubmit, formId]
  );

  const handleSetFormData = useCallback(
    (updater: FormData | ((prev: FormData) => FormData)) => {
      if (typeof updater === "function") {
        setFormData(updater);
      } else {
        setFormData((prev) => ({ ...prev, ...updater }));
      }
    },
    []
  );

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={formId || "ui-tree-form"}
        className="ui-tree-form"
        variants={containerVariants}
        initial="initial"
        animate="animate"
        exit="exit"
      >
        <UIRenderer
          tree={tree}
          onAction={handleAction}
          formData={formData}
          setFormData={handleSetFormData}
        />
      </motion.div>
    </AnimatePresence>
  );
}
