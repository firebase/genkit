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

import {
  Action,
  defineAction,
  getStreamingCallback,
  Middleware,
  StreamingCallback,
} from '@genkit-ai/core';
import { toJsonSchema } from '@genkit-ai/core/schema';
import * as clc from 'colorette';
import { performance } from 'node:perf_hooks';
import { z } from 'zod';
import { DocumentDataSchema } from './document.js';
import {
  augmentWithContext,
  conformOutput,
  validateSupport,
} from './model/middleware.js';

//
// IMPORTANT: Please keep type definitions in sync with
//   genkit-tools/src/types/model.ts
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

export const CustomPartSchema = EmptyPartSchema.extend({
  custom: z.record(z.any()),
});
export type CustomPart = z.infer<typeof CustomPartSchema>;

export const PartSchema = z.union([
  TextPartSchema,
  MediaPartSchema,
  ToolRequestPartSchema,
  ToolResponsePartSchema,
  DataPartSchema,
  CustomPartSchema,
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
export type GenerateRequestData = z.infer<typeof GenerateRequestSchema>;

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
  inputVideos: z.number().optional(),
  outputVideos: z.number().optional(),
  inputAudioFiles: z.number().optional(),
  outputAudioFiles: z.number().optional(),
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

export type ModelAction<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
> = Action<
  typeof GenerateRequestSchema,
  typeof GenerateResponseSchema,
  { model: ModelInfo }
> & {
  __configSchema: CustomOptionsSchema;
};

export type ModelMiddleware = Middleware<
  z.infer<typeof GenerateRequestSchema>,
  z.infer<typeof GenerateResponseSchema>
>;

/**
 * Defines a new model and adds it to the registry.
 */
export function defineModel<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
>(
  options: {
    name: string;
    /** Known version names for this model, e.g. `gemini-1.0-pro-001`. */
    versions?: string[];
    /** Capabilities this model supports. */
    supports?: ModelInfo['supports'];
    /** Custom options schema for this model. */
    configSchema?: CustomOptionsSchema;
    /** Descriptive name for this model e.g. 'Google AI - Gemini Pro'. */
    label?: string;
    use?: ModelMiddleware[];
  },
  runner: (
    request: GenerateRequest<CustomOptionsSchema>,
    streamingCallback?: StreamingCallback<GenerateResponseChunkData>
  ) => Promise<GenerateResponseData>
): ModelAction<CustomOptionsSchema> {
  const label = options.label || options.name;
  const middleware: ModelMiddleware[] = [
    ...(options.use || []),
    validateSupport(options),
  ];
  if (!options?.supports?.context) middleware.push(augmentWithContext());
  middleware.push(conformOutput());
  const act = defineAction(
    {
      actionType: 'model',
      name: options.name,
      description: label,
      inputSchema: GenerateRequestSchema,
      outputSchema: GenerateResponseSchema,
      metadata: {
        model: {
          label,
          customOptions: options.configSchema
            ? toJsonSchema({ schema: options.configSchema })
            : undefined,
          versions: options.versions,
          supports: options.supports,
        },
      },
      use: middleware,
    },
    (input) => {
      const startTimeMs = performance.now();

      return runner(input, getStreamingCallback()).then((response) => {
        const timedResponse = {
          ...response,
          latencyMs: performance.now() - startTimeMs,
        };
        return timedResponse;
      });
    }
  );
  Object.assign(act, {
    __configSchema: options.configSchema || z.unknown(),
  });
  return act as ModelAction<CustomOptionsSchema>;
}

export interface ModelReference<CustomOptions extends z.ZodTypeAny> {
  name: string;
  configSchema?: CustomOptions;
  info?: ModelInfo;
  version?: string;
}

/**
 *
 */
export function modelRef<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
>(
  options: ModelReference<CustomOptionsSchema>
): ModelReference<CustomOptionsSchema> {
  if (options.info?.stage === 'deprecated') {
    deprecateModel({ name: options.name });
  }
  return { ...options };
}

/**
 * Warns when a model is deprecated.
 */
function deprecateModel(options: { name: string }) {
  console.warn(
    `${clc.bold(clc.yellow('Warning:'))} ` +
      `Model '${options.name}' is deprecated and may be removed in a future release.`
  );
}

/** Container for counting usage stats for a single input/output {Part} */
type PartCounts = {
  characters: number;
  images: number;
  videos: number;
  audio: number;
};

/**
 * Calculates basic usage statistics from the given model inputs and outputs.
 */
export function getBasicUsageStats(
  input: MessageData[],
  candidates: CandidateData[]
): GenerationUsage {
  const inputCounts = getPartCounts(input.flatMap((md) => md.content));
  const outputCounts = getPartCounts(
    candidates.flatMap((c) => c.message.content)
  );
  return {
    inputCharacters: inputCounts.characters,
    inputImages: inputCounts.images,
    inputVideos: inputCounts.videos,
    inputAudioFiles: inputCounts.audio,
    outputCharacters: outputCounts.characters,
    outputImages: outputCounts.images,
    outputVideos: outputCounts.videos,
    outputAudioFiles: outputCounts.audio,
  };
}

function getPartCounts(parts: Part[]): PartCounts {
  return parts.reduce(
    (counts, part) => {
      return {
        characters: counts.characters + (part.text?.length || 0),
        images:
          counts.images +
          (part.media?.contentType?.startsWith('image') ? 1 : 0),
        videos:
          counts.videos +
          (part.media?.contentType?.startsWith('video') ? 1 : 0),
        audio:
          counts.audio + (part.media?.contentType?.startsWith('audio') ? 1 : 0),
      };
    },
    { characters: 0, images: 0, videos: 0, audio: 0 }
  );
}

export type ModelArgument<
  CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
> = ModelAction<CustomOptions> | ModelReference<CustomOptions> | string;
