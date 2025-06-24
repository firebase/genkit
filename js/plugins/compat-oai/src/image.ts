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
import type {
  GenerateRequest,
  GenerateResponseData,
  Genkit,
  ModelReference,
} from 'genkit';
import { Message, z } from 'genkit';
import { ModelAction } from 'genkit/model';
import OpenAI from 'openai';
import type {
  ImageGenerateParams,
  ImagesResponse,
} from 'openai/resources/images.mjs';

function toImageGenerateParams(
  modelName: string,
  request: GenerateRequest
): ImageGenerateParams {
  const {
    temperature,
    version: modelVersion,
    maxOutputTokens,
    stopSequences,
    topK,
    topP,
    response_format,
    ...restOfConfig
  } = request.config ?? {};

  const options: ImageGenerateParams = {
    model: modelVersion ?? modelName,
    prompt: new Message(request.messages[0]).text,
    response_format: response_format || 'b64_json',
    ...restOfConfig,
  };
  for (const k in options) {
    if (options[k] === undefined) {
      delete options[k];
    }
  }
  return options;
}

function toGenerateResponse(result: ImagesResponse): GenerateResponseData {
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

/**
 * Method to define a new Genkit Model that is compatible with Open AI
 * Images API. 
 *
 * These models are to be used to create images from a user prompt.
 *
 * @param params An object containing parameters for defining the OpenAI
 * image model.
 * @param params.ai The Genkit AI instance.
 * @param params.name The name of the model.
 * @param params.client The OpenAI client instance.
 * @param params.modelRef Optional reference to the model's configuration and
 * custom options.

 * @returns the created {@link ModelAction}
 */
export function defineCompatOpenAIImageModel<
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(params: {
  ai: Genkit;
  name: string;
  client: OpenAI;
  modelRef?: ModelReference<CustomOptions>;
}): ModelAction<CustomOptions> {
  const { ai, name, client, modelRef } = params;
  const model = name.split('/').pop();

  return ai.defineModel(
    {
      name,
      ...modelRef?.info,
      configSchema: modelRef?.configSchema,
    },
    async (request) => {
      const result = await client.images.generate(
        toImageGenerateParams(model!, request)
      );
      return toGenerateResponse(result);
    }
  );
}
