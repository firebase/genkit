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

import { Genkit, GenkitError } from 'genkit';
import { extractJson } from 'genkit/extract';
import { logger } from 'genkit/logging';
import {
  GenerateRequest,
  GenerateResponseData,
  GenerationCommonConfigSchema,
  MessageData,
  getBasicUsageStats,
} from 'genkit/model';
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';
import { ErrorResponse } from 'ollama';
import { defineOllamaEmbedder } from './embeddings.js';
import {
  ApiType,
  ChatResponse,
  GenerateResponse,
  Message,
  ModelDefinition,
  OllamaPluginParams,
  RequestHeaders,
} from './types.js';

export { defineOllamaEmbedder };

export function ollama(params: OllamaPluginParams): GenkitPlugin {
  return genkitPlugin('ollama', async (ai: Genkit) => {
    const serverAddress = params.serverAddress;
    params.models?.map((model) =>
      ollamaModel(ai, model, serverAddress, params.requestHeaders)
    );
    params.embedders?.map((model) =>
      defineOllamaEmbedder(ai, {
        name: model.name,
        modelName: model.name,
        dimensions: model.dimensions,
        options: params,
      })
    );
  });
}

function ollamaModel(
  ai: Genkit,
  model: ModelDefinition,
  serverAddress: string,
  requestHeaders?: RequestHeaders
) {
  return ai.defineModel(
    {
      name: `ollama/${model.name}`,
      label: `Ollama - ${model.name}`,
      configSchema: GenerationCommonConfigSchema,
      supports: {
        multiturn: !model.type || model.type === 'chat',
        systemRole: true,
      },
    },
    async (input, streamingCallback) => {
      const options: Record<string, any> = {};
      if (input.config?.temperature !== undefined) {
        options.temperature = input.config.temperature;
      }
      if (input.config?.topP !== undefined) {
        options.top_p = input.config.topP;
      }
      if (input.config?.topK !== undefined) {
        options.top_k = input.config.topK;
      }
      if (input.config?.stopSequences !== undefined) {
        options.stop = input.config.stopSequences.join('');
      }
      if (input.config?.maxOutputTokens !== undefined) {
        options.num_predict = input.config.maxOutputTokens;
      }
      const type = model.type ?? 'chat';
      const request = toOllamaRequest(
        model.name,
        input,
        options,
        type,
        !!streamingCallback
      );
      logger.debug(request, `ollama request (${type})`);

      const extraHeaders = requestHeaders
        ? typeof requestHeaders === 'function'
          ? await requestHeaders(
              {
                serverAddress,
                model,
              },
              input
            )
          : requestHeaders
        : {};

      let res;
      try {
        res = await fetch(
          serverAddress + (type === 'chat' ? '/api/chat' : '/api/generate'),
          {
            method: 'POST',
            body: JSON.stringify(request),
            headers: {
              'Content-Type': 'application/json',
              ...extraHeaders,
            },
          }
        );
      } catch (e) {
        const cause = (e as any).cause;
        if (
          cause &&
          cause instanceof Error &&
          cause.message?.includes('ECONNREFUSED')
        ) {
          cause.message += '. Make sure the Ollama server is running.';
          throw cause;
        }
        throw e;
      }
      if (!res.body) {
        throw new Error('Response has no body');
      }

      let message: MessageData;

      if (streamingCallback) {
        const reader = res.body.getReader();
        const textDecoder = new TextDecoder();
        let textResponse = '';
        for await (const chunk of readChunks(reader)) {
          const chunkText = textDecoder.decode(chunk);
          const json = extractJson(chunkText) as
            | ChatResponse
            | GenerateResponse;
          const message = parseMessage(json, type, input);
          streamingCallback({
            index: 0,
            content: message.content,
          });
          textResponse += message.content[0].text;
        }
        message = {
          role: 'model',
          content: [
            {
              text: textResponse,
            },
          ],
        };
      } else {
        const txtBody = await res.text();
        const json = extractJson(txtBody) as ChatResponse | GenerateResponse;
        message = parseMessage(json, type, input);
      }

      return {
        message,
        usage: getBasicUsageStats(input.messages, message),
        finishReason: 'stop',
      } as GenerateResponseData;
    }
  );
}

function parseMessage(
  response: ChatResponse | GenerateResponse,
  type: ApiType,
  input: GenerateRequest
): MessageData {
  function isErrorResponse(resp: any): resp is ErrorResponse {
    return 'error' in resp && typeof resp.error === 'string';
  }

  if (isErrorResponse(response)) {
    throw new Error(response.error);
  }

  function isChatResponse(resp: any): resp is ChatResponse {
    return 'message' in resp;
  }

  function isGenerateResponse(resp: any): resp is GenerateResponse {
    return 'response' in resp;
  }

  // Handle JSON format if requested
  if (input.output?.format === 'json' && input.output.schema) {
    let rawContent;
    if (isChatResponse(response)) {
      try {
        // Parse the content string into an object
        const parsedContent = extractJson(response.message.content);
        // Validate against the schema
        rawContent = parsedContent;
      } catch (e) {
        throw new GenkitError({
          message: 'Failed to parse structured response from Ollama model',
          status: 'FAILED_PRECONDITION',
        });
      }
    } else if (isGenerateResponse(response)) {
      try {
        const parsedContent = extractJson(response.response);
        rawContent = parsedContent;
      } catch (e) {
        throw new GenkitError({
          message: 'Failed to parse structured response from Ollama model',
          status: 'FAILED_PRECONDITION',
        });
      }
    } else {
      throw new Error('Invalid response format');
    }

    return {
      role:
        type === 'chat' && isChatResponse(response)
          ? toGenkitRole(response.message.role)
          : 'model',
      content: [{ text: JSON.stringify(rawContent) }],
    };
  }

  // Handle regular output
  if (isChatResponse(response)) {
    return {
      role: toGenkitRole(response.message.role),
      content: [{ text: response.message.content }],
    };
  } else if (isGenerateResponse(response)) {
    return {
      role: 'model',
      content: [{ text: response.response }],
    };
  }

  throw new GenkitError({
    message: 'Invalid response format from Ollama model',
    status: 'FAILED_PRECONDITION',
  });
}

function toOllamaRequest(
  name: string,
  input: GenerateRequest,
  options: Record<string, any>,
  type: ApiType,
  stream: boolean
) {
  const request: any = {
    model: name,
    options,
    stream,
  };

  // Add format and schema if specified in output
  if (input.output?.format === 'json' && input.output.schema) {
    request.format = input.output.schema;
  }

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
    request.system = getSystemMessage(input);
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

function getPrompt(input: GenerateRequest): string {
  return input.messages
    .filter((m) => m.role !== 'system')
    .map((m) => m.content.map((c) => c.text).join())
    .join();
}

function getSystemMessage(input: GenerateRequest): string {
  return input.messages
    .filter((m) => m.role === 'system')
    .map((m) => m.content.map((c) => c.text).join())
    .join();
}
