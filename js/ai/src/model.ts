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
  GenkitError,
  getStreamingCallback,
  SimpleMiddleware,
  StreamingCallback,
  z,
} from '@genkit-ai/core';
import { Registry } from '@genkit-ai/core/registry';
import { toJsonSchema } from '@genkit-ai/core/schema';
import { performance } from 'node:perf_hooks';
import { DocumentDataSchema } from './document.js';
import { augmentWithContext, validateSupport } from './model/middleware.js';

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
export type GenerationCommonConfig = typeof GenerationCommonConfigSchema;

const OutputConfigSchema = z.object({
  format: z.string().optional(),
  schema: z.record(z.any()).optional(),
  constrained: z.boolean().optional(),
  instructions: z.string().optional(),
  contentType: z.string().optional(),
});
export type OutputConfig = z.infer<typeof OutputConfigSchema>;

/** ModelRequestSchema represents the parameters that are passed to a model when generating content. */
export const ModelRequestSchema = z.object({
  messages: z.array(MessageSchema),
  config: z.any().optional(),
  tools: z.array(ToolDefinitionSchema).optional(),
  output: OutputConfigSchema.optional(),
  docs: z.array(DocumentDataSchema).optional(),
});
/** ModelRequest represents the parameters that are passed to a model when generating content. */
export interface ModelRequest<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
> extends z.infer<typeof ModelRequestSchema> {
  config?: z.infer<CustomOptionsSchema>;
}

