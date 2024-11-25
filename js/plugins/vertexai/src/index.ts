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

import { Genkit } from 'genkit';
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';
import { getDerivedParams } from './common/index.js';
import { PluginOptions } from './common/types.js';
import {
  SUPPORTED_EMBEDDER_MODELS,
  defineVertexAIEmbedder,
  textEmbedding004,
  textEmbeddingGecko003,
  textEmbeddingGeckoMultilingual001,
  textMultilingualEmbedding002,
} from './embedder.js';
import {
  SUPPORTED_GEMINI_MODELS,
  defineGeminiModel,
  gemini10Pro,
  gemini15Flash,
  gemini15Pro,
} from './gemini.js';
import {
  SUPPORTED_IMAGEN_MODELS,
  imagen2,
  imagen3,
  imagen3Fast,
  imagenModel,
} from './imagen.js';
export { type PluginOptions } from './common/types.js';
export {
  gemini10Pro,
  gemini15Flash,
  gemini15Pro,
  imagen2,
  imagen3,
  imagen3Fast,
  textEmbedding004,
  textEmbeddingGecko003,
  textEmbeddingGeckoMultilingual001,
  textMultilingualEmbedding002,
};

/**
 * Add Google Cloud Vertex AI to Genkit. Includes Gemini and Imagen models and text embedder.
 */
export function vertexAI(options?: PluginOptions): GenkitPlugin {
  return genkitPlugin('vertexai', async (ai: Genkit) => {
    const { projectId, location, vertexClientFactory, authClient } =
      await getDerivedParams(options);

    Object.keys(SUPPORTED_IMAGEN_MODELS).map((name) =>
      imagenModel(ai, name, authClient, { projectId, location })
    );
    Object.keys(SUPPORTED_GEMINI_MODELS).map((name) =>
      defineGeminiModel(ai, name, vertexClientFactory, { projectId, location })
    );

    Object.keys(SUPPORTED_EMBEDDER_MODELS).map((name) =>
      defineVertexAIEmbedder(ai, name, authClient, { projectId, location })
    );
  });
}

export default vertexAI;
