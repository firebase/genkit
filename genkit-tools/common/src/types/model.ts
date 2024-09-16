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
import { z } from 'zod';
import { DocumentDataSchema } from './document.js';

//
// IMPORTANT: Keep this file in sync with genkit/ai/src/model.ts!
//

const EmptyPartSchema = z.object({
  text: z.never().optional(),
  media: z.never().optional(),
  toolRequest: z.never().optional(),
  toolResponse: z.never().optional(),
  data: z.unknown().optional(),
  metadata: z.record(z.unknown()).optional(),
});

export const TextPartSchema = EmptyPartSchema.extend({
  /** The text of the message. */
  text: z.string(),
});
export type TextPart = z.infer<typeof TextPartSchema>;

export const MediaPartSchema = EmptyPartSchema.extend({
  media: z.object({
    /** The media content type. Inferred from data uri if not provided. */
    contentType: z.string().optional(),
    /** A `data:` or `https:` uri containing the media content.  */
    url: z.string(),
  }),
});
export type MediaPart = z.infer<typeof MediaPartSchema>;

export const ToolRequestPartSchema = EmptyPartSchema.extend({
  /** A request for a tool to be executed, usually provided by a model. */
  toolRequest: z.object({
    /** The call id or reference for a specific request. */
    ref: z.string().optional(),
    /** The name of the tool to call. */
    name: z.string(),
    /** The input parameters for the tool, usually a JSON object. */
    input: z.unknown().optional(),
  }),
});
export type ToolRequestPart = z.infer<typeof ToolRequestPartSchema>;

export const ToolResponsePartSchema = EmptyPartSchema.extend({
  /** A provided response to a tool call. */
  toolResponse: z.object({
    /** The call id or reference for a specific request. */
    ref: z.string().optional(),
    /** The name of the tool. */
    name: z.string(),
    /** The output data returned from the tool, usually a JSON object. */
    output: z.unknown().optional(),
  }),
});
export type ToolResponsePart = z.infer<typeof ToolResponsePartSchema>;

export const DataPartSchema = EmptyPartSchema.extend({
  data: z.unknown(),
});

export type DataPart = z.infer<typeof DataPartSchema>;

export const PartSchema = z.union([
  TextPartSchema,
  MediaPartSchema,
  ToolRequestPartSchema,
  ToolResponsePartSchema,
  DataPartSchema,
]);
export type Part = z.infer<typeof PartSchema>;

export const RoleSchema = z.enum(['system', 'user', 'model', 'tool']);
export type Role = z.infer<typeof RoleSchema>;

export const MessageSchema = z.object({
  role: RoleSchema,
  content: z.array(PartSchema),
  metadata: z.record(z.unknown()).optional(),
});
export type MessageData = z.infer<typeof MessageSchema>;

const OutputFormatSchema = z.enum(['json', 'text', 'media']);

export const ModelInfoSchema = z.object({
  /** Acceptable names for this model (e.g. different versions). */
  versions: z.array(z.string()).optional(),
  /** Friendly label for this model (e.g. "Google AI - Gemini Pro") */
  label: z.string().optional(),
  /** Supported model capabilities. */
  supports: z
    .object({
      /** Model can process historical messages passed with a prompt. */
      multiturn: z.boolean().optional(),
      /** Model can process media as part of the prompt (multimodal input). */
      media: z.boolean().optional(),
      /** Model can perform tool calls. */
      tools: z.boolean().optional(),
      /** Model can accept messages with role "system". */
      systemRole: z.boolean().optional(),
      /** Model can output this type of data. */
      output: z.array(OutputFormatSchema).optional(),
      /** Model can natively support document-based context grounding. */
      context: z.boolean().optional(),
    })
    .optional(),
});
export type ModelInfo = z.infer<typeof ModelInfoSchema>;

export const ToolDefinitionSchema = z.object({
  name: z.string(),
  description: z.string(),
  inputSchema: z
    .record(z.any())
    .describe('Valid JSON Schema representing the input of the tool.'),
  outputSchema: z
    .record(z.any())
    .describe('Valid JSON Schema describing the output of the tool.')
    .optional(),
});
export type ToolDefinition = z.infer<typeof ToolDefinitionSchema>;

export const GenerationCommonConfigSchema = z.object({
  /** A specific version of a model family, e.g. `gemini-1.0-pro-001` for the `gemini-1.0-pro` family. */
  version: z.string().optional(),
  temperature: z.number().optional(),
  maxOutputTokens: z.number().optional(),
  topK: z.number().optional(),
  topP: z.number().optional(),
  stopSequences: z.array(z.string()).optional(),
});

const OutputConfigSchema = z.object({
  format: OutputFormatSchema.optional(),
  schema: z.record(z.any()).optional(),
});
export type OutputConfig = z.infer<typeof OutputConfigSchema>;

export const GenerateRequestSchema = z.object({
  messages: z.array(MessageSchema),
  config: z.any().optional(),
  tools: z.array(ToolDefinitionSchema).optional(),
  output: OutputConfigSchema.optional(),
  context: z.array(DocumentDataSchema).optional(),
  candidates: z.number().optional(),
});

export interface GenerateRequest<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
> extends z.infer<typeof GenerateRequestSchema> {
  config?: z.infer<CustomOptionsSchema>;
}

export const GenerationUsageSchema = z.object({
  inputTokens: z.number().optional(),
  outputTokens: z.number().optional(),
  totalTokens: z.number().optional(),
  inputCharacters: z.number().optional(),
  outputCharacters: z.number().optional(),
  inputImages: z.number().optional(),
  outputImages: z.number().optional(),
  custom: z.record(z.number()).optional(),
});
export type GenerationUsage = z.infer<typeof GenerationUsageSchema>;

export const CandidateSchema = z.object({
  index: z.number(),
  message: MessageSchema,
  usage: GenerationUsageSchema.optional(),
  finishReason: z.enum(['stop', 'length', 'blocked', 'other', 'unknown']),
  finishMessage: z.string().optional(),
  custom: z.unknown(),
});
export type CandidateData = z.infer<typeof CandidateSchema>;

export const CandidateErrorSchema = z.object({
  index: z.number(),
  code: z.enum(['blocked', 'other', 'unknown']),
  message: z.string().optional(),
});
export type CandidateError = z.infer<typeof CandidateErrorSchema>;

export const GenerateResponseSchema = z.object({
  candidates: z.array(CandidateSchema),
  latencyMs: z.number().optional(),
  usage: GenerationUsageSchema.optional(),
  custom: z.unknown(),
  request: GenerateRequestSchema.optional(),
});
export type GenerateResponseData = z.infer<typeof GenerateResponseSchema>;

export const GenerateResponseChunkSchema = z.object({
  /** The index of the candidate this chunk belongs to. */
  index: z.number(),
  /** The chunk of content to stream right now. */
  content: z.array(PartSchema),
  /** Model-specific extra information attached to this chunk. */
  custom: z.unknown().optional(),
});
export type GenerateResponseChunkData = z.infer<
  typeof GenerateResponseChunkSchema
>;