export const GenerateRequestSchema = ModelRequestSchema.extend({
  /** @deprecated All responses now return a single candidate. This will always be `undefined`. */
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

/** @deprecated All responses now return a single candidate. Only the first candidate will be used if supplied. */
export const CandidateSchema = z.object({
  index: z.number(),
  message: MessageSchema,
  usage: GenerationUsageSchema.optional(),
  finishReason: z.enum(['stop', 'length', 'blocked', 'other', 'unknown']),
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

export const ModelResponseSchema = z.object({
  message: MessageSchema.optional(),
  finishReason: z.enum(['stop', 'length', 'blocked', 'other', 'unknown']),
  finishMessage: z.string().optional(),
  latencyMs: z.number().optional(),
  usage: GenerationUsageSchema.optional(),
  /** @deprecated use `raw` instead */
  custom: z.unknown(),
  raw: z.unknown(),
  request: GenerateRequestSchema.optional(),
});
export type ModelResponseData = z.infer<typeof ModelResponseSchema>;

export const GenerateResponseSchema = ModelResponseSchema.extend({
  /** @deprecated All responses now return a single candidate. Only the first candidate will be used if supplied. Return `message`, `finishReason`, and `finishMessage` instead. */
  candidates: z.array(CandidateSchema).optional(),
  finishReason: z
    .enum(['stop', 'length', 'blocked', 'other', 'unknown'])
    .optional(),
});
export type GenerateResponseData = z.infer<typeof GenerateResponseSchema>;

/** ModelResponseChunkSchema represents a chunk of content to stream to the client. */
export const ModelResponseChunkSchema = z.object({
  /** The chunk of content to stream right now. */
  content: z.array(PartSchema),
  /** Model-specific extra information attached to this chunk. */
  custom: z.unknown().optional(),
  /** If true, the chunk includes all data from previous chunks. Otherwise, considered to be incremental. */
  aggregated: z.boolean().optional(),
});
export type ModelResponseChunkData = z.infer<typeof ModelResponseChunkSchema>;

export const GenerateResponseChunkSchema = ModelResponseChunkSchema.extend({
  /** @deprecated The index of the candidate this chunk belongs to. Always 0. */
  index: z.number().optional(),
});
export type GenerateResponseChunkData = z.infer<
  typeof GenerateResponseChunkSchema
>;

export type ModelAction<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
> = Action<
  typeof GenerateRequestSchema,
  typeof GenerateResponseSchema,
  typeof GenerateResponseChunkSchema
> & {
  __configSchema: CustomOptionsSchema;
};

export type ModelMiddleware = SimpleMiddleware<
  z.infer<typeof GenerateRequestSchema>,
  z.infer<typeof GenerateResponseSchema>
>;

export type DefineModelOptions<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
> = {
  name: string;
  /** Known version names for this model, e.g. `gemini-1.0-pro-001`. */
  versions?: string[];
  /** Capabilities this model supports. */
  supports?: ModelInfo['supports'];
  /** Custom options schema for this model. */
  configSchema?: CustomOptionsSchema;
  /** Descriptive name for this model e.g. 'Google AI - Gemini Pro'. */
  label?: string;
  /** Middleware to be used with this model. */
  use?: ModelMiddleware[];
};

/**
 * Defines a new model and adds it to the registry.
 */
export function defineModel<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  options: DefineModelOptions<CustomOptionsSchema>,
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
  // middleware.push(conformOutput(registry));
  const act = defineAction(
    registry,
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
  config?: z.infer<CustomOptions>;

  withConfig(cfg: z.infer<CustomOptions>): ModelReference<CustomOptions>;
  withVersion(version: string): ModelReference<CustomOptions>;
}

/** Cretes a model reference. */
export function modelRef<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
>(
  options: Omit<
    ModelReference<CustomOptionsSchema>,
    'withConfig' | 'withVersion'
  >
): ModelReference<CustomOptionsSchema> {
  const ref: Partial<ModelReference<CustomOptionsSchema>> = { ...options };
  ref.withConfig = (
    cfg: z.infer<CustomOptionsSchema>
  ): ModelReference<CustomOptionsSchema> => {
    return modelRef({
      ...options,
      config: cfg,
    });
  };
  ref.withVersion = (version: string): ModelReference<CustomOptionsSchema> => {
    return modelRef({
      ...options,
      version,
    });
  };
  return ref as ModelReference<CustomOptionsSchema>;
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
  response: MessageData | CandidateData[]
): GenerationUsage {
  const inputCounts = getPartCounts(input.flatMap((md) => md.content));
  const outputCounts = getPartCounts(
    Array.isArray(response)
      ? response.flatMap((c) => c.message.content)
      : response.content
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
      const isImage =
        part.media?.contentType?.startsWith('image') ||
        part.media?.url?.startsWith('data:image');
      const isVideo =
        part.media?.contentType?.startsWith('video') ||
        part.media?.url?.startsWith('data:video');
      const isAudio =
        part.media?.contentType?.startsWith('audio') ||
        part.media?.url?.startsWith('data:audio');
      return {
        characters: counts.characters + (part.text?.length || 0),
        images: counts.images + (isImage ? 1 : 0),
        videos: counts.videos + (isVideo ? 1 : 0),
        audio: counts.audio + (isAudio ? 1 : 0),
      };
    },
    { characters: 0, images: 0, videos: 0, audio: 0 }
  );
}

export type ModelArgument<
  CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
> = ModelAction<CustomOptions> | ModelReference<CustomOptions> | string;

export interface ResolvedModel<
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> {
  modelAction: ModelAction;
  config?: z.infer<CustomOptions>;
  version?: string;
}

export async function resolveModel<C extends z.ZodTypeAny = z.ZodTypeAny>(
  registry: Registry,
  model: ModelArgument<C> | undefined
): Promise<ResolvedModel<C>> {
  let out: ResolvedModel<C>;
  let modelId: string;

  if (!model) {
    model = await registry.lookupValue('defaultModel', 'defaultModel');
  }
  if (!model) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: 'Must supply a `model` to `generate()` calls.',
    });
  }
  if (typeof model === 'string') {
    modelId = model;
    out = { modelAction: await registry.lookupAction(`/model/${model}`) };
  } else if (model.hasOwnProperty('__action')) {
    modelId = (model as ModelAction).__action.name;
    out = { modelAction: model as ModelAction };
  } else {
    const ref = model as ModelReference<any>;
    modelId = ref.name;
    out = {
      modelAction: (await registry.lookupAction(
        `/model/${ref.name}`
      )) as ModelAction,
      config: {
        ...ref.config,
      },
      version: ref.version,
    };
  }

  if (!out.modelAction) {
    throw new GenkitError({
      status: 'NOT_FOUND',
      message: `Model ${modelId} not found`,
    });
  }

  return out;
}
