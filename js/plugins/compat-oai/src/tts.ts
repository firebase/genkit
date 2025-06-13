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
import type { SpeechCreateParams } from 'openai/resources/audio/index.mjs';

export const TTSConfigSchema = GenerationCommonConfigSchema.extend({
  voice: z
    .enum(['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'])
    .optional()
    .default('alloy'),
  speed: z.number().min(0.25).max(4.0).optional(),
  response_format: z
    .enum(['mp3', 'opus', 'aac', 'flac', 'wav', 'pcm'])
    .optional(),
});

export const tts1 = modelRef({
  name: 'openai/tts-1',
  info: {
    label: 'OpenAI - Text-to-speech 1',
    supports: {
      media: false,
      output: ['media'],
      multiturn: false,
      systemRole: false,
      tools: false,
    },
  },
  configSchema: TTSConfigSchema,
});

export const tts1Hd = modelRef({
  name: 'openai/tts-1-hd',
  info: {
    label: 'OpenAI - Text-to-speech 1 HD',
    supports: {
      media: false,
      output: ['media'],
      multiturn: false,
      systemRole: false,
      tools: false,
    },
  },
  configSchema: TTSConfigSchema,
});

export const gpt4oMiniTts = modelRef({
  name: 'openai/gpt-4o-mini-tts',
  info: {
    label: 'OpenAI - GPT-4o Mini Text-to-speech',
    supports: {
      media: false,
      output: ['media'],
      multiturn: false,
      systemRole: false,
      tools: false,
    },
  },
  configSchema: TTSConfigSchema,
});

export const SUPPORTED_TTS_MODELS = {
  'tts-1': tts1,
  'tts-1-hd': tts1Hd,
  'gpt-4o-mini-tts': gpt4oMiniTts,
};

export const RESPONSE_FORMAT_MEDIA_TYPES = {
  mp3: 'audio/mpeg',
  opus: 'audio/opus',
  aac: 'audio/aac',
  flac: 'audio/flac',
  wav: 'audio/wav',
  pcm: 'audio/L16',
};

function toTTSRequest(
  modelName: string,
  request: GenerateRequest<typeof TTSConfigSchema>
): SpeechCreateParams {
  const mappedModelName = request.config?.version || modelName;
  const options: SpeechCreateParams = {
    model: mappedModelName,
    input: new Message(request.messages[0]).text,
    voice: request.config?.voice ?? 'alloy',
    speed: request.config?.speed,
    response_format: request.config?.response_format,
  };
  for (const k in options) {
    if (options[k] === undefined) {
      delete options[k];
    }
  }
  return options;
}

function toGenerateResponse(
  result: Buffer,
  responseFormat: z.infer<typeof TTSConfigSchema>['response_format'] = 'mp3'
): GenerateResponseData {
  const mediaType = RESPONSE_FORMAT_MEDIA_TYPES[responseFormat];
  return {
    candidates: [
      {
        index: 0,
        finishReason: 'stop',
        message: {
          role: 'model',
          content: [
            {
              media: {
                contentType: mediaType,
                url: `data:${mediaType};base64,${result.toString('base64')}`,
              },
            },
          ],
        },
      },
    ],
  };
}

export function ttsModel(
  ai: Genkit,
  name: string,
  client: OpenAI
): ModelAction<typeof TTSConfigSchema> {
  const modelId = `openai/${name}`;
  const model = SUPPORTED_TTS_MODELS[name];
  if (!model) throw new Error(`Unsupported model: ${name}`);

  return ai.defineModel<typeof TTSConfigSchema>(
    {
      name: modelId,
      ...model.info,
      configSchema: model.configSchema,
    },
    async (request) => {
      const ttsRequest = toTTSRequest(name, request);
      const result = await client.audio.speech.create(ttsRequest);
      const resultArrayBuffer = await result.arrayBuffer();
      const resultBuffer = Buffer.from(new Uint8Array(resultArrayBuffer));
      return toGenerateResponse(resultBuffer, ttsRequest.response_format);
    }
  );
}
