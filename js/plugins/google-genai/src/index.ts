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

import { genkitPlugin, Plugin } from '@genkit-ai/core/config';
import {
  SUPPORTED_MODELS as EMBEDDER_MODELS,
  textEmbeddingGeckoEmbedder,
} from './embedder.js';
import {
  SUPPORTED_MODELS as GEMINI_MODELS,
  geminiPro,
  geminiProVision,
  googleAIModel,
} from './gemini.js';
export { geminiPro, geminiProVision };

export interface PluginOptions {
  apiKey?: string;
}

export const googleGenAI: Plugin<PluginOptions[]> = genkitPlugin(
  'google-ai',
  async (options: PluginOptions) => {
    return {
      models: [
        ...Object.keys(GEMINI_MODELS).map((name) =>
          googleAIModel(name, options?.apiKey)
        ),
      ],
      embedders: [
        ...Object.keys(EMBEDDER_MODELS).map((name) =>
          textEmbeddingGeckoEmbedder(name, { apiKey: options?.apiKey })
        ),
      ],
    };
  }
);

export default googleGenAI;
