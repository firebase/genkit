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

import {
  defineCompatOpenAISpeechModel,
  defineCompatOpenAITranscriptionModel,
} from '../audio.js';
import { defineCompatOpenAIEmbedder } from '../embedder.js';
import { defineCompatOpenAIImageModel } from '../image.js';
import openAICompatible, { PluginOptions } from '../index.js';
import { defineCompatOpenAIModel } from '../model.js';
import { SUPPORTED_IMAGE_MODELS, dallE3 } from './dalle.js';
import {
  SUPPORTED_EMBEDDING_MODELS,
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
  o1,
  o1Mini,
  o1Preview,
  o3,
  o3Mini,
  o4Mini,
} from './gpt.js';
import { SUPPORTED_TTS_MODELS, gpt4oMiniTts, tts1, tts1Hd } from './tts.js';
import { SUPPORTED_STT_MODELS, gpt4oTranscribe, whisper1 } from './whisper.js';
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

export type OpenAIPluginOptions = Exclude<PluginOptions, 'name'>;

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
 *    openai()
 *    ... // other plugins
 *  ]
 * });
 * ```
 */
export const openAI = (options?: OpenAIPluginOptions) =>
  openAICompatible({
    name: 'openai',
    ...options,
    initializer: async (ai, client) => {
      Object.values(SUPPORTED_GPT_MODELS).forEach((modelRef) =>
        defineCompatOpenAIModel({ ai, name: modelRef.name, client, modelRef })
      );
      Object.values(SUPPORTED_EMBEDDING_MODELS).forEach((embedderRef) =>
        defineCompatOpenAIEmbedder({
          ai,
          name: embedderRef.name,
          client,
          embedderRef,
        })
      );
      Object.values(SUPPORTED_TTS_MODELS).forEach((modelRef) =>
        defineCompatOpenAISpeechModel({
          ai,
          name: modelRef.name,
          client,
          modelRef,
        })
      );
      Object.values(SUPPORTED_STT_MODELS).forEach((modelRef) =>
        defineCompatOpenAITranscriptionModel({
          ai,
          name: modelRef.name,
          client,
          modelRef,
        })
      );
      Object.values(SUPPORTED_IMAGE_MODELS).forEach((modelRef) =>
        defineCompatOpenAIImageModel({
          ai,
          name: modelRef.name,
          client,
          modelRef,
        })
      );
    },
  });

export default openAI;
