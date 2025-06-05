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
  Transcription,
  TranscriptionCreateParams,
} from 'openai/resources/audio/index.mjs';

export const Whisper1ConfigSchema = GenerationCommonConfigSchema.extend({
  language: z.string().optional(),
  timestamp_granularities: z.array(z.enum(['word', 'segment'])).optional(),
  response_format: z
    .enum(['json', 'text', 'srt', 'verbose_json', 'vtt'])
    .optional(),
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
  configSchema: Whisper1ConfigSchema,
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
  configSchema: Whisper1ConfigSchema,
});

function toWhisper1Request(
  request: GenerateRequest<typeof Whisper1ConfigSchema>
): TranscriptionCreateParams {
  const message = new Message(request.messages[0]);
  const media = message.media;
  if (!media?.url) {
    throw new Error('No media found in the request');
  }
  const mediaBuffer = Buffer.from(
    media.url.slice(media.url.indexOf(',') + 1),
    'base64'
  );
  const mediaFile = new File([mediaBuffer], 'input', {
    type:
      media.contentType ??
      media.url.slice('data:'.length, media.url.indexOf(';')),
  });
  const options: TranscriptionCreateParams = {
    model: 'whisper-1',
    file: mediaFile,
    prompt: message.text,
    temperature: request.config?.temperature,
    language: request.config?.language,
    timestamp_granularities: request.config?.timestamp_granularities,
  };
  const outputFormat = request.output?.format as 'json' | 'text' | 'media';
  const customFormat = request.config?.response_format;
  if (outputFormat && customFormat) {
    if (
      outputFormat === 'json' &&
      customFormat !== 'json' &&
      customFormat !== 'verbose_json'
    ) {
      throw new Error(
        `Custom response format ${customFormat} is not compatible with output format ${outputFormat}`
      );
    }
  }
  if (outputFormat === 'media') {
    throw new Error(`Output format ${outputFormat} is not supported.`);
  }
  options.response_format = customFormat || outputFormat || 'text';
  for (const k in options) {
    if (options[k] === undefined) {
      delete options[k];
    }
  }
  return options;
}

function toGenerateResponse(
  result: Transcription | string
): GenerateResponseData {
  return {
    candidates: [
      {
        index: 0,
        finishReason: 'stop',
        message: {
          role: 'model',
          content: [
            {
              text: typeof result === 'string' ? result : result.text,
            },
          ],
        },
      },
    ],
  };
}

export const SUPPORTED_STT_MODELS = {
  'gpt-4o-transcribe': gpt4oTranscribe,
  'whisper-1': whisper1,
};

export function sttModel(
  ai: Genkit,
  name: string,
  client: OpenAI
): ModelAction<typeof Whisper1ConfigSchema> {
  const modelId = `openai/${name}`;
  const model = SUPPORTED_STT_MODELS[name];
  if (!model) throw new Error(`Unsupported model: ${name}`);

  return ai.defineModel<typeof Whisper1ConfigSchema>(
    {
      name: modelId,
      ...model.info,
      configSchema: model.configSchema,
    },
    async (request) => {
      const params = toWhisper1Request(request);
      // Explicitly setting stream to false ensures we use the non-streaming overload
      const result = await client.audio.transcriptions.create({
        ...params,
        stream: false,
      });
      return toGenerateResponse(result);
    }
  );
}
