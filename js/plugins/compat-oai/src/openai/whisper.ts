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
import { Whisper1ConfigSchema, sttModel as compatSttModel } from '../audio';

export const whisper1 = modelRef({
  name: 'openai/whisper-1',
  info: {
    label: 'OpenAI - Whisper',
    supports: {
      media: true,
      output: ['text', 'json'],
      multiturn: false,
      systemRole: false,
      tools: false,
    },
  },
  configSchema: Whisper1ConfigSchema,
});

export const gpt4oTranscribe = modelRef({
  name: 'openai/gpt-4o-transcribe',
  info: {
    label: 'OpenAI - GPT-4o Transcribe',
    supports: {
      media: true,
      output: ['text', 'json'],
      multiturn: false,
      systemRole: false,
      tools: false,
    },
  },
  configSchema: Whisper1ConfigSchema,
});

export const SUPPORTED_STT_MODELS = {
  'gpt-4o-transcribe': gpt4oTranscribe,
  'whisper-1': whisper1,
};

export function sttModel(
  ai: Genkit,
  name: string,
  client: OpenAI
): ModelAction<typeof Whisper1ConfigSchema> {
  const modelId = `openai/${name}`;
  const model = SUPPORTED_STT_MODELS[name];
  if (!model) throw new Error(`Unsupported model: ${name}`);

  return compatSttModel(ai, modelId, client, model);
}
