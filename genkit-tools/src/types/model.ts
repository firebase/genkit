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

//
// IMPORTANT: Keep this file in sync with genkit/ai/src/model.ts!
//
import { z } from 'zod';

export const TextPartSchema = z.object({
  /** The text of the message. */
  text: z.string(),
  media: z.never().optional(),
  toolRequest: z.never().optional(),
  toolResponse: z.never().optional(),
});
export type TextPart = z.infer<typeof TextPartSchema>;

export const MediaPartSchema = z.object({
  text: z.never().optional(),
  media: z.object({
    /** The media content type. Inferred from data uri if not provided. */
    contentType: z.string().optional(),
    /** A `data:` or `https:` uri containing the media content.  */
    url: z.string(),
  }),
  toolRequest: z.never().optional(),
  toolResponse: z.never().optional(),
});
export type MediaPart = z.infer<typeof MediaPartSchema>;

export const ToolRequestPartSchema = z.object({
  text: z.never().optional(),
  media: z.never().optional(),
  /** A request for a tool to be executed, usually provided by a model. */
  toolRequest: z.object({
    /** The call id or reference for a specific request. */
    ref: z.string().optional(),
    /** The name of the tool to call. */
    name: z.string(),
    /** The input parameters for the tool, usually a JSON object. */
    input: z.unknown().optional(),
  }),
  toolResponse: z.never().optional(),
});
export type ToolRequestPart = z.infer<typeof ToolRequestPartSchema>;

export const ToolResponsePartSchema = z.object({
  text: z.never().optional(),
  media: z.never().optional(),
  toolRequest: z.never().optional(),
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

export const PartSchema = z.union([
  TextPartSchema,
  MediaPartSchema,
  ToolRequestPartSchema,
  ToolResponsePartSchema,
]);
export type Part = z.infer<typeof PartSchema>;

export const RoleSchema = z.enum(['system', 'user', 'model', 'tool']);
export type Role = z.infer<typeof RoleSchema>;

export const MessageSchema = z.object({
  role: RoleSchema,
  content: z.array(PartSchema),
});
export type MessageData = z.infer<typeof MessageSchema>;

export const ToolDefinitionSchema = z.object({
  name: z.string(),
  inputSchema: z
    .record(z.any())
    .describe('Valid JSON Schema representing the input of the tool.'),
  outputSchema: z
    .record(z.any())
    .describe('Valid JSON Schema describing the output of the tool.')
    .optional(),
});
export type ToolDefinition = z.infer<typeof ToolDefinitionSchema>;

export const GenerationConfig = z.object({
  version: z.string().optional(),
  temperature: z.number().optional(),
  maxOutputTokens: z.number().optional(),
  topK: z.number().optional(),
  topP: z.number().optional(),
  custom: z.record(z.any()).optional(),
  stopSequences: z.array(z.string()).optional(),
});
export type GenerationConfig<CustomOptions = any> = z.infer<
  typeof GenerationConfig
> & { custom?: CustomOptions };

const OutputConfigSchema = z.object({
  format: z.enum(['json', 'text']).optional(),
  schema: z.record(z.any()).optional(),
});
export type OutputConfig = z.infer<typeof OutputConfigSchema>;

export const GenerateRequestSchema = z.object({
  messages: z.array(MessageSchema),
  config: GenerationConfig.optional(),
  tools: z.array(ToolDefinitionSchema).optional(),
  output: OutputConfigSchema.optional(),
  candidates: z.number().optional(),
});
export type GenerateRequest = z.infer<typeof GenerateRequestSchema>;

export const GenerationUsageSchema = z.object({
  inputTokens: z.number().optional(),
  outputTokens: z.number().optional(),
  totalTokens: z.number().optional(),
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

export const GenerateResponseSchema = z.object({
  candidates: z.array(CandidateSchema),
  usage: GenerationUsageSchema.optional(),
  custom: z.unknown(),
});
export type GenerateResponseData = z.infer<typeof GenerateResponseSchema>;
