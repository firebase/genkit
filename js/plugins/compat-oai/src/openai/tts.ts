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
import { ModelReference, z } from 'genkit';
import { ModelInfo, modelRef } from 'genkit/model';

export const SpeechConfigSchema = z.object({
  voice: z
    .enum(['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'])
    .default('alloy'),
  speed: z.number().min(0.25).max(4.0).optional(),
  response_format: z
    .enum(['mp3', 'opus', 'aac', 'flac', 'wav', 'pcm'])
    .optional(),
});

export const SPEECH_MODEL_INFO: ModelInfo = {
  supports: {
    media: false,
    output: ['media'],
    multiturn: false,
    systemRole: false,
    tools: false,
  },
};

function commonRef<CustomOptions extends z.ZodTypeAny = z.ZodTypeAny>(
  name: string,
  configSchema: CustomOptions,
  info?: ModelInfo
): ModelReference<CustomOptions> {
  return modelRef<typeof configSchema>({
    name,
    configSchema: configSchema ?? SpeechConfigSchema,
    info: info ?? SPEECH_MODEL_INFO,
  });
}

export const SUPPORTED_TTS_MODELS = {
  'tts-1': commonRef('openai/tts-1', SpeechConfigSchema),
  'tts-1-hd': commonRef('openai/tts-1-hd', SpeechConfigSchema),
  'gpt-4o-mini-tts': commonRef(
    'openai/gpt-4o-mini-tts',
    SpeechConfigSchema.omit({ speed: true })
  ),
};
