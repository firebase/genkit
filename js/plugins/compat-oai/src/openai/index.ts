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
import { SUPPORTED_IMAGE_MODELS } from './dalle.js';
import { SUPPORTED_EMBEDDING_MODELS } from './embedder.js';
import { SUPPORTED_GPT_MODELS } from './gpt.js';
import { SUPPORTED_TTS_MODELS } from './tts.js';
import { SUPPORTED_STT_MODELS } from './whisper.js';

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
