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

import { z, type Document, type Genkit } from 'genkit';
import {
  EmbedderInfo,
  embedderRef,
  type EmbedderAction,
  type EmbedderReference,
} from 'genkit/embedder';
import { embedContent } from './client';
import {
  ClientOptions,
  EmbedContentRequest,
  EmbeddingInstance,
  EmbeddingPrediction,
  EmbeddingResult,
  TaskTypeSchema,
  isMultimodalEmbeddingPrediction,
  isObject,
} from './types';

export const VertexEmbeddingConfigSchema = z.object({
  /**
   * The `task_type` parameter is defined as the intended downstream application
   * to help the model produce better quality embeddings.
   **/
  taskType: TaskTypeSchema.optional(),
  title: z.string().optional(),
  location: z.string().optional(),
  version: z.string().optional(),
  /**
   * The `outputDimensionality` parameter allows you to specify the dimensionality of the embedding output.
   * By default, the model generates embeddings with 768 dimensions.
   * By selecting a smaller output dimensionality, users can save memory and storage space, leading to more efficient computations.
   **/
  outputDimensionality: z.number().min(1).optional(),
  /**
   * For newly released embedders this parameter provides a hint for the proper
   * way to call the embedder. (Multimodal embedders have a different request
   * structure than non-multimodal embedders).
   * For well-known embedders, this value will be ignored since we will already
   * know if it's multimodal or not.
   */
  multimodal: z.boolean().optional(),
});

export type VertexEmbeddingConfig = z.infer<typeof VertexEmbeddingConfigSchema>;

// for commonRef
type ConfigSchema = typeof VertexEmbeddingConfigSchema;

function commonRef(
  name: string,
  info?: EmbedderInfo
): EmbedderReference<ConfigSchema> {
  return embedderRef({
    name: `vertexai/${name}`,
    configSchema: VertexEmbeddingConfigSchema,
    info: info ?? {
      dimensions: 768,
      supports: {
        input: ['text'],
      },
    },
  });
}

export const KNOWN_EMBEDDER_MODELS: Record<
  string,
  EmbedderReference<ConfigSchema>
> = {
  'text-embedding-005': commonRef('text-embedding-005'),
  'text-multilingual-embedding-002': commonRef(
    'text-multilingual-embedding-002'
  ),
  'multimodalembedding@001': commonRef('multimodalembedding@001', {
    dimensions: 768,
    supports: { input: ['text', 'image', 'video'] },
  }),
  'gemini-embedding-001': commonRef('gemini-embedding-001', {
    dimensions: 3072,
    supports: { input: ['text'] },
  }),
} as const;

export function embedder(
  version: string,
  config: VertexEmbeddingConfig = {}
): EmbedderReference<ConfigSchema> {
  const name = version.split('/').at(-1);
  if (name && KNOWN_EMBEDDER_MODELS[name]) {
    return embedderRef({
      name: `vertexai/${name}`,
      configSchema: VertexEmbeddingConfigSchema,
      config,
      info: {
        ...KNOWN_EMBEDDER_MODELS[name].info,
      },
    });
  }
  if (config.multimodal) {
    // Generic multimodal embedder format
    return embedderRef({
      name: `vertexai/${name}`,
      configSchema: VertexEmbeddingConfigSchema,
      config,
      info: {
        dimensions: 768,
        supports: { input: ['text', 'image', 'video'] },
      },
    });
  }
  // Generic text-only embedder format
  return embedderRef({
    name: `vertexai/${name}`,
    configSchema: VertexEmbeddingConfigSchema,
    config,
    info: {
      dimensions: 3072,
      supports: { input: ['text'] },
    },
  });
}

export function defineVertexAIEmbedder(
  ai: Genkit,
  name: string,
  clientOptions: ClientOptions
): EmbedderAction<any> {
  const apiModelName = name.startsWith('vertexai/')
    ? name.substring('vertexai/'.length)
    : name;

  const ref = embedder(apiModelName);

  return ai.defineEmbedder(
    {
      name: ref.name,
      configSchema: ref.configSchema,
      info: ref.info!,
    },
    async (input, options?: VertexEmbeddingConfig) => {
      const embedContentRequest: EmbedContentRequest = {
        instances: input.map((doc: Document) =>
          toEmbeddingInstance(ref, doc, options)
        ),
        parameters: { outputDimensionality: options?.outputDimensionality },
      };

      const response = await embedContent(
        apiModelName,
        embedContentRequest,
        clientOptions
      );

      return {
        embeddings: response.predictions
          .map(toEmbeddingResult)
          .reduce((accumulator, value) => {
            return accumulator.concat(value);
          }, []),
      };
    }
  );
}

