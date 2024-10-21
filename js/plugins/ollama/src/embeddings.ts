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
import { GenerateRequest } from '@genkit-ai/ai';
import { defineEmbedder } from '@genkit-ai/ai/embedder';
import { Document } from '@genkit-ai/ai/retriever';
import { logger } from '@genkit-ai/core/logging';
import z from 'zod';
import { OllamaPluginParams } from './index.js';
// Define the schema for Ollama embedding configuration
export const OllamaEmbeddingConfigSchema = z
  .object({
    serverAddress: z.string().optional(),
  })
  .passthrough();

export type EmbeddingModelDefinition = { name: string; dimensions: number };

export type OllamaEmbeddingConfig = z.infer<typeof OllamaEmbeddingConfigSchema>;

// Define the structure of the request and response for embedding
interface OllamaEmbeddingPrediction {
  embedding: number[];
}

interface DefineOllamaEmbeddingParams {
  name: string;
  modelName: string;
  dimensions: number;
  options: OllamaPluginParams;
}

type RequestHeaders =
  | Record<string, string>
  | ((
      params: { serverAddress: string; model: EmbeddingModelDefinition },
      request: GenerateRequest
    ) => Promise<Record<string, string> | void>);

/**
 * Helper function to create the Ollama embed request and headers.
 */
async function toOllamaEmbedRequest(
  modelName: string,
  document: Document,
  serverAddress: string,
  requestHeaders?: Record<string, string> | ((params: any, request: any) => any)
): Promise<{
  url: string;
  requestPayload: any;
  headers: Record<string, string>;
}> {
  const requestPayload = {
    model: modelName,
    prompt: document.text(),
  };

  // Determine headers
  const extraHeaders = requestHeaders
    ? typeof requestHeaders === 'function'
      ? await requestHeaders(
          {
            serverAddress,
            modelName,
          },
          document
        )
      : requestHeaders
    : {};

  const headers = {
    'Content-Type': 'application/json',
    ...extraHeaders, // Add any dynamic headers
  };

  return {
    url: `${serverAddress}/api/embeddings`,
    requestPayload,
    headers,
  };
}

export function defineOllamaEmbedder({
  name,
  modelName,
  dimensions,
  options,
}: DefineOllamaEmbeddingParams) {
  return defineEmbedder(
    {
      name: `ollama/${name}`,
      configSchema: OllamaEmbeddingConfigSchema, // Use the Zod schema directly here
      info: {
        label: 'Ollama Embedding - ' + name,
        dimensions,
        supports: {
          input: ['text'],
        },
      },
    },
    async (input, config) => {
      const serverAddress = config?.serverAddress || options.serverAddress;

      const responses = await Promise.all(
        input.map(async (doc) => {
          // Generate the request and headers using the helper function
          const { url, requestPayload, headers } = await toOllamaEmbedRequest(
            modelName,
            doc,
            serverAddress,
            options.requestHeaders
          );

          let res: Response;
          try {
            res = await fetch(url, {
              method: 'POST',
              headers,
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
