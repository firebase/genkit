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

import { z } from 'genkit';
import { ModelReference } from 'genkit/model';
import { GoogleAuthOptions } from 'google-auth-library';
import { VertexAIEvaluationMetric } from '../evaluation';
import { VertexRerankerConfig } from '../reranker';
import { VectorSearchOptions } from '../vector-search';

/** Common options for Vertex AI plugin configuration */
export interface CommonPluginOptions {
  /** The Google Cloud project id to call. */
  projectId?: string;
  /** The Google Cloud region to call. */
  location: string;
  /** Provide custom authentication configuration for connecting to Vertex AI. */
  googleAuth?: GoogleAuthOptions;
}

/** Options specific to evaluation configuration */
export interface EvaluationOptions {
  /** Configure Vertex AI evaluators */
  evaluation?: {
    metrics: VertexAIEvaluationMetric[];
  };
}

/** Options specific to Model Garden configuration */
export interface ModelGardenOptions {
  /**
   * @deprecated use `modelGarden.models`
   */
  modelGardenModels?: ModelReference<any>[];
  modelGarden?: {
    models: ModelReference<any>[];
    openAiBaseUrlTemplate?: string;
  };
}

/** Options specific to vector search configuration */
export interface VectorSearchOptionsConfig {
  /** Configure Vertex AI vector search index options */
  vectorSearchOptions?: VectorSearchOptions<z.ZodTypeAny, any, any>[];
}

/** Options specific to reranker configuration */
export interface RerankerOptions {
  /** Configure reranker options */
  rerankOptions?: VertexRerankerConfig[];
}

/** Combined plugin options, extending common options with subplugin-specific options */
export interface PluginOptions
  extends CommonPluginOptions,
    EvaluationOptions,
    ModelGardenOptions,
    VectorSearchOptionsConfig,
    RerankerOptions {}
