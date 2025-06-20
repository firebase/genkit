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

import { z } from 'genkit';
import { GenerationCommonConfigSchema, modelRef } from 'genkit/model';

const ChunkingStrategySchema = z.object({
  type: z.string(),
  prefix_padding_ms: z.number().int().optional(),
  silence_duration_ms: z.number().int().optional(),
  threshold: z.number().min(0).max(1.0).optional(),
});
export const TranscriptionConfigSchema = GenerationCommonConfigSchema.pick({
  temperature: true,
}).extend({
  chunking_strategy: z
    .union([z.literal('auto'), ChunkingStrategySchema])
    .optional(),
  include: z.array(z.any()).optional(),
  language: z.string().optional(),
  timestamp_granularities: z.array(z.enum(['word', 'segment'])).optional(),
  response_format: z
    .enum(['json', 'text', 'srt', 'verbose_json', 'vtt'])
    .optional(),
  // TODO stream support
});

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
  configSchema: TranscriptionConfigSchema,
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
  configSchema: TranscriptionConfigSchema,
});

export const SUPPORTED_STT_MODELS = {
  'gpt-4o-transcribe': gpt4oTranscribe,
  'whisper-1': whisper1,
};
