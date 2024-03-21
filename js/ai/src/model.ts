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
  action,
  getStreamingCallback,
  StreamingCallback,
} from '@genkit-ai/common';
import * as registry from '@genkit-ai/common/registry';
import {
  setCustomMetadataAttributes,
  spanMetadataAls,
} from '@genkit-ai/common/tracing';
import { performance } from 'node:perf_hooks';
import { z } from 'zod';
import zodToJsonSchema from 'zod-to-json-schema';
import { conformOutput, validateSupport } from './model/middleware';
import * as telemetry from './telemetry';

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
});
export type MessageData = z.infer<typeof MessageSchema>;

const OutputFormatSchema = z.enum(['json', 'text', 'media']);

export const ModelInfoSchema = z.object({
  /** Acceptable names for this model (e.g. different versions). */
  names: z.array(z.string()).optional(),
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
      /** Model can output this type of data. */
      output: z.array(OutputFormatSchema).optional(),
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

export const GenerationConfigSchema = z.object({
  temperature: z.number().optional(),
  maxOutputTokens: z.number().optional(),
  topK: z.number().optional(),
  topP: z.number().optional(),
  custom: z.record(z.any()).optional(),
  stopSequences: z.array(z.string()).optional(),
});
export type GenerationConfig<CustomOptions = any> = z.infer<
  typeof GenerationConfigSchema
> & { custom?: CustomOptions };

const OutputConfigSchema = z.object({
  format: OutputFormatSchema.optional(),
  schema: z.record(z.any()).optional(),
});
export type OutputConfig = z.infer<typeof OutputConfigSchema>;

export const GenerationRequestSchema = z.object({
  messages: z.array(MessageSchema),
  config: GenerationConfigSchema.optional(),
  tools: z.array(ToolDefinitionSchema).optional(),
  output: OutputConfigSchema.optional(),
  candidates: z.number().optional(),
});
export type GenerationRequest = z.infer<typeof GenerationRequestSchema>;

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

export const GenerationResponseSchema = z.object({
  candidates: z.array(CandidateSchema),
  latencyMs: z.number().optional(),
  usage: GenerationUsageSchema.optional(),
  custom: z.unknown(),
});
export type GenerationResponseData = z.infer<typeof GenerationResponseSchema>;

export const GenerationResponseChunkSchema = z.object({
  /** The index of the candidate this chunk belongs to. */
  index: z.number(),
  /** The chunk of content to stream right now. */
  content: z.array(PartSchema),
  /** Model-specific extra information attached to this chunk. */
  custom: z.unknown().optional(),
});
export type GenerationResponseChunkData = z.infer<
  typeof GenerationResponseChunkSchema
>;

export type ModelAction<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny
> = Action<
  typeof GenerationRequestSchema,
  typeof GenerationResponseSchema,
  { model: ModelInfo }
> & {
  __customOptionsType: CustomOptionsSchema;
};

export interface ModelMiddleware {
  (
    req: GenerationRequest,
    next: (req?: GenerationRequest) => Promise<GenerationResponseData>
  ): Promise<GenerationResponseData>;
}

/**
 *
 */
export function modelWithMiddleware(
  model: ModelAction,
  middleware: ModelMiddleware[]
): ModelAction {
  const wrapped = (async (req: GenerationRequest) => {
    const dispatch = async (index: number, req: GenerationRequest) => {
      if (index === middleware.length) {
        // end of the chain, call the original model action
        return await model(req);
      }

      const currentMiddleware = middleware[index];
      return currentMiddleware(req, async (modifiedReq) =>
        dispatch(index + 1, modifiedReq || req)
      );
    };

    return await dispatch(0, req);
  }) as ModelAction;
  wrapped.__action = model.__action;
  return wrapped;
}

/**
 *
 */
export function defineModel<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny
>(
  options: {
    name: string;
    /** Alternate acceptable names for this model (e.g. different versions). */
    names?: string[];
    /** Capabilities this model supports. */
    supports?: ModelInfo['supports'];
    /** Custom options schema for this model. */
    customOptionsType?: CustomOptionsSchema;
    /** Descriptive name for this model e.g. 'Google AI - Gemini Pro'. */
    label?: string;
    use?: ModelMiddleware[];
  },
  runner: (
    request: GenerationRequest,
    streamingCallback?: StreamingCallback<GenerationResponseChunkData>
  ) => Promise<GenerationResponseData>
): ModelAction<CustomOptionsSchema> {
  const label = options.label || `${options.name} GenAI model`;
  const act = action(
    {
      name: options.name,
      description: label,
      input: GenerationRequestSchema,
      output: GenerationResponseSchema,
      metadata: {
        model: {
          label,
          customOptions: options.customOptionsType
            ? zodToJsonSchema(options.customOptionsType)
            : undefined,
          names: options.names,
          supports: options.supports,
        },
      },
    },
    (input) => {
      setCustomMetadataAttributes({ subtype: 'model' });
      const startTimeMs = performance.now();
      return runner(input, getStreamingCallback())
        .then((response) => {
          const timedResponse = {
            ...response,
            latencyMs: performance.now() - startTimeMs,
          };
          writeMetrics(options.name, input, { response: timedResponse });
          return timedResponse;
        })
        .catch((err) => {
          writeMetrics(options.name, input, { err });
          throw err;
        });
    }
  );
  Object.assign(act, {
    __customOptionsType: options.customOptionsType || z.unknown(),
  });
  const middleware = [
    ...(options.use || []),
    validateSupport(options),
    conformOutput(),
  ];
  const ma = modelWithMiddleware(
    act as ModelAction,
    middleware
  ) as ModelAction<CustomOptionsSchema>;
  registry.registerAction('model', ma.__action.name, ma);
  return ma;
}

export interface ModelReference<CustomOptions extends z.ZodTypeAny> {
  name: string;
  configSchema?: CustomOptions;
  info?: ModelInfo;
}

/**
 *
 */
export function modelRef<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny
>(
  options: ModelReference<CustomOptionsSchema>
): ModelReference<CustomOptionsSchema> {
  return { ...options };
}

/** Container for counting usage stats for a single input/output {Part} */
type PartCounts = {
  characters: number;
  images: number;
};

/**
 * Calculates basic usage statistics from the given model inputs and outputs.
 */
export function getBasicUsageStats(
  input: MessageData[],
  candidates: CandidateData[]
): GenerationUsage {
  const responseCandidateParts = candidates.flatMap(
    (candidate) => candidate.message.content
  );
  const inputCounts = getPartCounts(input.flatMap((md) => md.content));
  const outputCounts = getPartCounts(
    candidates.flatMap((c) => c.message.content)
  );
  return {
    inputCharacters: inputCounts.characters,
    inputImages: inputCounts.images,
    outputCharacters: outputCounts.characters,
    outputImages: outputCounts.images,
  };
}

function getPartCounts(parts: Part[]): PartCounts {
  return parts.reduce(
    (counts, part) => {
      return {
        characters: counts.characters + (part.text?.length || 0),
        images: counts.images + (part.media ? 1 : 0),
      };
    },
    { characters: 0, images: 0 }
  );
}

function writeMetrics(
  modelName: string,
  input: GenerationRequest,
  opts: {
    response?: GenerationResponseData;
    err?: any;
  }
) {
  telemetry.recordGenerateAction(modelName, {
    temperature: input.config?.temperature,
    topK: input.config?.topK,
    topP: input.config?.topP,
    maxOutputTokens: input.config?.maxOutputTokens,
    path: spanMetadataAls?.getStore()?.path,
    inputTokens: opts.response?.usage?.inputTokens,
    outputTokens: opts.response?.usage?.outputTokens,
    totalTokens: opts.response?.usage?.totalTokens,
    inputCharacters: opts.response?.usage?.inputCharacters,
    outputCharacters: opts.response?.usage?.outputCharacters,
    inputImages: opts.response?.usage?.inputImages,
    outputImages: opts.response?.usage?.outputImages,
    latencyMs: opts.response?.latencyMs,
    err: opts.err,
  });
}

export type ModelArgument<CustomOptions extends z.ZodTypeAny = z.ZodTypeAny> =
  | ModelAction<CustomOptions>
  | ModelReference<CustomOptions>
  | string;
