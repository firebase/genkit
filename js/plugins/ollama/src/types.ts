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

// Define possible API types
export type ApiType = 'chat' | 'generate';

// Standard model definition - removed format
export interface ModelDefinition {
  name: string;
  type?: ApiType;
}

// Definition for embedding models
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

export interface DefineOllamaEmbeddingParams {
  name: string;
  modelName: string;
  dimensions: number;
  options: OllamaPluginParams;
}

// Parameters for the Ollama plugin configuration
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

// Function type for generating request headers dynamically
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
