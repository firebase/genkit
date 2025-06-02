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
import type { GenerateRequest, GenerateResponseData, Genkit } from 'genkit';
import { GenerationCommonConfigSchema, Message, z } from 'genkit';
import type { ModelAction } from 'genkit/model';
import { modelRef } from 'genkit/model';
import type OpenAI from 'openai';
import type {
  ImageGenerateParams,
  ImagesResponse,
} from 'openai/resources/images.mjs';

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

function toDallE3Request(
  request: GenerateRequest<typeof DallE3ConfigSchema>
): ImageGenerateParams {
  const options = {
    model: 'dall-e-3',
    prompt: new Message(request.messages[0]).text,
    n: request.candidates || 1,
    size: request.config?.size,
    style: request.config?.style,
    user: request.config?.user,
    quality: request.config?.quality,
    response_format: request.config?.response_format || 'b64_json',
  };
  for (const k in options) {
    if (options[k] === undefined) {
      delete options[k];
    }
  }
  return options;
}

function toGenerateResponse(result: ImagesResponse): GenerateResponseData {
  const candidates: GenerateResponseData['candidates'] = (
    result.data ?? []
  ).map((image, index) => ({
    index: index,
    finishReason: 'stop',
    custom: { revisedPrompt: image.revised_prompt },
    message: {
      role: 'model',
      content: [
        {
          media: {
            contentType: 'image/png',
            url: image.url || `data:image/png;base64,${image.b64_json}`,
          },
        },
      ],
    },
  }));
  return { candidates };
}

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
      const result = await client.images.generate(toDallE3Request(request));
      return toGenerateResponse(result);
    }
  );
}
