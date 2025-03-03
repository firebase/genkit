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
import { DocumentDataSchema } from './document';

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
  custom: z.record(z.unknown()).optional(),
});

/**
 * Zod schema for a text part.
 */
export const TextPartSchema = EmptyPartSchema.extend({
  /** The text of the message. */
  text: z.string(),
});

/**
 * Text part.
 */
export type TextPart = z.infer<typeof TextPartSchema>;

/**
 * Zod schema of a media part.
 */
export const MediaPartSchema = EmptyPartSchema.extend({
  media: z.object({
    /** The media content type. Inferred from data uri if not provided. */
    contentType: z.string().optional(),
    /** A `data:` or `https:` uri containing the media content.  */
    url: z.string(),
  }),
});

/**
 * Media part.
 */
export type MediaPart = z.infer<typeof MediaPartSchema>;

/**
 * Zod schema of a tool request part.
 */
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

/**
 * Tool part.
 */
export type ToolRequestPart = z.infer<typeof ToolRequestPartSchema>;

/**
 * Zod schema of a tool response part.
 */
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

/**
 * Zod schema of message part.
 */
export const PartSchema = z.union([
  TextPartSchema,
  MediaPartSchema,
  ToolRequestPartSchema,
  ToolResponsePartSchema,
  DataPartSchema,
  CustomPartSchema,
]);

/**
 * Message part.
 */
export type Part = z.infer<typeof PartSchema>;

/**
 * Zod schema of a message role.
 */
export const RoleSchema = z.enum(['system', 'user', 'model', 'tool']);

/**
 * Message role.
 */
export type Role = z.infer<typeof RoleSchema>;

/**
 * Zod schema of a message.
 */
export const MessageSchema = z.object({
  role: RoleSchema,
  content: z.array(PartSchema),
  metadata: z.record(z.unknown()).optional(),
});

/**
 * Model message data.
 */
export type MessageData = z.infer<typeof MessageSchema>;

/**
 * Zod schema of model info metadata.
 */
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
      output: z.array(z.string()).optional(),
      /** Model supports output in these content types. */
      contentType: z.array(z.string()).optional(),
      /** Model can natively support document-based context grounding. */
      context: z.boolean().optional(),
      /** Model can natively support constrained generation. */
      constrained: z.enum(['none', 'all', 'no-tools']).optional(),
      /** Model supports controlling tool choice, e.g. forced tool calling. */
      toolChoice: z.boolean().optional(),
    })
    .optional(),
  /** At which stage of development this model is.
   * - `featured` models are recommended for general use.
   * - `stable` models are well-tested and reliable.
   * - `unstable` models are experimental and may change.
   * - `legacy` models are no longer recommended for new projects.
   * - `deprecated` models are deprecated by the provider and may be removed in future versions.
   */
  stage: z
    .enum(['featured', 'stable', 'unstable', 'legacy', 'deprecated'])
    .optional(),
});

/**
 * Model info metadata.
 */
export type ModelInfo = z.infer<typeof ModelInfoSchema>;

/**
 * Zod schema of a tool definition.
 */
export const ToolDefinitionSchema = z.object({
  name: z.string(),
  description: z.string(),
  inputSchema: z
    .record(z.any())
    .describe('Valid JSON Schema representing the input of the tool.')
    .nullish(),
  outputSchema: z
    .record(z.any())
    .describe('Valid JSON Schema describing the output of the tool.')
    .nullish(),
  metadata: z
    .record(z.any())
    .describe('additional metadata for this tool definition')
    .optional(),
});

/**
 * Tool definition.
 */
export type ToolDefinition = z.infer<typeof ToolDefinitionSchema>;

/**
 * Zod schema of a common config object.
 */
export const GenerationCommonConfigSchema = z.object({
  /** A specific version of a model family, e.g. `gemini-1.0-pro-001` for the `gemini-1.0-pro` family. */
  version: z.string().optional(),
  temperature: z.number().optional(),
  maxOutputTokens: z.number().optional(),
  topK: z.number().optional(),
  topP: z.number().optional(),
  stopSequences: z.array(z.string()).optional(),
});

/**
 * Common config object.
 */
export type GenerationCommonConfig = typeof GenerationCommonConfigSchema;

/**
 * Zod schema of output config.
 */
export const OutputConfigSchema = z.object({
  format: z.string().optional(),
  schema: z.record(z.any()).optional(),
  constrained: z.boolean().optional(),
  instructions: z.string().optional(),
  contentType: z.string().optional(),
});

/**
 * Output config.
 */
export type OutputConfig = z.infer<typeof OutputConfigSchema>;

/** ModelRequestSchema represents the parameters that are passed to a model when generating content. */
export const ModelRequestSchema = z.object({
  messages: z.array(MessageSchema),
  config: z.any().optional(),
  tools: z.array(ToolDefinitionSchema).optional(),
  toolChoice: z.enum(['auto', 'required', 'none']).optional(),
  output: OutputConfigSchema.optional(),
  docs: z.array(DocumentDataSchema).optional(),
});
/** ModelRequest represents the parameters that are passed to a model when generating content. */
export interface ModelRequest<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
> extends z.infer<typeof ModelRequestSchema> {
  config?: z.infer<CustomOptionsSchema>;
}
/**
 * Zod schema of a generate request.
 */
export const GenerateRequestSchema = ModelRequestSchema.extend({
  /** @deprecated All responses now return a single candidate. This will always be `undefined`. */
  candidates: z.number().optional(),
});

/**
 * Generate request data.
 */
export type GenerateRequestData = z.infer<typeof GenerateRequestSchema>;

/**
 * Generate request.
 */
