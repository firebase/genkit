/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
import z from 'zod';

//
// IMPORTANT: Keep this file in sync with genkit/ai/src/document.ts!
//

const EmptyPartSchema = z.object({
  text: z.never().optional(),
  media: z.never().optional(),
  toolRequest: z.never().optional(),
  toolResponse: z.never().optional(),
  data: z.unknown().optional(),
  metadata: z.record(z.unknown()).optional(),
  custom: z.record(z.unknown()).optional(),
  reasoning: z.never().optional(),
});

/**
 * Zod schema for a text part.
 */
export const TextPartSchema = EmptyPartSchema.extend({
  /** The text of the document. */
  text: z.string(),
});

/**
 * Zod schema for a reasoning part.
 */
export const ReasoningPartSchema = EmptyPartSchema.extend({
  /** The reasoning text of the message. */
  reasoning: z.string(),
});

/**
 * Text part.
 */
export type TextPart = z.infer<typeof TextPartSchema>;

/**
 * Zod schema of media.
 */
export const MediaSchema = z.object({
  /** The media content type. Inferred from data uri if not provided. */
  contentType: z.string().optional(),
  /** A `data:` or `https:` uri containing the media content.  */
  url: z.string(),
});

/**
 * Zod schema of a media part.
 */
export const MediaPartSchema = EmptyPartSchema.extend({
  media: MediaSchema,
});

/**
 * Media part.
 */
export type MediaPart = z.infer<typeof MediaPartSchema>;

/**
 * Zod schema of a tool request.
 */
export const ToolRequestSchema = z.object({
  /** The call id or reference for a specific request. */
  ref: z.string().optional(),
  /** The name of the tool to call. */
  name: z.string(),
  /** The input parameters for the tool, usually a JSON object. */
  input: z.unknown().optional(),
});

/**
 * Zod schema of a tool request part.
 */
export const ToolRequestPartSchema = EmptyPartSchema.extend({
  /** A request for a tool to be executed, usually provided by a model. */
  toolRequest: ToolRequestSchema,
});

/**
 * Tool part.
 */
export type ToolRequestPart = z.infer<typeof ToolRequestPartSchema>;

/**
 * Zod schema of a tool response.
 */
export const ToolResponseSchema = z.object({
  /** The call id or reference for a specific request. */
  ref: z.string().optional(),
  /** The name of the tool. */
  name: z.string(),
  /** The output data returned from the tool, usually a JSON object. */
  output: z.unknown().optional(),
});

/**
 * Zod schema of a tool response part.
 */
export const ToolResponsePartSchema = EmptyPartSchema.extend({
  /** A provided response to a tool call. */
  toolResponse: ToolResponseSchema,
});

/**
 * Tool response part.
 */
export type ToolResponsePart = z.infer<typeof ToolResponsePartSchema>;

/**
 * Zod schema of a data part.
 */
export const DataPartSchema = EmptyPartSchema.extend({
  data: z.unknown(),
});

/**
 * Data part.
 */
export type DataPart = z.infer<typeof DataPartSchema>;

/**
 * Zod schema of a custom part.
 */
export const CustomPartSchema = EmptyPartSchema.extend({
  custom: z.record(z.any()),
});

/**
 * Custom part.
 */
export type CustomPart = z.infer<typeof CustomPartSchema>;

// Disclaimer: genkit/js/ai/document.ts defines the following schema, type pair
// as PartSchema and Part, respectively. genkit-tools cannot retain those names
// due to it clashing with similar schema in model.ts, and genkit-tools
// exporting all types at root. We use a different name here and updated
// coresponding the imports.
export const DocumentPartSchema = z.union([TextPartSchema, MediaPartSchema]);
export type DocumentPart = z.infer<typeof DocumentPartSchema>;

export const DocumentDataSchema = z.object({
  content: z.array(DocumentPartSchema),
  metadata: z.record(z.string(), z.any()).optional(),
});
export type DocumentData = z.infer<typeof DocumentDataSchema>;
