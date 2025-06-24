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
import { ModelInfo, modelRef } from 'genkit/model';

export const ImageGenerationConfigSchema = z.object({
  size: z.enum(['1024x1024', '1792x1024', '1024x1792']).optional(),
  style: z.enum(['vivid', 'natural']).optional(),
  user: z.string().optional(),
  n: z.number().int().min(1).max(10).default(1),
  quality: z.enum(['standard', 'hd']).optional(),
  response_format: z.enum(['b64_json', 'url']).optional(),
});

export const IMAGE_GENERATION_MODEL_INFO: ModelInfo = {
  supports: {
    media: false,
    output: ['media'],
    multiturn: false,
    systemRole: false,
    tools: false,
  },
};

export const dallE3 = modelRef({
  name: 'openai/dall-e-3',
  info: {
    label: 'OpenAI - DALL-E 3',
    ...IMAGE_GENERATION_MODEL_INFO,
  },
  configSchema: ImageGenerationConfigSchema,
});

export const SUPPORTED_IMAGE_MODELS = {
  'dall-e-3': dallE3,
};