export interface GenerateRequest<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
> extends z.infer<typeof GenerateRequestSchema> {
  config?: z.infer<CustomOptionsSchema>;
}

/**
 * Zod schema of usage info from a generate request.
 */
export const GenerationUsageSchema = z.object({
  inputTokens: z.number().optional(),
  outputTokens: z.number().optional(),
  totalTokens: z.number().optional(),
  inputCharacters: z.number().optional(),
  outputCharacters: z.number().optional(),
  inputImages: z.number().optional(),
  outputImages: z.number().optional(),
  inputVideos: z.number().optional(),
  outputVideos: z.number().optional(),
  inputAudioFiles: z.number().optional(),
  outputAudioFiles: z.number().optional(),
  custom: z.record(z.number()).optional(),
});

/**
 * Usage info from a generate request.
 */
export type GenerationUsage = z.infer<typeof GenerationUsageSchema>;

/** Model response finish reason enum. */
const FinishReasonSchema = z.enum([
  'stop',
  'length',
  'blocked',
  'interrupted',
  'other',
  'unknown',
]);

/** @deprecated All responses now return a single candidate. Only the first candidate will be used if supplied. */
export const CandidateSchema = z.object({
  index: z.number(),
  message: MessageSchema,
  usage: GenerationUsageSchema.optional(),
  finishReason: FinishReasonSchema,
  finishMessage: z.string().optional(),
  custom: z.unknown(),
});
/** @deprecated All responses now return a single candidate. Only the first candidate will be used if supplied. */
export type CandidateData = z.infer<typeof CandidateSchema>;

/** @deprecated All responses now return a single candidate. Only the first candidate will be used if supplied. */
export const CandidateErrorSchema = z.object({
  index: z.number(),
  code: z.enum(['blocked', 'other', 'unknown']),
  message: z.string().optional(),
});
/** @deprecated All responses now return a single candidate. Only the first candidate will be used if supplied. */
export type CandidateError = z.infer<typeof CandidateErrorSchema>;

/**
 * Zod schema of a model response.
 */
export const ModelResponseSchema = z.object({
  message: MessageSchema.optional(),
  finishReason: FinishReasonSchema,
  finishMessage: z.string().optional(),
  latencyMs: z.number().optional(),
  usage: GenerationUsageSchema.optional(),
  /** @deprecated use `raw` instead */
  custom: z.unknown(),
  raw: z.unknown(),
  request: GenerateRequestSchema.optional(),
});

/**
 * Model response data.
 */
export type ModelResponseData = z.infer<typeof ModelResponseSchema>;

/**
 * Zod schema of generaete response.
 */
export const GenerateResponseSchema = ModelResponseSchema.extend({
  /** @deprecated All responses now return a single candidate. Only the first candidate will be used if supplied. Return `message`, `finishReason`, and `finishMessage` instead. */
  candidates: z.array(CandidateSchema).optional(),
  finishReason: FinishReasonSchema.optional(),
});

/**
 * Generate response data.
 */
export type GenerateResponseData = z.infer<typeof GenerateResponseSchema>;

/** ModelResponseChunkSchema represents a chunk of content to stream to the client. */
export const ModelResponseChunkSchema = z.object({
  role: RoleSchema.optional(),
  /** index of the message this chunk belongs to. */
  index: z.number().optional(),
  /** The chunk of content to stream right now. */
  content: z.array(PartSchema),
  /** Model-specific extra information attached to this chunk. */
  custom: z.unknown().optional(),
  /** If true, the chunk includes all data from previous chunks. Otherwise, considered to be incremental. */
  aggregated: z.boolean().optional(),
});
export type ModelResponseChunkData = z.infer<typeof ModelResponseChunkSchema>;

export const GenerateResponseChunkSchema = ModelResponseChunkSchema;
export type GenerateResponseChunkData = z.infer<
  typeof GenerateResponseChunkSchema
>;

export const GenerateActionOutputConfig = z.object({
  format: z.string().optional(),
  contentType: z.string().optional(),
  instructions: z.union([z.boolean(), z.string()]).optional(),
  jsonSchema: z.any().optional(),
  constrained: z.boolean().optional(),
});

export const GenerateActionOptionsSchema = z.object({
  /** A model name (e.g. `vertexai/gemini-1.0-pro`). */
  model: z.string(),
  /** Retrieved documents to be used as context for this generation. */
  docs: z.array(DocumentDataSchema).optional(),
  /** Conversation history for multi-turn prompting when supported by the underlying model. */
  messages: z.array(MessageSchema),
  /** List of registered tool names for this generation if supported by the underlying model. */
  tools: z.array(z.string()).optional(),
  /** Tool calling mode. `auto` lets the model decide whether to use tools, `required` forces the model to choose a tool, and `none` forces the model not to use any tools. Defaults to `auto`.  */
  toolChoice: z.enum(['auto', 'required', 'none']).optional(),
  /** Configuration for the generation request. */
  config: z.any().optional(),
  /** Configuration for the desired output of the request. Defaults to the model's default output if unspecified. */
  output: GenerateActionOutputConfig.optional(),
  /** Options for resuming an interrupted generation. */
  resume: z
    .object({
      respond: z.array(ToolResponsePartSchema).optional(),
      restart: z.array(ToolRequestPartSchema).optional(),
      metadata: z.record(z.any()).optional(),
    })
    .optional(),
  /** When true, return tool calls for manual processing instead of automatically resolving them. */
  returnToolRequests: z.boolean().optional(),
  /** Maximum number of tool call iterations that can be performed in a single generate call (default 5). */
  maxTurns: z.number().optional(),
});
export type GenerateActionOptions = z.infer<typeof GenerateActionOptionsSchema>;
