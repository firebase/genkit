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
import { Document, Genkit } from 'genkit';
import { EmbedRequest, EmbedResponse } from 'ollama';
import { DefineOllamaEmbeddingParams, RequestHeaders } from './types.js';

/**
 * Constructs an Ollama embedding request from the provided parameters.
 * @param {string} modelName - The name of the Ollama model to use
 * @param {number} dimensions - The number of dimensions for the embeddings
 * @param {Document[]} documents - The documents to embed
 * @param {string} serverAddress - The Ollama server address
 * @param {RequestHeaders} [requestHeaders] - Optional headers to include with the request
 * @returns {Promise<{url: string, requestPayload: EmbedRequest, headers: Record<string, string>}>} The prepared request
 * @private
 */
async function toOllamaEmbedRequest(
  modelName: string,
  dimensions: number,
  documents: Document[],
  serverAddress: string,
  requestHeaders?: RequestHeaders
): Promise<{
  url: string;
  requestPayload: EmbedRequest;
  headers: Record<string, string>;
}> {
  const requestPayload: EmbedRequest = {
    model: modelName,
    input: documents.map((doc) => doc.text),
  };

  // Determine headers
  const extraHeaders = requestHeaders
    ? typeof requestHeaders === 'function'
      ? await requestHeaders({
          serverAddress,
          model: {
            name: modelName,
            dimensions,
          },
          embedRequest: requestPayload,
        })
      : requestHeaders
    : {};

  const headers = {
    'Content-Type': 'application/json',
    ...extraHeaders, // Add any dynamic headers
  };

  return {
    url: `${serverAddress}/api/embed`,
    requestPayload,
    headers,
  };
}

/**
 * Defines and registers an Ollama embedder in the Genkit environment.
 * @param {Genkit} ai - The Genkit instance
 * @param {DefineOllamaEmbeddingParams} params - Configuration for the embedder
 * @returns {Embedder} The defined Genkit embedder
 */
export function defineOllamaEmbedder(
  ai: Genkit,
  { name, modelName, dimensions, options }: DefineOllamaEmbeddingParams
) {
  return ai.defineEmbedder(
    {
      name: `ollama/${name}`,
      info: {
        label: 'Ollama Embedding - ' + name,
        dimensions,
        supports: {
          //  TODO: do any ollama models support other modalities?
          input: ['text'],
        },
      },
    },
    async (input, config) => {
      const serverAddress = config?.serverAddress || options.serverAddress;

      const { url, requestPayload, headers } = await toOllamaEmbedRequest(
        modelName,
        dimensions,
        input,
        serverAddress,
        options.requestHeaders
      );

      const response: Response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestPayload),
      });

      if (!response.ok) {
        throw new Error(
          `Error fetching embedding from Ollama: ${response.statusText}`
        );
      }

      const payload: EmbedResponse = await response.json();

      const embeddings: { embedding: number[] }[] = [];

      for (const embedding of payload.embeddings) {
        embeddings.push({ embedding });
      }
      return { embeddings };
    }
  );
}
