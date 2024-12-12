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

import { Genkit, GenkitError, Role } from 'genkit';
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

/**
 * Creates and registers a Genkit plugin for Ollama integration.
 * @param {OllamaPluginParams} params - Configuration options for the Ollama plugin
 * @returns {GenkitPlugin} A configured Genkit plugin for Ollama
 */
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

/**
 * Defines a new Ollama model in the Genkit registry.
 * @param {Genkit} ai - The Genkit instance
 * @param {ModelDefinition} model - The model configuration
 * @param {string} serverAddress - The Ollama server address
 * @param {RequestHeaders} [requestHeaders] - Optional headers to include with requests
 * @returns {Model} The defined Genkit model
 * @private
 */
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
          const message = parseMessage(json, type);
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
        message = parseMessage(json, type);
      }

      return {
        message,
        usage: getBasicUsageStats(input.messages, message),
        finishReason: 'stop',
      } as GenerateResponseData;
    }
  );
}

/**
 * Parses the Ollama response into a standardized MessageData format.
 * @param {ChatResponse | GenerateResponse} response - The raw response from Ollama
 * @param {ApiType} type - The type of API used (chat or generate)
 * @returns {MessageData} The parsed message data
 * @throws {GenkitError} If the response format is invalid or parsing fails
 */
function parseMessage(
  response: ChatResponse | GenerateResponse,
  _type: ApiType
): MessageData {
  // Type guards
  const isErrorResponse = (resp: any): resp is ErrorResponse =>
    'error' in resp && typeof resp.error === 'string';
  const isChatResponse = (resp: any): resp is ChatResponse => 'message' in resp;
  const isGenerateResponse = (resp: any): resp is GenerateResponse =>
    'response' in resp;

  // Handle error responses first
  if (isErrorResponse(response)) {
    throw new Error(response.error);
  }

  // Get the text content based on response type
  const content = isChatResponse(response)
    ? response.message.content
    : isGenerateResponse(response)
      ? response.response
      : null;

  if (content === null) {
    throw new GenkitError({
      message: 'Invalid response format from Ollama model',
      status: 'FAILED_PRECONDITION',
    });
  }

  // Determine role for chat responses, default to 'model'
  const role = isChatResponse(response)
    ? toGenkitRole(response.message.role)
    : 'model';

  return {
    role,
    content: [{ text: content }],
  };
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

/**
 * Converts a Genkit role to the corresponding Ollama role.
 * @param {string} role - The Genkit role to convert
 * @returns {string} The corresponding Ollama role
 * @private
 */
function toOllamaRole(role: string) {
  if (role === 'model') {
    return 'assistant';
  }
  return role; // everything else seems to match
}

/**
 * Converts an Ollama role to the corresponding Genkit role.
 * @param {string} role - The Ollama role to convert
 * @returns {Role} The corresponding Genkit role
 * @private
 */
function toGenkitRole(role: string): Role {
  if (role === 'assistant') {
    return 'model' as Role;
  }
  return role as Role; // everything else seems to match
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
