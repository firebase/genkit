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
import {
  GenerationCommonConfigSchema,
  ModelInfo,
  modelRef,
} from 'genkit/model';

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

export const TRANSCRIPTION_MODEL_INFO = {
  supports: {
    media: true,
    output: ['text', 'json'],
    multiturn: false,
    systemRole: false,
    tools: false,
  },
};

function commonRef(
  name: string,
  info?: ModelInfo
): ModelReference<typeof TranscriptionConfigSchema> {
  return modelRef({
    name,
    configSchema: TranscriptionConfigSchema,
    info: info ?? TRANSCRIPTION_MODEL_INFO,
  });
}

export const SUPPORTED_STT_MODELS = {
  'gpt-4o-transcribe': commonRef('openai/gpt-4o-transcribe'),
  'whisper-1': commonRef('openai/whisper-1'),
};
