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

import { Action, defineAction, z } from '@genkit-ai/core';
import { Registry } from '@genkit-ai/core/registry';
import { Document, DocumentData, DocumentDataSchema } from './document.js';

export type EmbeddingBatch = { embedding: number[] }[];

export const EmbeddingSchema = z.array(z.number());
export type Embedding = z.infer<typeof EmbeddingSchema>;

export type EmbedderFn<EmbedderOptions extends z.ZodTypeAny> = (
  input: Document[],
  embedderOpts?: z.infer<EmbedderOptions>
) => Promise<EmbedResponse>;

const EmbedRequestSchema = z.object({
  input: z.array(DocumentDataSchema),
  options: z.any().optional(),
});

const EmbedResponseSchema = z.object({
  embeddings: z.array(z.object({ embedding: EmbeddingSchema })),
  // TODO: stats, etc.
});
type EmbedResponse = z.infer<typeof EmbedResponseSchema>;

export type EmbedderAction<CustomOptions extends z.ZodTypeAny = z.ZodTypeAny> =
  Action<typeof EmbedRequestSchema, typeof EmbedResponseSchema> & {
    __configSchema?: CustomOptions;
  };

export interface EmbedderParams<
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> {
  embedder: EmbedderArgument<CustomOptions>;
  content: string | DocumentData;
  metadata?: Record<string, unknown>;
  options?: z.infer<CustomOptions>;
}

function withMetadata<CustomOptions extends z.ZodTypeAny>(
  embedder: Action<typeof EmbedRequestSchema, typeof EmbedResponseSchema>,
  configSchema?: CustomOptions
): EmbedderAction<CustomOptions> {
  const withMeta = embedder as EmbedderAction<CustomOptions>;
  withMeta.__configSchema = configSchema;
  return withMeta;
}

/**
 * Creates embedder model for the provided {@link EmbedderFn} model implementation.
 */
export function defineEmbedder<
  ConfigSchema extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  options: {
    name: string;
    configSchema?: ConfigSchema;
    info?: EmbedderInfo;
  },
  runner: EmbedderFn<ConfigSchema>
) {
  const embedder = defineAction(
    registry,
    {
      actionType: 'embedder',
      name: options.name,
      inputSchema: options.configSchema
        ? EmbedRequestSchema.extend({
            options: options.configSchema.optional(),
          })
        : EmbedRequestSchema,
      outputSchema: EmbedResponseSchema,
      metadata: {
        type: 'embedder',
        info: options.info,
      },
    },
    (i) =>
      runner(
        i.input.map((dd) => new Document(dd)),
        i.options
      )
  );
  const ewm = withMetadata(
    embedder as Action<typeof EmbedRequestSchema, typeof EmbedResponseSchema>,
    options.configSchema
  );
  return ewm;
}

export type EmbedderArgument<
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> = string | EmbedderAction<CustomOptions> | EmbedderReference<CustomOptions>;

/**
 * A veneer for interacting with embedder models.
 */
export async function embed<CustomOptions extends z.ZodTypeAny = z.ZodTypeAny>(
  registry: Registry,
  params: EmbedderParams<CustomOptions>
): Promise<Embedding> {
  let embedder = await resolveEmbedder(registry, params);
  if (!embedder.embedderAction) {
    let embedderId: string;
    if (typeof params.embedder === 'string') {
      embedderId = params.embedder;
    } else if ((params.embedder as EmbedderAction)?.__action?.name) {
      embedderId = (params.embedder as EmbedderAction).__action.name;
    } else {
      embedderId = (params.embedder as EmbedderReference<any>).name;
    }
    throw new Error(`Unable to resolve embedder ${embedderId}`);
  }
  const response = await embedder.embedderAction({
    input:
      typeof params.content === 'string'
        ? [Document.fromText(params.content, params.metadata)]
        : [params.content],
    options: {
      version: embedder.version,
      ...embedder.config,
      ...params.options,
    },
  });
  return response.embeddings[0].embedding;
}

interface ResolvedEmbedder<CustomOptions extends z.ZodTypeAny = z.ZodTypeAny> {
  embedderAction: EmbedderAction<CustomOptions>;
  config?: z.infer<CustomOptions>;
  version?: string;
}

async function resolveEmbedder<
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  params: EmbedderParams<CustomOptions>
): Promise<ResolvedEmbedder<CustomOptions>> {
  if (typeof params.embedder === 'string') {
    return {
      embedderAction: await registry.lookupAction(
        `/embedder/${params.embedder}`
      ),
    };
  } else if (Object.hasOwnProperty.call(params.embedder, '__action')) {
    return {
      embedderAction: params.embedder as EmbedderAction<CustomOptions>,
    };
  } else if (Object.hasOwnProperty.call(params.embedder, 'name')) {
    const ref = params.embedder as EmbedderReference<any>;
    return {
      embedderAction: await registry.lookupAction(
        `/embedder/${(params.embedder as EmbedderReference).name}`
      ),
      config: {
        ...ref.config,
      },
      version: ref.version,
    };
  }
  throw new Error(`failed to resolve embedder ${params.embedder}`);
}

/**
 * A veneer for interacting with embedder models in bulk.
 */
export async function embedMany<
  ConfigSchema extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  params: {
    embedder: EmbedderArgument<ConfigSchema>;
    content: string[] | DocumentData[];
    metadata?: Record<string, unknown>;
    options?: z.infer<ConfigSchema>;
  }
): Promise<EmbeddingBatch> {
  let embedder: EmbedderAction<ConfigSchema>;
  if (typeof params.embedder === 'string') {
    embedder = await registry.lookupAction(`/embedder/${params.embedder}`);
  } else if (Object.hasOwnProperty.call(params.embedder, 'info')) {
    embedder = await registry.lookupAction(
      `/embedder/${(params.embedder as EmbedderReference).name}`
    );
  } else {
    embedder = params.embedder as EmbedderAction<ConfigSchema>;
  }
  if (!embedder) {
    throw new Error('Unable to utilize the provided embedder');
  }
  const response = await embedder({
    input: params.content.map((i) =>
      typeof i === 'string' ? Document.fromText(i, params.metadata) : i
    ),
    options: params.options,
  });
  return response.embeddings;
}

export const EmbedderInfoSchema = z.object({
  /** Friendly label for this model (e.g. "Google AI - Gemini Pro") */
  label: z.string().optional(),
  /** Supported model capabilities. */
  supports: z
    .object({
      /** Model can input this type of data. */
      input: z.array(z.enum(['text', 'image'])).optional(),
      /** Model can support multiple languages */
      multilingual: z.boolean().optional(),
    })
    .optional(),
  /** Embedding dimension */
  dimensions: z.number().optional(),
});
export type EmbedderInfo = z.infer<typeof EmbedderInfoSchema>;

export interface EmbedderReference<
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> {
  name: string;
  configSchema?: CustomOptions;
  info?: EmbedderInfo;
  config?: z.infer<CustomOptions>;
  version?: string;
}

/**
 * Helper method to configure a {@link EmbedderReference} to a plugin.
 */
export function embedderRef<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
>(
  options: EmbedderReference<CustomOptionsSchema>
): EmbedderReference<CustomOptionsSchema> {
  return { ...options };
}
