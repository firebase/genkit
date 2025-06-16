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
import { GenerationCommonConfigSchema, z } from 'genkit';
import type { ModelAction } from 'genkit/model';
import { modelRef } from 'genkit/model';
import type OpenAI from 'openai';
import { toGenerateResponse, toImageGenerateParams } from '../image';

export const DallE3ConfigSchema = GenerationCommonConfigSchema.extend({
  size: z.enum(['1024x1024', '1792x1024', '1024x1792']).optional(),
  style: z.enum(['vivid', 'natural']).optional(),
  user: z.string().optional(),
  quality: z.enum(['standard', 'hd']).optional(),
  response_format: z.enum(['b64_json', 'url']).optional(),
});

export const dallE3 = modelRef({
  name: 'openai/dall-e-3',
  info: {
    label: 'OpenAI - DALL-E 3',
    supports: {
      media: false,
      output: ['media'],
      multiturn: false,
      systemRole: false,
      tools: false,
    },
  },
  configSchema: DallE3ConfigSchema,
});

export function dallE3Model(
  ai: Genkit,
  client: OpenAI
): ModelAction<typeof DallE3ConfigSchema> {
  return ai.defineModel<typeof DallE3ConfigSchema>(
    {
      name: dallE3.name,
      ...dallE3.info,
      configSchema: dallE3.configSchema,
    },
    async (request) => {
      const result = await client.images.generate(
        toImageGenerateParams({ model: 'dall-e-3', ...request })
      );
      return toGenerateResponse(result);
    }
  );
}
