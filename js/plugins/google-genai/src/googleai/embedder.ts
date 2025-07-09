/**
 * Copyright 2025 Google LLC
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
  EmbedderAction,
  EmbedderInfo,
  EmbedderReference,
  Genkit,
  GenkitError,
  z,
} from 'genkit';
import { embedderRef } from 'genkit/embedder';
import { embedContent } from './client';
import { EmbedContentRequest, PluginOptions, TaskTypeSchema } from './types';
import { getApiKeyFromEnvVar } from './utils';

export const GoogleAIEmbeddingConfigSchema = z.object({
  /** Override the API key provided at plugin initialization. */
  apiKey: z.string().optional(),
  /**
   * The `task_type` parameter is defined as the intended downstream application to help the model
   * produce better quality embeddings.
   **/
  taskType: TaskTypeSchema.optional(),
  title: z.string().optional(),
  version: z.string().optional(),
  /**
   * The `outputDimensionality` parameter allows you to specify the dimensionality of the embedding output.
   * By default, the model generates embeddings with 768 dimensions. Models such as
   * `text-embedding-004`, `text-embedding-005`, and `text-multilingual-embedding-002`
   * allow the output dimensionality to be adjusted between 1 and 768.
   * By selecting a smaller output dimensionality, users can save memory and storage space, leading to more efficient computations.
   **/
  outputDimensionality: z.number().min(1).optional(),
});

export type GeminiEmbeddingConfig = z.infer<
  typeof GoogleAIEmbeddingConfigSchema
>;

// for commonRef
type ConfigSchema = typeof GoogleAIEmbeddingConfigSchema;

function commonRef(
  name: string,
  info?: EmbedderInfo
): EmbedderReference<ConfigSchema> {
  return embedderRef({
    name: `googleai/${name}`,
    configSchema: GoogleAIEmbeddingConfigSchema,
    info: info ?? {
      dimensions: 768,
      supports: {
        input: ['text'],
      },
    },
  });
}

// TODO(ifielker): Update embedders to be current models.
// (textEmbeddingGecko001 is outdated).

export const KNOWN_EMBEDDER_MODELS = {
  'text-embedding-004': commonRef('test-embedding-004'),
};

export function embedder(
  version: string,
  config: GeminiEmbeddingConfig = {}
): EmbedderReference<ConfigSchema> {
  const name = version.split('/').at(-1);
  if (name && KNOWN_EMBEDDER_MODELS[name]) {
    return embedderRef({
      name: `googleai/${name}`,
      configSchema: GoogleAIEmbeddingConfigSchema,
      config,
      info: {
        ...KNOWN_EMBEDDER_MODELS[name].info,
      },
    });
  }
  // Generic text-only embedder format
  return embedderRef({
    name: `googleai/${name}`,
    configSchema: GoogleAIEmbeddingConfigSchema,
    config,
    info: {
      dimensions: 768,
      supports: { input: ['text'] },
    },
  });
}

export function defineGoogleAIEmbedder(
  ai: Genkit,
  name: string,
  pluginOptions: PluginOptions
): EmbedderAction<any> {
  const apiModelName = name.startsWith('googleai/')
    ? name.substring('googleai/'.length)
    : name;
  let apiKey: string | undefined;
  // DO NOT throw if {apiKey: false} was supplied to options.
  if (pluginOptions.apiKey !== false) {
    apiKey = pluginOptions?.apiKey || getApiKeyFromEnvVar();
    if (!apiKey)
      throw new Error(
        'Please pass in the API key or set either GEMINI_API_KEY or GOOGLE_API_KEY environment variable.\n' +
          'For more details see https://firebase.google.com/docs/genkit/plugins/google-genai'
      );
  }

  const ref = embedder(apiModelName);

  return ai.defineEmbedder(
    {
      name: ref.name,
      configSchema: GoogleAIEmbeddingConfigSchema,
      info: ref.info!,
    },
    async (input, options) => {
      if (pluginOptions.apiKey === false && !options?.apiKey) {
        throw new GenkitError({
          status: 'INVALID_ARGUMENT',
          message:
            'GoogleAI plugin was initialized with {apiKey: false} but no apiKey configuration was passed at call time.',
        });
      }
      const embedApiKey = options?.apiKey || apiKey!;
      const embedVersion =
        options?.version || ref.config?.version || ref.version || apiModelName;
      const embeddings = await Promise.all(
        input.map(async (doc) => {
          const response = await embedContent(embedApiKey, embedVersion, {
            taskType: options?.taskType,
            title: options?.title,
            content: {
              role: '',
              parts: [{ text: doc.text }],
            },
            outputDimensionality: options?.outputDimensionality,
          } as EmbedContentRequest);
          const values = response.embedding.values;
          return { embedding: values };
        })
      );
      return { embeddings };
    }
  );
}
