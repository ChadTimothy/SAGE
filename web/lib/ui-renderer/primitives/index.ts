/**
 * Primitive Component Registry
 *
 * Maps component names to their React implementations.
 * Used by UIRenderer to look up components dynamically.
 */

import type { PrimitiveRegistry } from "../types";

// Layout primitives
import { Stack, Grid, Card, Divider } from "./layout";

// Typography primitives
import { Text, Markdown } from "./typography";

// Input primitives
import { TextInput, TextArea, Slider, RadioGroup, Radio, Checkbox, Select } from "./inputs";

// Action primitives
import { Button, ButtonGroup } from "./actions";

// Display primitives
import { ImageDisplay, Table, ProgressBar, Badge } from "./display";

/**
 * Registry mapping component names to implementations.
 *
 * Component names are case-sensitive and must match exactly
 * what the backend generates in UITreeNode.component.
 */
export const primitiveRegistry: PrimitiveRegistry = {
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
  Image: ImageDisplay,
  Table,
  ProgressBar,
  Badge,
};

// Re-export all primitives for direct use
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
};
