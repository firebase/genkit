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
  defineModel,
  GenerateRequest,
  GenerateResponseData,
  GenerationCommonConfigSchema,
  getBasicUsageStats,
  MessageData,
} from '@genkit-ai/ai/model';
import { genkitPlugin, Plugin } from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';

type ApiType = 'chat' | 'generate';

interface OllamaPluginParams {
  models: { name: string; type?: ApiType }[];
  /**
   *  ollama server address.
   */
  serverAddress: string;
}

export const ollama: Plugin<[OllamaPluginParams]> = genkitPlugin(
  'ollama',
  async (params: OllamaPluginParams) => {
    const serverAddress = params?.serverAddress;
    return {
      models: params.models.map((model) =>
        ollamaModel(model.name, model.type ?? 'chat', serverAddress)
      ),
    };
  }
);

function ollamaModel(name: string, type: ApiType, serverAddress: string) {
  return defineModel(
    {
      name: `ollama/${name}`,
      label: `Ollama - ${name}`,
      configSchema: GenerationCommonConfigSchema,
      supports: {
        multiturn: type === 'chat',
      },
    },
    async (input, streamingCallback) => {
      const options: Record<string, any> = {};
      if (input.config?.hasOwnProperty('temperature')) {
        options.temperature = input.config?.temperature;
      }
      if (input.config?.hasOwnProperty('topP')) {
        options.top_p = input.config?.topP;
      }
      if (input.config?.hasOwnProperty('topK')) {
        options.top_k = input.config?.topK;
      }
      if (input.config?.hasOwnProperty('stopSequences')) {
        options.stop = input.config?.stopSequences?.join('');
      }
      if (input.config?.hasOwnProperty('maxOutputTokens')) {
        options.num_predict = input.config?.maxOutputTokens;
      }
      const request = toOllamaRequest(
        name,
        input,
        options,
        type,
        !!streamingCallback
      );
      logger.debug(request, `ollama request (${type})`);

      const res = await fetch(
        serverAddress + (type === 'chat' ? '/api/chat' : '/api/generate'),
        {
          method: 'POST',
          body: JSON.stringify(request),
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      if (!res.body) {
        throw new Error('Response has no body');
      }

      const responseCandidates: CandidateData[] = [];

      if (streamingCallback) {
        const reader = res.body.getReader();
        const textDecoder = new TextDecoder();
        let textResponse = '';
        for await (const chunk of readChunks(reader)) {
          const chunkText = textDecoder.decode(chunk);
          const json = JSON.parse(chunkText);
          const message = parseMessage(json, type);
          streamingCallback({
            index: 0,
            content: message.content,
          });
          textResponse += message.content[0].text;
        }
        responseCandidates.push({
          index: 0,
          finishReason: 'stop',
          message: {
            role: 'model',
            content: [
              {
                text: textResponse,
              },
            ],
          },
        } as CandidateData);
      } else {
        const txtBody = await res.text();
        const json = JSON.parse(txtBody);
        logger.debug(txtBody, 'ollama raw response');

        responseCandidates.push({
          index: 0,
          finishReason: 'stop',
          message: parseMessage(json, type),
        } as CandidateData);
      }

      return {
        candidates: responseCandidates,
        usage: getBasicUsageStats(input.messages, responseCandidates),
      } as GenerateResponseData;
    }
  );
}

function parseMessage(response: any, type: ApiType): MessageData {
  if (response.error) {
    throw new Error(response.error);
  }
  if (type === 'chat') {
    return {
      role: toGenkitRole(response.message.role),
      content: [
        {
          text: response.message.content,
        },
      ],
    };
  } else {
    return {
      role: 'model',
      content: [
        {
          text: response.response,
        },
      ],
    };
  }
}

function toOllamaRequest(
  name: string,
  input: GenerateRequest,
  options: Record<string, any>,
  type: ApiType,
  stream: boolean
) {
  const request = {
    model: name,
    options,
    stream,
  } as any;
  if (type === 'chat') {
    const messages: Message[] = [];
    input.messages.forEach((m) => {
      let messageText = '';
      const images: string[] = [];
      m.content.forEach((c) => {
        if (c.text) {
          messageText += c.text;
        }
        if (c.media) {
          images.push(c.media.url);
        }
      });
      messages.push({
        role: toOllamaRole(m.role),
        content: messageText,
        images: images.length > 0 ? images : undefined,
      });
    });
    request.messages = messages;
  } else {
    request.prompt = getPrompt(input);
  }
  return request;
}

function toOllamaRole(role) {
  if (role === 'model') {
    return 'assistant';
  }
  return role; // everything else seems to match
}

function toGenkitRole(role) {
  if (role === 'assistant') {
    return 'model';
  }
  return role; // everything else seems to match
}

function readChunks(reader) {
  return {
    async *[Symbol.asyncIterator]() {
      let readResult = await reader.read();
      while (!readResult.done) {
        yield readResult.value;
        readResult = await reader.read();
      }
    },
  };
}

function getPrompt(input: GenerateRequest) {
  return input.messages.map((m) => m.content.map((c) => c.text).join()).join();
}

interface Message {
  role: string;
  content: string;
  images?: string[];
}
