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

import { GenerateRequest, z } from 'genkit';
import {
  ChatResponse,
  EmbedRequest,
  GenerateResponse,
  Message as OllamaMessage,
} from 'ollama';

/**
 * Represents the type of API endpoint to use when communicating with Ollama.
 * Can be either 'chat' for conversational models or 'generate' for completion models.
 */
export type ApiType = 'chat' | 'generate';

/**
 * Configuration for defining an Ollama model.
 * @interface ModelDefinition
 * @property {string} name - The name of the Ollama model to use
 * @property {ApiType} [type] - Optional API type to use. Defaults to 'chat' if not specified
 */
export interface ModelDefinition {
  name: string;
  type?: ApiType;
}

/**
 * Configuration for defining an Ollama embedding model.
 * @interface EmbeddingModelDefinition
 * @property {string} name - The name of the Ollama embedding model
 * @property {number} dimensions - The number of dimensions in the embedding output
 */
export interface EmbeddingModelDefinition {
  name: string;
  dimensions: number;
}

export const OllamaEmbeddingPredictionSchema = z.object({
  embedding: z.array(z.number()),
});

export type OllamaEmbeddingPrediction = z.infer<
  typeof OllamaEmbeddingPredictionSchema
>;

/**
 * Parameters for defining an Ollama embedder.
 * @interface DefineOllamaEmbeddingParams
 * @property {string} name - The name to use for the embedder
 * @property {string} modelName - The name of the Ollama model to use
 * @property {number} dimensions - The number of dimensions in the embedding output
 * @property {OllamaPluginParams} options - Configuration options for the embedder
 */
export interface DefineOllamaEmbeddingParams {
  name: string;
  modelName: string;
  dimensions: number;
  options: OllamaPluginParams;
}

/**
 * Configuration options for the Ollama plugin.
 * @interface OllamaPluginParams
 * @property {ModelDefinition[]} [models] - Array of model definitions to register
 * @property {EmbeddingModelDefinition[]} [embedders] - Array of embedding model definitions to register
 * @property {string} serverAddress - The base URL of the Ollama server
 * @property {RequestHeaders} [requestHeaders] - Optional headers to include with requests
 */
export interface OllamaPluginParams {
  /**
   * Array of models to be defined.
   */
  models?: ModelDefinition[];

  /**
   * Array of embedding models to be defined.
   */
  embedders?: EmbeddingModelDefinition[];

  /**
   * The address of the Ollama server.
   */
  serverAddress: string;

  /**
   * Optional request headers, which can be either static or dynamically generated.
   */
  requestHeaders?: RequestHeaders;
}

/**
 * Function for dynamically generating request headers.
 * @callback RequestHeaderFunction
 * @param {Object} params - Parameters for generating headers
 * @param {string} params.serverAddress - The Ollama server address
 * @param {ModelDefinition | EmbeddingModelDefinition} params.model - The model being used
 * @param {GenerateRequest} [params.modelRequest] - The generation request (if applicable)
 * @param {EmbedRequest} [params.embedRequest] - The embedding request (if applicable)
 * @param {GenerateRequest} [modelRequest] - @deprecated Legacy parameter for backwards compatibility
 * @returns {Promise<Record<string, string> | void>} The headers to include with the request
 */
export interface RequestHeaderFunction {
  (
    params: {
      serverAddress: string;
      model: ModelDefinition | EmbeddingModelDefinition;
      modelRequest?: GenerateRequest;
      embedRequest?: EmbedRequest;
    },
    // @deprecated -- moved into params, here for backwards compatibility reasons.
    modelRequest?: GenerateRequest
  ): Promise<Record<string, string> | void>;
}

// Union type for request headers, supporting both static and dynamic options
export type RequestHeaders = Record<string, string> | RequestHeaderFunction;

// Use Ollama's Message type
export type { OllamaMessage as Message };

// Export response types from Ollama
export type { ChatResponse, GenerateResponse };
