/**
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
  CandidateData,
  GenerationRequest,
  defineModel,
  getBasicUsageStats,
  modelRef,
} from '@genkit-ai/ai/model';
import { GoogleAuth } from 'google-auth-library';
import z from 'zod';
import { PluginOptions } from '.';
import { predictModel } from './predict';

const ImagenConfigSchema = z.object({
  /** Language of the prompt text. */
  language: z
    .enum(['auto', 'en', 'es', 'hi', 'ja', 'ko', 'pt', 'zh-TW', 'zh', 'zh-CN'])
    .optional(),
  /** Desired aspect ratio of output image. */
  aspectRatio: z.enum(['1:1', '9:16', '16:9']).optional(),
  /** A negative prompt to help generate the images. For example: "animals" (removes animals), "blurry" (makes the image clearer), "text" (removes text), or "cropped" (removes cropped images). */
  negativePrompt: z.string().optional(),
  /** Any non-negative integer you provide to make output images deterministic. Providing the same seed number always results in the same output images. Accepted integer values: 1 - 2147483647. */
  seed: z.number().optional(),
});
type ImagenConfig = z.infer<typeof ImagenConfigSchema>;

export const imagen2 = modelRef({
  name: 'vertex-ai/imagen2',
  info: {
    label: 'Vertex AI - Imagen2',
    supports: {
      media: false,
      multiturn: false,
      tools: false,
      output: ['media'],
    },
  },
  configSchema: ImagenConfigSchema,
});

function extractText(request: GenerationRequest) {
  return request.messages
    .at(-1)!
    .content.map((c) => c.text || '')
    .join('');
}

interface ImagenParameters {
  sampleCount?: number;
  aspectRatio?: string;
  negativePrompt?: string;
  seed?: number;
  language?: string;
}

function toParameters(request: GenerationRequest): ImagenParameters {
  const config = request.config?.custom || ({} as ImagenConfig);

  const out = {
    sampleCount: request.candidates || 1,
    aspectRatio: config.aspectRatio,
    negativePrompt: config.negativePrompt,
    seed: config.seed,
    language: config.language,
  };

  for (const k in out) {
    if (!out[k]) delete out[k];
  }

  return out;
}

function extractPromptImage(request: GenerationRequest): string | undefined {
  return request.messages
    .at(-1)
    ?.content.find((p) => !!p.media)
    ?.media?.url.split(',')[1];
}

interface ImagenPrediction {
  bytesBase64Encoded: string;
  mimeType: string;
}

interface ImagenInstance {
  prompt: string;
  image?: { bytesBase64Encoded: string };
}

/**
 *
 */
export function imagen2Model(client: GoogleAuth, options: PluginOptions) {
  const predict = predictModel<
    ImagenInstance,
    ImagenPrediction,
    ImagenParameters
  >(client, options, 'imagegeneration@005');

  return defineModel(imagen2, async (request) => {
    const instance: ImagenInstance = {
      prompt: extractText(request),
    };
    if (extractPromptImage(request))
      instance.image = { bytesBase64Encoded: extractPromptImage(request)! };

    const req: any = {
      instances: [instance],
      parameters: toParameters(request),
    };

    const response = await predict([instance], toParameters(request));

    const candidates: CandidateData[] = response.predictions.map((p, i) => {
      const b64data = p.bytesBase64Encoded;
      const mimeType = p.mimeType;
      return {
        index: i,
        finishReason: 'stop',
        message: {
          role: 'model',
          content: [
            {
              media: {
                url: `data:${mimeType};base64,${b64data}`,
                contentType: mimeType,
              },
            },
          ],
        },
      };
    });
    return {
      candidates,
      usage: {
        ...getBasicUsageStats(request.messages, candidates),
        custom: { generations: candidates.length },
      },
      custom: response,
    };
  });
}
