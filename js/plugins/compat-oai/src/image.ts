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
import type { GenerateResponseData } from 'genkit';
import { Message, z } from 'genkit';
import { GenerateRequestSchema } from 'genkit/model';
import type {
  ImageGenerateParams,
  ImagesResponse,
} from 'openai/resources/images.mjs';

export const ImageGenerateRequestSchema = GenerateRequestSchema.extend({
  model: z.string(),
  n: z.number().optional().describe('Number of images to generate'),
});
export type ImageGenerateRequest = z.infer<typeof ImageGenerateRequestSchema>;

export function toImageGenerateParams(
  request: ImageGenerateRequest
): ImageGenerateParams {
  const options: ImageGenerateParams = {
    model: request.model,
    prompt: new Message(request.messages[0]).text,
    n: request.n || 1,
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

export function toGenerateResponse(
  result: ImagesResponse
): GenerateResponseData {
  const images = result.data;
  if (!images) {
    return { finishReason: 'stop' };
  } else {
    const content = (result.data ?? []).map((image) => ({
      media: {
        contentType: 'image/png',
        url: image.url || `data:image/png;base64,${image.b64_json}`,
      },
    }));
    return { message: { role: 'model', content } };
  }
}
