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

import { MistralGoogleCloud } from '@mistralai/mistralai-gcp';
import { HTTPClient } from '@mistralai/mistralai-gcp/lib/http';
import {
  AssistantMessage,
  ChatCompletionChoiceFinishReason,
  ChatCompletionRequest,
  ChatCompletionResponse,
  FunctionCall,
  Tool as MistralTool,
  ToolCall,
  ToolTypes,
} from '@mistralai/mistralai-gcp/models/components';
import {
  GENKIT_CLIENT_HEADER,
  GenerateRequest,
  GenerationCommonConfigSchema,
  Genkit,
  MessageData,
  ModelReference,
  ModelResponseData,
  Part,
  Role,
  ToolRequestPart,
  z,
} from 'genkit';
import { modelRef } from 'genkit/model';

export const MistralConfigSchema = GenerationCommonConfigSchema.extend({
  location: z.string().optional(),
  maxOutputTokens: z.number().optional(),
  temperature: z.number().optional(),
  //   TODO: is this supported?
  //   topK: z.number().optional(),
  topP: z.number().optional(),
  stopSequences: z.array(z.string()).optional(),
});

export const mistralLarge = modelRef({
  name: 'vertexai/mistral-large',
  info: {
    label: 'Vertex AI Model Garden - Mistral Large',
    versions: ['mistral-large-2411', 'mistral-large-2407'],
    supports: {
      multiturn: true,
      media: false,
      tools: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: MistralConfigSchema,
});

export const mistralNemo = modelRef({
  name: 'vertexai/mistral-nemo',
  info: {
    label: 'Vertex AI Model Garden - Mistral Nemo',
    versions: ['mistral-nemo-2407'],
    supports: {
      multiturn: true,
      media: false,
      tools: false,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: MistralConfigSchema,
});

export const codestral = modelRef({
  name: 'vertexai/codestral',
  info: {
    label: 'Vertex AI Model Garden - Codestral',
    versions: ['codestral-2405'],
    supports: {
      multiturn: true,
      media: false,
      tools: false,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: MistralConfigSchema,
});

export const SUPPORTED_MISTRAL_MODELS: Record<
  string,
  ModelReference<typeof MistralConfigSchema>
> = {
  'mistral-large': mistralLarge,
  'mistral-nemo': mistralNemo,
  codestral: codestral,
};

// TODO: Do they export a type for this?
type MistralRole = 'assistant' | 'user' | 'tool' | 'system';

function toMistralRole(role: Role): MistralRole {
  switch (role) {
    case 'model':
      return 'assistant';
    case 'user':
      return 'user';
    case 'tool':
      return 'tool';
    case 'system':
      return 'system';
  }
}
function toMistralToolRequest(toolRequest: Record<string, any>): FunctionCall {
  if (!toolRequest.name) {
    throw new Error('Tool name is required');
  }

  return {
    name: toolRequest.name,
    // Mistral expects arguments as either a string or object
    arguments:
      typeof toolRequest.input === 'string'
        ? toolRequest.input
        : JSON.stringify(toolRequest.input),
  };
}

export function toMistralRequest(
  model: string,
  input: GenerateRequest<typeof MistralConfigSchema>
): ChatCompletionRequest {
  const messages = input.messages.map((msg) => {
    // Handle regular text messages
    if (msg.content.every((part) => part.text)) {
      const content = msg.content.map((part) => part.text || '').join('');
      return {
        role: toMistralRole(msg.role),
        content,
      };
    }

    // Handle assistant's tool/function calls
    const toolRequest = msg.content.find((part) => part.toolRequest);
    if (toolRequest?.toolRequest) {
      const functionCall = toMistralToolRequest(toolRequest.toolRequest);
      return {
        role: 'assistant' as const,
        content: null,
        toolCalls: [
          {
            // Changed from function_call to tool_calls array
            id: toolRequest.toolRequest.ref,
            type: ToolTypes.Function,
            function: {
              name: functionCall.name,
              arguments: functionCall.arguments,
            },
          },
        ],
      };
    }

    // Handle tool responses
    const toolResponse = msg.content.find((part) => part.toolResponse);
    if (toolResponse?.toolResponse) {
      return {
        role: 'tool' as const,
        name: toolResponse.toolResponse.name,
        content: JSON.stringify(toolResponse.toolResponse.output),
        tool_call_id: toolResponse.toolResponse.ref, // This must match the id from tool_calls
      };
    }

    return {
      role: toMistralRole(msg.role),
      content: msg.content.map((part) => part.text || '').join(''),
    };
  });

  validateToolSequence(messages); // This line exists but might not be running?

  const request: ChatCompletionRequest = {
    model,
    messages,
    maxTokens: input.config?.maxOutputTokens ?? 1024,
    temperature: input.config?.temperature ?? 0.7,
    topP: input.config?.topP,
    stop: input.config?.stopSequences,
  };

  if (input.tools) {
    request.tools = input.tools.map((tool) => ({
      type: 'function',
      function: {
        name: tool.name,
        description: tool.description,
        parameters: tool.inputSchema || {},
      },
    })) as MistralTool[];
  }

  return request;
}
// Helper to convert Mistral AssistantMessage content into Genkit parts
function fromMistralTextPart(content: string): Part {
  return {
    text: content,
  };
}

// Helper to convert Mistral ToolCall into Genkit parts
function fromMistralToolCall(toolCall: ToolCall): ToolRequestPart {
  if (!toolCall.function) {
    throw new Error('Tool call must include a function definition');
  }

  return {
    toolRequest: {
      ref: toolCall.id,
      name: toolCall.function.name,
      input:
        typeof toolCall.function.arguments === 'string'
          ? JSON.parse(toolCall.function.arguments)
          : toolCall.function.arguments,
    },
  };
}

// Converts Mistral AssistantMessage content into Genkit parts
function fromMistralMessage(message: AssistantMessage): Part[] {
  const parts: Part[] = [];

  // Handle textual content
  if (typeof message.content === 'string') {
    parts.push(fromMistralTextPart(message.content));
  } else if (Array.isArray(message.content)) {
    // If content is an array of ContentChunk, handle each chunk
    message.content.forEach((chunk) => {
      if (chunk.type === 'text') {
        parts.push(fromMistralTextPart(chunk.text));
      }
      // Add support for other ContentChunk types here if needed
    });
  }

  // Handle tool calls if present
  if (message.toolCalls) {
    message.toolCalls.forEach((toolCall) => {
      parts.push(fromMistralToolCall(toolCall));
    });
  }

  return parts;
}

// Maps Mistral finish reasons to Genkit finish reasons
export function fromMistralFinishReason(
  reason: ChatCompletionChoiceFinishReason | undefined
): 'length' | 'unknown' | 'stop' | 'blocked' | 'other' {
  switch (reason) {
    case ChatCompletionChoiceFinishReason.Stop:
      return 'stop';
    case ChatCompletionChoiceFinishReason.Length:
    case ChatCompletionChoiceFinishReason.ModelLength:
      return 'length';
    case ChatCompletionChoiceFinishReason.Error:
      return 'other'; // Map generic errors to "other"
    case ChatCompletionChoiceFinishReason.ToolCalls:
      return 'stop'; // Assuming tool calls signify a "stop" in processing
    default:
      return 'other'; // For undefined or unmapped reasons
  }
}

// Converts a Mistral response to a Genkit response
export function fromMistralResponse(
  input: GenerateRequest<typeof MistralConfigSchema>,
  response: ChatCompletionResponse
): ModelResponseData {
  const firstChoice = response.choices?.[0];
  // Convert content from Mistral response to Genkit parts
  const contentParts: Part[] = firstChoice?.message
    ? fromMistralMessage(firstChoice.message)
    : [];

  const message: MessageData = {
    role: 'model',
    content: contentParts,
  };

  return {
    message,
    finishReason: fromMistralFinishReason(firstChoice?.finishReason),
    usage: {
      inputTokens: response.usage.promptTokens,
      outputTokens: response.usage.completionTokens,
    },
    custom: {
      id: response.id,
      model: response.model,
      created: response.created,
    },
    raw: response, // Include the raw response for debugging or additional context
  };
}

export function mistralModel(
  ai: Genkit,
  modelName: string,
  projectId: string,
  region: string
) {
  const clientFactory = createClientFactory(projectId, GENKIT_CLIENT_HEADER);

  const model = SUPPORTED_MISTRAL_MODELS[modelName];
  if (!model) {
    throw new Error(`Unsupported Mistral model name ${modelName}`);
  }

  return ai.defineModel(
    {
      name: model.name,
      label: model.info?.label,
      configSchema: MistralConfigSchema,
      supports: model.info?.supports,
      versions: model.info?.versions,
    },
    async (input, streamingCallback) => {
      const client = clientFactory(input.config?.location || region);

      const versionedModel =
        input.config?.version ?? model.info?.versions?.[0] ?? model.name;

      if (!streamingCallback) {
        const mistralRequest = toMistralRequest(versionedModel, input);

        const response = await client.chat.complete(mistralRequest);

        const responseToGenkit = fromMistralResponse(input, response);

        // return fromMistralResponse(input, response);
        return responseToGenkit;
      } else {
        // TODO: is this supported?
        throw new Error('Streaming is not yet implemented for Mistral models.');
      }
    }
  );
}

function createClientFactory(
  projectId: string,
  GENKIT_CLIENT_HEADER: string
): (region: string) => MistralGoogleCloud {
  const clients: Record<string, MistralGoogleCloud> = {};

  return (region: string): MistralGoogleCloud => {
    if (!clients[region]) {
      const httpClient = new HTTPClient({
        fetcher: (input, init) => {
          const request = new Request(
            input instanceof Request ? input : input.toString(),
            init
          );

          const modifiedHeaders = new Headers(request.headers);
          modifiedHeaders.set('X-Goog-Api-Client', GENKIT_CLIENT_HEADER);

          const modifiedRequest = new Request(request, {
            headers: modifiedHeaders,
          });
          return fetch(modifiedRequest);
        },
      });

      // This is necessary because the SDK wasn't handling 2411 model correctly, see https://github.com/mistralai/client-ts/issues/52
      httpClient.addHook('beforeRequest', async (request) => {
        const url = new URL(request.url);

        // Clone the request to safely handle its body
        const clonedRequest = request.clone();

        try {
          // Read and parse the request body if it exists
          const bodyText = await clonedRequest.text();
          const body = bodyText ? JSON.parse(bodyText) : null;

          if (body && body.model) {
            const modelMapping: Record<string, string> = {
              'mistral-large-2407': 'mistral-large-2407',
              'mistral-large-2411': 'mistral-large-2411',
              'mistral-nemo-2407': 'mistral-nemo-2407',
              'codestral-2405': 'codestral-2405',
            };

            const mappedModel = modelMapping[body.model] ?? body.model;

            // Update the model name in the body
            body.model = mappedModel;

            // Update the URL path to include the correct model ID
            url.pathname = url.pathname.replace(
              /models\/[^:]+/,
              `models/${mappedModel}`
            );

            // Return the modified request with the updated URL and body
            return new Request(url.toString(), {
              ...request,
              method: 'POST', // Ensure the method is POST
              body: JSON.stringify(body), // Serialize the updated body back to JSON
              headers: new Headers(request.headers), // Clone headers if needed
            });
          }
        } catch (error) {
          console.error(
            'Failed to process request body in beforeRequest hook:',
            error
          );
          throw new Error('Invalid request body format in beforeRequest hook');
        }

        // If no modifications are needed, return the original request
        return request;
      });

      clients[region] = new MistralGoogleCloud({
        region,
        projectId,
        httpClient,
      });
    }

    return clients[region];
  };
}

// Helper function to validate tool calls and responses match
function validateToolSequence(messages: any[]) {
  const toolCalls = messages
    .filter((m) => {
      return m.role === 'assistant' && (m.toolCalls || m.function_call);
    })
    .reduce((acc: any[], m) => {
      if (m.toolCalls) {
        return [...acc, ...m.toolCalls];
      }
      if (m.function_call) {
        return [...acc, { id: m.tool_call_id, ...m.function_call }];
      }
      return acc;
    }, []);

  const toolResponses = messages.filter((m) => m.role === 'tool');

  if (toolCalls.length !== toolResponses.length) {
    throw new Error(
      `Mismatch between tool calls (${toolCalls.length}) and responses (${toolResponses.length})`
    );
  }

  // Verify each tool response matches a call by ID
  toolResponses.forEach((response) => {
    const matchingCall = toolCalls.find(
      (call) => call.id === response.tool_call_id
    );
    if (!matchingCall) {
      throw new Error(
        `Tool response with ID ${response.tool_call_id} has no matching call`
      );
    }
  });
}
