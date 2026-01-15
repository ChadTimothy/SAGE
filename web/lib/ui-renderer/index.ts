/**
 * UI Renderer - Composable UI Generation System
 *
 * Renders arbitrary component trees from UITreeNode structures.
 * Enables true ad-hoc UI generation where SAGE can create any UI it needs.
 *
 * @example
 * ```tsx
 * import { UITreeForm } from '@/lib/ui-renderer';
 *
 * function MyComponent() {
 *   const tree: UITreeNode = response.ui_tree;
 *
 *   return (
 *     <UITreeForm
 *       tree={tree}
 *       onSubmit={(data) => console.log('Form submitted:', data)}
 *     />
 *   );
 * }
 * ```
 */

// Core components
export { UIRenderer, UIRendererStatic } from "./Renderer";
export { UITreeForm } from "./UITreeForm";

// Types
export type {
  UITreeNode,
  UIAction,
  FormData,
  SetFormData,
  PrimitiveProps,
  PrimitiveComponent,
  PrimitiveRegistry,
  UIRendererProps,
  UITreeFormProps,
} from "./types";

// Animations
export {
  containerVariants,
  itemVariants,
  staggerVariants,
  scaleVariants,
  fadeVariants,
  cardVariants,
  inputFocusVariants,
  transitions,
} from "./animations";

// Primitive registry and components
export { primitiveRegistry } from "./primitives";
export {
  // Layout
  Stack,
  Grid,
  Card,
  Divider,
  // Typography
  Text,
  Markdown,
  // Inputs
  TextInput,
  TextArea,
  Slider,
  RadioGroup,
  Radio,
  Checkbox,
  Select,
  // Actions
  Button,
  ButtonGroup,
  // Display
  ImageDisplay,
  Table,
  ProgressBar,
  Badge,
} from "./primitives";
