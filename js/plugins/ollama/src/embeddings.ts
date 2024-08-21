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

import { defineEmbedder } from '@genkit-ai/ai/embedder';
import { logger } from '@genkit-ai/core/logging';
import z from 'zod';
import { OllamaPluginParams } from './index.js';

// Define the schema for Ollama embedding configuration
export const OllamaEmbeddingConfigSchema = z.object({
  modelName: z.string(),
  serverAddress: z.string(),
});
export type OllamaEmbeddingConfig = z.infer<typeof OllamaEmbeddingConfigSchema>;

// Define the structure of the request and response for embedding
interface OllamaEmbeddingInstance {
  content: string;
}

interface OllamaEmbeddingPrediction {
  embedding: number[];
}

interface DefineOllamaEmbeddingParams {
  name: string;
  modelName: string;
  dimensions: number;
  options: OllamaPluginParams;
}

export function defineOllamaEmbedder({
  name,
  modelName,
  dimensions,
  options,
}: DefineOllamaEmbeddingParams) {
  return defineEmbedder(
    {
      name,
      configSchema: OllamaEmbeddingConfigSchema, // Use the Zod schema directly here
      info: {
        // TODO: do we want users to be able to specify the label when they call this method directly?
        label: 'Embedding using Ollama - ' + modelName,
        dimensions,
        supports: {
          //  TODO: do any ollama models support other modalities?
          input: ['text'],
        },
      },
    },
    async (input, _config) => {
      const serverAddress = options.serverAddress;

      const responses = await Promise.all(
        input.map(async (i) => {
          const requestPayload = {
            model: modelName,
            prompt: i.text(),
          };
          let res: Response;
          try {
            console.log('MODEL NAME: ', modelName);
            res = await fetch(`${serverAddress}/api/embeddings`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(requestPayload),
            });
          } catch (e) {
            logger.error('Failed to fetch Ollama embedding');
            throw new Error(`Error fetching embedding from Ollama: ${e}`);
          }

          if (!res.ok) {
            logger.error('Failed to fetch Ollama embedding');
            throw new Error(
              `Error fetching embedding from Ollama: ${res.statusText}`
            );
          }

          const responseData = (await res.json()) as OllamaEmbeddingPrediction;
          return responseData;
        })
      );

      return {
        embeddings: responses,
      };
    }
  );
}