function toEmbeddingInstance(
  embedder: EmbedderReference<ConfigSchema>,
  doc: Document,
  options?: VertexEmbeddingConfig
): EmbeddingInstance {
  let instance: EmbeddingInstance;
  if (
    isMultiModalEmbedder(embedder) ||
    embedder.config?.multimodal ||
    options?.multimodal
  ) {
    instance = {};
    if (doc.text) {
      instance.text = doc.text;
    }
    for (var media of doc.media) {
      if (
        isObject(media) &&
        typeof media.url === 'string' &&
        typeof media.contentType === 'string'
      ) {
        if (media.contentType?.startsWith('image/')) {
          if (media.url.startsWith('http') || media.url.startsWith('gs://')) {
            instance.image = {
              gcsUri: media.url,
              mimeType: media.contentType,
            };
          } else {
            instance.image = {
              bytesBase64Encoded: media.url,
              mimeType: media.contentType,
            };
          }
        } else if (media.contentType.startsWith('video/')) {
          if (media.url.startsWith('http') || media.url.startsWith('gs://')) {
            instance.video = {
              gcsUri: media.url,
            };
          } else {
            instance.video = {
              bytesBase64Encoded: media.url,
            };
          }
          if (
            instance.video &&
            doc.metadata &&
            doc.metadata.videoSegmentConfig
          ) {
            instance.video.videoSegmentConfig = doc.metadata.videoSegmentConfig;
          }
        } else {
          throw new Error(`Unsupported contentType: '${media.contentType}`);
        }
      } else {
        // It needs to be a {url:string, contentType:string} object.
        throw new Error('Invalid media specified.');
      }
    }
  } else {
    // Text only embedder
    instance = {
      content: doc.text,
      task_type: options?.taskType,
      title: options?.title,
    };
  }
  return instance;
}

/**
 * Converts an `EmbeddingPrediction` object to an array of `EmbeddingResult` objects.
 *
 * There will only be multiple EmbeddingResult objects in the array if it is a
 * multimodal embedding prediction for a video.
 * A single video gets automatically broken into chunks and an embedding is
 * returned for each chunk. The metadata identifies which chunk of the video
 * it is for.
 *
 * @param prediction The input `EmbeddingPrediction` object.
 * @returns An array of `EmbeddingResult` objects, each representing a different embedding.
 */
function toEmbeddingResult(prediction: EmbeddingPrediction): EmbeddingResult[] {
  if (isMultimodalEmbeddingPrediction(prediction)) {
    const eArray: EmbeddingResult[] = [];
    if (prediction.imageEmbedding?.length) {
      const imageResult: EmbeddingResult = {
        embedding: prediction.imageEmbedding,
        metadata: { embedType: 'imageEmbedding' },
      };
      eArray.push(imageResult);
    }
    if (prediction.textEmbedding?.length) {
      const textResult: EmbeddingResult = {
        embedding: prediction.textEmbedding,
        metadata: { embedType: 'textEmbedding' },
      };
      eArray.push(textResult);
    }
    if (prediction.videoEmbeddings?.length) {
      for (const ve of prediction.videoEmbeddings) {
        if (ve.embedding?.length) {
          const { embedding, ...metadata } = ve;
          (metadata as Record<string, unknown>).embedType = 'videoEmbedding';
          const videoResult: EmbeddingResult = {
            embedding,
            metadata,
          };
          eArray.push(videoResult);
        }
      }
    }
    return eArray;
  } else {
    // Text-only embedding
    return [
      {
        embedding: prediction.embeddings.values,
      },
    ];
  }
}

function isMultiModalEmbedder(
  embedder: EmbedderReference<ConfigSchema>
): boolean {
  if (embedder.config?.multimodal) {
    return true;
  }
  const input = embedder.info?.supports?.input || '';
  return (input.includes('text') && input.includes('image')) || false;
}
