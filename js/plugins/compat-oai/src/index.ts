/**
 * Copyright 2024 The Fire Company
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
import type { Genkit } from 'genkit';
import { genkitPlugin } from 'genkit/plugin';
import { ClientOptions, OpenAI } from 'openai';

import { ModelInfo } from 'genkit/model';
import { dallE3, dallE3Model } from './dalle.js';
import {
  SUPPORTED_EMBEDDING_MODELS,
  openaiEmbedder,
  textEmbedding3Large,
  textEmbedding3Small,
  textEmbeddingAda002,
} from './embedder.js';
import {
  SUPPORTED_GPT_MODELS,
  gpt35Turbo,
  gpt4,
  gpt41,
  gpt41Mini,
  gpt41Nano,
  gpt45,
  gpt4Turbo,
  gpt4Vision,
  gpt4o,
  gpt4oMini,
  gptModel,
  o1,
  o1Mini,
  o1Preview,
  o3,
  o3Mini,
  o4Mini,
} from './gpt.js';
import {
  SUPPORTED_TTS_MODELS,
  gpt4oMiniTts,
  tts1,
  tts1Hd,
  ttsModel,
} from './tts.js';
import {
  SUPPORTED_STT_MODELS,
  gpt4oTranscribe,
  sttModel,
  whisper1,
} from './whisper.js';
export {
  dallE3,
  gpt35Turbo,
  gpt4,
  gpt41,
  gpt41Mini,
  gpt41Nano,
  gpt45,
  gpt4Turbo,
  gpt4Vision,
  gpt4o,
  gpt4oMini,
  gpt4oMiniTts,
  gpt4oTranscribe,
  o1,
  o1Mini,
  o1Preview,
  o3,
  o3Mini,
  o4Mini,
  textEmbedding3Large,
  textEmbedding3Small,
  textEmbeddingAda002,
  tts1,
  tts1Hd,
  whisper1,
};

export interface PluginOptions extends Partial<ClientOptions> {
  models?: ModelDefinition[];
}

// Standard model definition
export interface ModelDefinition {
  name: string;
  info: ModelInfo;
  configSchema?: any;
}

/**
 * This module provides an interface to the OpenAI models through the Genkit
 * plugin system. It allows users to interact with various models by providing
 * an API key and optional configuration.
 *
 * The main export is the `openai` plugin, which can be configured with an API
 * key either directly or through environment variables. It initializes the
 * OpenAI client and makes available the models for use.
 *
 * Exports:
 * - gpt4o: Reference to the GPT-4o model.
 * - gpt4oMini: Reference to the GPT-4o-mini model.
 * - gpt4Turbo: Reference to the GPT-4 Turbo model.
 * - gpt4Vision: Reference to the GPT-4 Vision model.
 * - gpt4: Reference to the GPT-4 model.
 * - gpt35Turbo: Reference to the GPT-3.5 Turbo model.
 * - dallE3: Reference to the DALL-E 3 model.
 * - tts1: Reference to the Text-to-speech 1 model.
 * - tts1Hd: Reference to the Text-to-speech 1 HD model.
 * - whisper: Reference to the Whisper model.
 * - textEmbedding3Large: Reference to the Text Embedding Large model.
 * - textEmbedding3Small: Reference to the Text Embedding Small model.
 * - textEmbeddingAda002: Reference to the Ada model.
 * - openai: The main plugin function to interact with OpenAI.
 *
 * Usage:
 * To use the models, initialize the openai plugin inside `configureGenkit` and
 * pass the configuration options. If no API key is provided in the options, the
 * environment variable `OPENAI_API_KEY` must be set.
 *
 * Example:
 * ```
 * import openai from 'genkitx-openai';
 *
 * export default configureGenkit({
 *  plugins: [
 *    openai({ apiKey: 'your-api-key' })
 *    ... // other plugins
 *  ]
 * });
 * ```
 */
export const openAI = (options?: PluginOptions) =>
  genkitPlugin('openai', async (ai: Genkit) => {
    const client = new OpenAI(options);
    for (const name of Object.keys(SUPPORTED_GPT_MODELS)) {
      gptModel(ai, name, client);
    }
    // Initialize the models if provided in the options
    options?.models?.map((model) => {
      if (!model.name || !model.info || !model.configSchema) {
        throw new Error(`Model ${model.name} is missing required fields`);
      }
      gptModel(ai, model.name, client, model.info, model.configSchema);
    });

    dallE3Model(ai, client);
    for (const name of Object.keys(SUPPORTED_STT_MODELS)) {
      sttModel(ai, name, client);
    }
    for (const name of Object.keys(SUPPORTED_TTS_MODELS)) {
      ttsModel(ai, name, client);
    }
    for (const name of Object.keys(SUPPORTED_EMBEDDING_MODELS)) {
      openaiEmbedder(ai, name, options);
    }
  });

export default openAI;
