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

import { Genkit, z } from 'genkit';
import {
  CandidateData,
  GenerateRequest,
  GenerationCommonConfigSchema,
  ModelAction,
  ModelReference,
  getBasicUsageStats,
  modelRef,
} from 'genkit/model';
import { GoogleAuth } from 'google-auth-library';
import { PluginOptions } from './common/types.js';
import { PredictClient, predictModel } from './predict.js';

const ImagenConfigSchema = GenerationCommonConfigSchema.extend({
  /** Language of the prompt text. */
  language: z
    .enum(['auto', 'en', 'es', 'hi', 'ja', 'ko', 'pt', 'zh-TW', 'zh', 'zh-CN'])
    .optional(),
  /** Desired aspect ratio of output image. */
  aspectRatio: z.enum(['1:1', '9:16', '16:9', '3:4', '4:3']).optional(),
  /**
   * A negative prompt to help generate the images. For example: "animals"
   * (removes animals), "blurry" (makes the image clearer), "text" (removes
   * text), or "cropped" (removes cropped images).
   **/
  negativePrompt: z.string().optional(),
  /**
   * Any non-negative integer you provide to make output images deterministic.
   * Providing the same seed number always results in the same output images.
   * Accepted integer values: 1 - 2147483647.
   **/
  seed: z.number().optional(),
  /** Your GCP project's region. e.g.) us-central1, europe-west2, etc. **/
  location: z.string().optional(),
  /** Allow generation of people by the model. */
  personGeneration: z
    .enum(['dont_allow', 'allow_adult', 'allow_all'])
    .optional(),
  /** Adds a filter level to safety filtering. */
  safetySetting: z
    .enum(['block_most', 'block_some', 'block_few', 'block_fewest'])
    .optional(),
  /** Add an invisible watermark to the generated images. */
  addWatermark: z.boolean().optional(),
  /** Cloud Storage URI to store the generated images. **/
  storageUri: z.string().optional(),
  /** Mode must be set for upscaling requests. */
  mode: z.enum(['upscale']).optional(),
  /**
   * Describes the editing intention for the request.
   *
   * Refer to https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/imagen-api#edit_images_2 for details.
   */
  editConfig: z
    .object({
      /** Describes the editing intention for the request. */
      editMode: z
        .enum([
          'inpainting-insert',
          'inpainting-remove',
          'outpainting',
          'product-image',
        ])
        .optional(),
      /** Prompts the model to generate a mask instead of you needing to provide one. Consequently, when you provide this parameter you can omit a mask object. */
      maskMode: z
        .object({
          maskType: z.enum(['background', 'foreground', 'semantic']),
          classes: z.array(z.number()).optional(),
        })
        .optional(),
      maskDilation: z.number().optional(),
      guidanceScale: z.number().optional(),
      productPosition: z.enum(['reposition', 'fixed']).optional(),
    })
    .passthrough()
    .optional(),
  /** Upscale config object. */
  upscaleConfig: z.object({ upscaleFactor: z.enum(['x2', 'x4']) }).optional(),
}).passthrough();

export const imagen2 = modelRef({
  name: 'vertexai/imagen2',
  info: {
    label: 'Vertex AI - Imagen2',
    versions: ['imagegeneration@006', 'imagegeneration@005'],
    supports: {
      media: false,
      multiturn: false,
      tools: false,
      systemRole: false,
      output: ['media'],
    },
  },
  version: 'imagegeneration@006',
  configSchema: ImagenConfigSchema,
});

export const imagen3 = modelRef({
  name: 'vertexai/imagen3',
  info: {
    label: 'Vertex AI - Imagen3',
    versions: ['imagen-3.0-generate-001'],
    supports: {
      media: true,
      multiturn: false,
      tools: false,
      systemRole: false,
      output: ['media'],
    },
  },
  version: 'imagen-3.0-generate-001',
  configSchema: ImagenConfigSchema,
});

export const imagen3Fast = modelRef({
  name: 'vertexai/imagen3-fast',
  info: {
    label: 'Vertex AI - Imagen3 Fast',
    versions: ['imagen-3.0-fast-generate-001'],
    supports: {
      media: false,
      multiturn: false,
      tools: false,
      systemRole: false,
      output: ['media'],
    },
  },
  version: 'imagen-3.0-fast-generate-001',
  configSchema: ImagenConfigSchema,
});

export const SUPPORTED_IMAGEN_MODELS = {
  imagen2: imagen2,
  imagen3: imagen3,
  'imagen3-fast': imagen3Fast,
};

function extractText(request: GenerateRequest) {
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
  personGeneration?: string;
  safetySetting?: string;
  addWatermark?: boolean;
  storageUri?: string;
}

function toParameters(
  request: GenerateRequest<typeof ImagenConfigSchema>
): ImagenParameters {
  const out = {
    sampleCount: request.candidates ?? 1,
    ...request?.config,
  };

  for (const k in out) {
    if (!out[k]) delete out[k];
  }

  return out;
}

function extractMaskImage(request: GenerateRequest): string | undefined {
  return request.messages
    .at(-1)
    ?.content.find((p) => !!p.media && p.metadata?.type === 'mask')
    ?.media?.url.split(',')[1];
}

function extractBaseImage(request: GenerateRequest): string | undefined {
  return request.messages
    .at(-1)
    ?.content.find(
      (p) => !!p.media && (!p.metadata?.type || p.metadata?.type === 'base')
    )
    ?.media?.url.split(',')[1];
}

interface ImagenPrediction {
  bytesBase64Encoded: string;
  mimeType: string;
}

interface ImagenInstance {
  prompt: string;
  image?: { bytesBase64Encoded: string };
  mask?: { image?: { bytesBase64Encoded: string } };
}

export function imagenModel(
  ai: Genkit,
  name: string,
  client: GoogleAuth,
  options: PluginOptions
): ModelAction {
  const modelName = `vertexai/${name}`;
  const model: ModelReference<z.ZodTypeAny> = SUPPORTED_IMAGEN_MODELS[name];
  if (!model) throw new Error(`Unsupported model: ${name}`);

  const predictClients: Record<
    string,
    PredictClient<ImagenInstance, ImagenPrediction, ImagenParameters>
  > = {};
  const predictClientFactory = (
    request: GenerateRequest<typeof ImagenConfigSchema>
  ): PredictClient<ImagenInstance, ImagenPrediction, ImagenParameters> => {
    const requestLocation = request.config?.location || options.location;
    if (!predictClients[requestLocation]) {
      predictClients[requestLocation] = predictModel<
        ImagenInstance,
        ImagenPrediction,
        ImagenParameters
      >(
        client,
        {
          ...options,
          location: requestLocation,
        },
        request.config?.version || model.version || name
      );
    }
    return predictClients[requestLocation];
  };

  return ai.defineModel(
    {
      name: modelName,
      ...model.info,
      configSchema: ImagenConfigSchema,
    },
    async (request) => {
      const instance: ImagenInstance = {
        prompt: extractText(request),
      };
      const baseImage = extractBaseImage(request);
      if (baseImage) {
        instance.image = { bytesBase64Encoded: baseImage };
      }
      const maskImage = extractMaskImage(request);
      if (maskImage) {
        instance.mask = {
          image: { bytesBase64Encoded: maskImage },
        };
      }

      const predictClient = predictClientFactory(request);
      const response = await predictClient([instance], toParameters(request));

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
    }
  );
}
