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
  embedderRef,
  modelActionMetadata,
  z,
  type ActionMetadata,
  type EmbedderReference,
  type ModelReference,
  type ToolRequest,
  type ToolRequestPart,
  type ToolResponse,
} from 'genkit';
import { logger } from 'genkit/logging';
import {
  GenerationCommonConfigDescriptions,
  GenerationCommonConfigSchema,
  getBasicUsageStats,
  modelRef,
  type GenerateRequest,
  type GenerateResponseData,
  type MessageData,
  type ModelInfo,
  type ToolDefinition,
} from 'genkit/model';
import {
  embedder,
  genkitPluginV2,
  model,
  type GenkitPluginV2,
  type ResolvableAction,
} from 'genkit/plugin';
import type {
  ApiType,
  EmbeddingModelDefinition,
  ListLocalModelsResponse,
  LocalModel,
  Message,
  ModelDefinition,
  OllamaPluginParams,
  OllamaTool,
  OllamaToolCall,
  RequestHeaders,
} from './types.js';

export type { OllamaPluginParams };

export type OllamaPlugin = {
  (params?: OllamaPluginParams): GenkitPluginV2;

  model(
    name: string,
    config?: z.infer<typeof OllamaConfigSchema>
  ): ModelReference<typeof OllamaConfigSchema>;
  embedder(name: string, config?: Record<string, any>): EmbedderReference;
};

const ANY_JSON_SCHEMA: Record<string, any> = {
  $schema: 'http://json-schema.org/draft-07/schema#',
};

const GENERIC_MODEL_INFO = {
  supports: {
    multiturn: true,
    media: true,
    tools: true,
    toolChoice: true,
    systemRole: true,
    constrained: 'all',
  },
} as ModelInfo;

const DEFAULT_OLLAMA_SERVER_ADDRESS = 'http://localhost:11434';

