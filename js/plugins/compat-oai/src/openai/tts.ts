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
import type { ModelAction } from 'genkit/model';
import { modelRef } from 'genkit/model';
import type OpenAI from 'openai';
import { TTSConfigSchema, ttsModel as compatTtsModel } from '../audio';

export const tts1 = modelRef({
  name: 'openai/tts-1',
  info: {
    label: 'OpenAI - Text-to-speech 1',
    supports: {
      media: false,
      output: ['media'],
      multiturn: false,
      systemRole: false,
      tools: false,
    },
  },
  configSchema: TTSConfigSchema,
});

export const tts1Hd = modelRef({
  name: 'openai/tts-1-hd',
  info: {
    label: 'OpenAI - Text-to-speech 1 HD',
    supports: {
      media: false,
      output: ['media'],
      multiturn: false,
      systemRole: false,
      tools: false,
    },
  },
  configSchema: TTSConfigSchema,
});

export const gpt4oMiniTts = modelRef({
  name: 'openai/gpt-4o-mini-tts',
  info: {
    label: 'OpenAI - GPT-4o Mini Text-to-speech',
    supports: {
      media: false,
      output: ['media'],
      multiturn: false,
      systemRole: false,
      tools: false,
    },
  },
  configSchema: TTSConfigSchema,
});

export const SUPPORTED_TTS_MODELS = {
  'tts-1': tts1,
  'tts-1-hd': tts1Hd,
  'gpt-4o-mini-tts': gpt4oMiniTts,
};

export function ttsModel(
  ai: Genkit,
  name: string,
  client: OpenAI
): ModelAction<typeof TTSConfigSchema> {
  const modelId = `openai/${name}`;
  const model = SUPPORTED_TTS_MODELS[name];
  if (!model) throw new Error(`Unsupported model: ${name}`);

  return compatTtsModel(ai, modelId, client, model);
}
