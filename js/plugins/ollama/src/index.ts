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
  getBasicUsageStats,
} from '@genkit-ai/ai/model';
import { genkitPlugin, Plugin } from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';

interface OllamaPluginParams {
  models: { name: string; type?: 'chat' | 'generate' }[];
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
        ollamaModel(model.name, model.type, serverAddress)
      ),
    };
  }
);

function ollamaModel(
  name: string,
  type: 'chat' | 'generate' | undefined,
  serverAddress: string
) {
  return defineModel(
    {
      name: `ollama/${name}`,
      label: `Ollama - ${name}`,
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
      const request = {
        model: name,
        options,
        stream: !!streamingCallback,
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
            role: m.role,
            content: messageText,
            images: images.length > 0 ? images : undefined,
          });
        });
        request.messages = messages;
      } else {
        request.prompt = getPrompt(input);
      }
      logger.debug(request, `ollama request (type: ${type})`);
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

      let textResponse = '';
      if (streamingCallback) {
        const reader = res.body.getReader();
        const textDecoder = new TextDecoder();
        for await (const chunk of readChunks(reader)) {
          const chunkText = textDecoder.decode(chunk);
          const json = JSON.parse(chunkText);
          streamingCallback({
            index: 0,
            content: [
              {
                text:
                  type === 'chat'
                    ? (json.message as Message).content
                    : json.response,
              },
            ],
          });
          textResponse +=
            type === 'chat' ? (json.message as Message).content : json.response;
        }
      } else {
        const txtBody = await res.text();
        const json = JSON.parse(txtBody);
        textResponse = json.response;
      }
      logger.debug(textResponse, 'ollama final response');

      const responseCandidates = [
        {
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
        } as CandidateData,
      ];
      return {
        candidates: responseCandidates,
        usage: getBasicUsageStats(input.messages, responseCandidates),
      } as GenerateResponseData;
    }
  );
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
  // TODO: too naive...
  // see https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion
  const content = input.messages[0]?.content[0];
  return content.text;
}

interface Message {
  role: string;
  content: string;
  images?: string[];
}