async function createOllamaModel(
  modelDef: ModelDefinition,
  serverAddress: string,
  requestHeaders?: RequestHeaders
) {
  return model(
    {
      name: modelDef.name,
      label: `Ollama - ${modelDef.name}`,
      configSchema: OllamaConfigSchema,
      supports: {
        multiturn: !modelDef.type || modelDef.type === 'chat',
        systemRole: true,
        tools: modelDef.supports?.tools,
      },
    },
    async (input, opts) => {
      const { topP, topK, stopSequences, maxOutputTokens, ...rest } =
        input.config as any;
      const options: Record<string, any> = { ...rest };
      if (topP !== undefined) {
        options.top_p = topP;
      }
      if (topK !== undefined) {
        options.top_k = topK;
      }
      if (stopSequences !== undefined) {
        options.stop = stopSequences.join('');
      }
      if (maxOutputTokens !== undefined) {
        options.num_predict = maxOutputTokens;
      }
      const type = modelDef.type ?? 'chat';
      const request = toOllamaRequest(
        modelDef.name,
        input,
        options,
        type,
        !!opts.sendChunk
      );
      logger.debug(request, `ollama request (${type})`);

      const extraHeaders = await getHeaders(
        serverAddress,
        requestHeaders,
        modelDef,
        input
      );
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

      if (opts.sendChunk) {
        const reader = res.body.getReader();
        const textDecoder = new TextDecoder();
        let textResponse = '';
        for await (const chunk of readChunks(reader)) {
          const chunkText = textDecoder.decode(chunk);
          const json = JSON.parse(chunkText);
          const message = parseMessage(json, type);
          opts.sendChunk({
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
        const json = JSON.parse(txtBody);
        logger.debug(txtBody, 'ollama raw response');

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

async function createOllamaEmbedder(
  modelDef: EmbeddingModelDefinition,
  serverAddress: string,
  requestHeaders?: RequestHeaders
) {
  return embedder(
    {
      name: modelDef.name,
      info: {
        label: 'Ollama Embedding - ' + modelDef.name,
        dimensions: modelDef.dimensions,
        supports: {
          input: ['text'],
        },
      },
    },
    async (input, config) => {
      const { url, requestPayload, headers } = await toOllamaEmbedRequest(
        modelDef.name,
        modelDef.dimensions,
        input.input,
        serverAddress,
        requestHeaders
      );

      const response: Response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestPayload),
      });

      if (!response.ok) {
        const errMsg = (await response.json()).error?.message || '';
        throw new Error(
          `Error fetching embedding from Ollama: ${response.statusText}. ${errMsg}`
        );
      }

      const payload = (await response.json()) as any;

      const embeddings: { embedding: number[] }[] = [];

      for (const embedding of payload.embeddings) {
        embeddings.push({ embedding });
      }
      return { embeddings };
    }
  );
}

async function listActions(
  serverAddress: string,
  requestHeaders?: RequestHeaders
): Promise<ActionMetadata[]> {
  const models = await listLocalModels(serverAddress, requestHeaders);
  return (
    models
      // naively filter out embedders, unfortunately there's no better way.
      ?.filter((m) => m.model && !m.model.includes('embed'))
      .map((m) =>
        modelActionMetadata({
          name: m.model,
          info: GENERIC_MODEL_INFO,
        })
      ) || []
  );
}

function ollamaPlugin(params?: OllamaPluginParams): GenkitPluginV2 {
  if (!params) {
    params = {};
  }
  if (!params.serverAddress) {
    params.serverAddress = DEFAULT_OLLAMA_SERVER_ADDRESS;
  }
  const serverAddress = params.serverAddress;

  return genkitPluginV2({
    name: 'ollama',
    async init() {
      const actions: ResolvableAction[] = [];

      if (params?.models) {
        for (const model of params.models) {
          actions.push(
            await createOllamaModel(model, serverAddress, params.requestHeaders)
          );
        }
      }

      if (params?.embedders) {
        for (const embedder of params.embedders) {
          actions.push(
            await createOllamaEmbedder(
              embedder,
              serverAddress,
              params.requestHeaders
            )
          );
        }
      }

      return actions;
    },
    async resolve(actionType, actionName) {
      // dynamically resolve models, for embedders user must provide dimensions.
      if (actionType === 'model') {
        return await createOllamaModel(
          {
            name: actionName,
          },
          serverAddress,
          params?.requestHeaders
        );
      }
      return undefined;
    },
    async list() {
      return await listActions(serverAddress, params?.requestHeaders);
    },
  });
}

async function listLocalModels(
  serverAddress: string,
  requestHeaders?: RequestHeaders
): Promise<LocalModel[]> {
  // We call the ollama list local models api: https://github.com/ollama/ollama/blob/main/docs/api.md#list-local-models
  let res;
  try {
    res = await fetch(serverAddress + '/api/tags', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(await getHeaders(serverAddress, requestHeaders)),
      },
    });
  } catch (e) {
    throw new Error(`Make sure the Ollama server is running.`, {
      cause: e,
    });
  }
  const modelResponse = JSON.parse(await res.text()) as ListLocalModelsResponse;
  return modelResponse.models;
}

/**
 * Please refer to: https://github.com/ollama/ollama/blob/main/docs/modelfile.md
 * for further information.
 */
export const OllamaConfigSchema = GenerationCommonConfigSchema.extend({
  temperature: z
    .number()
    .min(0.0)
    .max(1.0)
    .describe(
      GenerationCommonConfigDescriptions.temperature +
        ' The default value is 0.8.'
    )
    .optional(),
  topK: z
    .number()
    .describe(
      GenerationCommonConfigDescriptions.topK + ' The default value is 40.'
    )
    .optional(),
  topP: z
    .number()
    .min(0)
    .max(1.0)
    .describe(
      GenerationCommonConfigDescriptions.topP + ' The default value is 0.9.'
    )
    .optional(),
});

async function toOllamaEmbedRequest(
  modelName: string,
  dimensions: number,
  documents: any[],
  serverAddress: string,
  requestHeaders?: RequestHeaders
): Promise<{
  url: string;
  requestPayload: any;
  headers: Record<string, string>;
}> {
  const requestPayload = {
    model: modelName,
    input: documents.map((doc) => doc.text),
  };

  const extraHeaders = requestHeaders
    ? typeof requestHeaders === 'function'
      ? await requestHeaders({
          serverAddress,
          model: {
            name: modelName,
            dimensions,
          },
          embedRequest: requestPayload,
        })
      : requestHeaders
    : {};

  const headers = {
    'Content-Type': 'application/json',
    ...extraHeaders,
  };

  return {
    url: `${serverAddress}/api/embed`,
    requestPayload,
    headers,
  };
}

function parseMessage(response: any, type: ApiType): MessageData {
  if (response.error) {
    throw new Error(response.error);
  }
  if (type === 'chat') {
    // Tool calling is available only on the 'chat' API, not on 'generate'
    // https://github.com/ollama/ollama/blob/main/docs/api.md#chat-request-with-tools
    if (response.message.tool_calls && response.message.tool_calls.length > 0) {
      return {
        role: toGenkitRole(response.message.role),
        content: toGenkitToolRequest(response.message.tool_calls),
      };
    } else {
      return {
        role: toGenkitRole(response.message.role),
        content: [
          {
            text: response.message.content,
          },
        ],
      };
    }
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

async function getHeaders(
  serverAddress: string,
  requestHeaders?: RequestHeaders,
  model?: ModelDefinition,
  input?: GenerateRequest
): Promise<Record<string, string> | void> {
  return requestHeaders
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
    tools: input.tools?.filter(isValidOllamaTool).map(toOllamaTool),
  };
  if (type === 'chat') {
    const messages: Message[] = [];
    input.messages.forEach((m) => {
      let messageText = '';
      const role = toOllamaRole(m.role);
      const images: string[] = [];
      const toolRequests: ToolRequest[] = [];
      const toolResponses: ToolResponse[] = [];
      m.content.forEach((c) => {
        if (c.text) {
          messageText += c.text;
        }
        if (c.media) {
          let imageUri = c.media.url;
          // ollama doesn't accept full data URIs, just the base64 encoded image,
          // strip out data URI prefix (ex. `data:image/jpeg;base64,`)
          if (imageUri.startsWith('data:')) {
            imageUri = imageUri.substring(imageUri.indexOf(',') + 1);
          }
          images.push(imageUri);
        }
        if (c.toolRequest) {
          toolRequests.push(c.toolRequest);
        }
        if (c.toolResponse) {
          toolResponses.push(c.toolResponse);
        }
      });
      // Add tool responses, if any.
      toolResponses.forEach((t) => {
        messages.push({
          role,
          content:
            typeof t.output === 'string' ? t.output : JSON.stringify(t.output),
        });
      });
      messages.push({
        role: role,
        content: toolRequests.length > 0 ? '' : messageText,
        images: images.length > 0 ? images : undefined,
        tool_calls:
          toolRequests.length > 0 ? toOllamaToolCall(toolRequests) : undefined,
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

function toOllamaTool(tool: ToolDefinition): OllamaTool {
  return {
    type: 'function',
    function: {
      name: tool.name,
      description: tool.description,
      parameters: tool.inputSchema ?? ANY_JSON_SCHEMA,
    },
  };
}

function toOllamaToolCall(toolRequests: ToolRequest[]): OllamaToolCall[] {
  return toolRequests.map((t) => ({
    function: {
      name: t.name,
      // This should be safe since we already filtered tools that don't accept
      // objects
      arguments: t.input as Record<string, any>,
    },
  }));
}

function toGenkitToolRequest(tool_calls: OllamaToolCall[]): ToolRequestPart[] {
  return tool_calls.map((t) => ({
    toolRequest: {
      name: t.function.name,
      ref: t.function.index ? t.function.index.toString() : undefined,
      input: t.function.arguments,
    },
  }));
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

function isValidOllamaTool(tool: ToolDefinition): boolean {
  if (tool.inputSchema?.type !== 'object') {
    throw new Error(
      `Unsupported tool: '${tool.name}'. Ollama only supports tools with object inputs`
    );
  }
  return true;
}

export const ollama = ollamaPlugin as OllamaPlugin;
ollama.model = (
  name: string,
  config?: z.infer<typeof OllamaConfigSchema>
): ModelReference<typeof OllamaConfigSchema> => {
  return modelRef({
    name: `ollama/${name}`,
    config,
    configSchema: OllamaConfigSchema,
  });
};
ollama.embedder = (
  name: string,
  config?: Record<string, any>
): EmbedderReference => {
  return embedderRef({
    name: `ollama/${name}`,
    config,
  });
};
