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
  ImageBlockParam,
  Message,
  MessageCreateParamsBase,
  MessageParam,
  TextBlock,
  TextBlockParam,
  TextDelta,
} from '@anthropic-ai/sdk/resources/messages';
import { AnthropicVertex } from '@anthropic-ai/vertex-sdk';
import {
  CandidateData,
  GenerateRequest,
  GenerateResponseData,
  GenerationCommonConfigSchema,
  Part as GenkitPart,
  ModelReference,
  defineModel,
  getBasicUsageStats,
  modelRef,
} from '@genkit-ai/ai/model';
import { GENKIT_CLIENT_HEADER } from '@genkit-ai/core';

export const claude35Sonnet = modelRef({
  name: 'vertexai/claude-3-5-sonnet',
  info: {
    label: 'Vertex AI Model Garden - Claude 35 Sonnet',
    versions: ['claude-3-5-sonnet@20240620'],
    supports: {
      multiturn: true,
      media: true,
      tools: false,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const claude3Sonnet = modelRef({
  name: 'vertexai/claude-3-sonnet',
  info: {
    label: 'Vertex AI Model Garden - Claude 3 Sonnet',
    versions: ['claude-3-sonnet@20240229'],
    supports: {
      multiturn: true,
      media: true,
      tools: false,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const claude3Haiku = modelRef({
  name: 'vertexai/claude-3-haiku',
  info: {
    label: 'Vertex AI Model Garden - Claude 3 Haiku',
    versions: ['claude-3-haiku@20240307'],
    supports: {
      multiturn: true,
      media: true,
      tools: false,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const claude3Opus = modelRef({
  name: 'vertexai/claude-3-opus',
  info: {
    label: 'Vertex AI Model Garden - Claude 3 Opus',
    versions: ['claude-3-opus@20240229'],
    supports: {
      multiturn: true,
      media: true,
      tools: false,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const SUPPORTED_ANTHROPIC_MODELS: Record<
  string,
  ModelReference<typeof GenerationCommonConfigSchema>
> = {
  'claude-3-5-sonnet': claude35Sonnet,
  'claude-3-sonnet': claude3Sonnet,
  'claude-3-opus': claude3Opus,
  'claude-3-haiku': claude3Haiku,
};

export function anthropicModel(
  modelName: string,
  projectId: string,
  region: string
) {
  const client = new AnthropicVertex({
    region,
    projectId,
    defaultHeaders: {
      'X-Goog-Api-Client': GENKIT_CLIENT_HEADER,
    },
  });
  const model = SUPPORTED_ANTHROPIC_MODELS[modelName];
  if (!model) {
    throw new Error(`unsupported Anthropic model name ${modelName}`);
  }

  return defineModel(
    {
      name: model.name,
      label: model.info?.label,
      configSchema: GenerationCommonConfigSchema,
      supports: model.info?.supports,
      versions: model.info?.versions,
    },
    async (input, streamingCallback) => {
      if (!streamingCallback) {
        const response = await client.messages.create({
          ...toAnthropicRequest(input.config?.version ?? modelName, input),
          stream: false,
        });
        return fromAnthropicResponse(input, response);
      } else {
        const stream = await client.messages.stream(
          toAnthropicRequest(input.config?.version ?? modelName, input)
        );
        for await (const event of stream) {
          if (event.type === 'content_block_delta') {
            streamingCallback({
              index: 0,
              content: [
                {
                  text: (event.delta as TextDelta).text,
                },
              ],
            });
          }
        }
        return fromAnthropicResponse(input, await stream.finalMessage());
      }
    }
  );
}

export function toAnthropicRequest(
  model: string,
  input: GenerateRequest<typeof GenerationCommonConfigSchema>
): MessageCreateParamsBase {
  let system: string | undefined = undefined;
  const messages: MessageParam[] = [];
  for (const msg of input.messages) {
    if (msg.role === 'system') {
      system = msg.content
        .map((c) => {
          if (!c.text) {
            throw new Error(
              'Only text context is supported for system messages.'
            );
          }
          return c.text;
        })
        .join();
    } else {
      messages.push({
        role: toAnthropicRole(msg.role),
        content: toAnthropicContent(msg.content),
      });
    }
  }
  const request = {
    model,
    messages,
    // https://docs.anthropic.com/claude/docs/models-overview#model-comparison
    max_tokens: input.config?.maxOutputTokens ?? 4096,
  } as MessageCreateParamsBase;
  if (system) {
    request['system'] = system;
  }
  if (input.config?.stopSequences) {
    request.stop_sequences = input.config?.stopSequences;
  }
  if (input.config?.temperature) {
    request.temperature = input.config?.temperature;
  }
  if (input.config?.topK) {
    request.top_k = input.config?.topK;
  }
  if (input.config?.topP) {
    request.top_p = input.config?.topP;
  }
  return request;
}

function toAnthropicContent(
  content: GenkitPart[]
): Array<TextBlockParam | ImageBlockParam> {
  return content.map((p) => {
    if (p.text) {
      return {
        type: 'text',
        text: p.text,
      };
    }
    if (p.media) {
      let b64Data = p.media.url;
      if (b64Data.startsWith('data:')) {
        b64Data = b64Data.substring(b64Data.indexOf(',')! + 1);
      }

      return {
        type: 'image',
        source: {
          type: 'base64',
          data: b64Data,
          media_type: p.media.contentType as
            | 'image/jpeg'
            | 'image/png'
            | 'image/gif'
            | 'image/webp',
        },
      };
    }
    throw new Error(`Unsupported content type: ${p}`);
  });
}

function toAnthropicRole(role): 'user' | 'assistant' {
  if (role === 'model') {
    return 'assistant';
  }
  if (role === 'user') {
    return 'user';
  }
  throw new Error(`Unsupported role type ${role}`);
}

export function fromAnthropicResponse(
  input: GenerateRequest<typeof GenerationCommonConfigSchema>,
  response: Message
): GenerateResponseData {
  const candidates: CandidateData[] = [
    {
      index: 0,
      finishReason: toGenkitFinishReason(
        response.stop_reason as 'end_turn' | 'max_tokens' | 'stop_sequence'
      ),
      custom: {
        id: response.id,
        model: response.model,
        type: response.type,
      },
      message: {
        role: 'model',
        content: response.content.map((c) => ({ text: (c as TextBlock).text })),
      },
    },
  ];
  return {
    candidates,
    usage: {
      ...getBasicUsageStats(input.messages, candidates),
      inputTokens: response.usage.input_tokens,
      outputTokens: response.usage.output_tokens,
    },
  };
}

function toGenkitFinishReason(
  reason: 'end_turn' | 'max_tokens' | 'stop_sequence' | null
): CandidateData['finishReason'] {
  switch (reason) {
    case 'end_turn':
      return 'stop';
    case 'max_tokens':
      return 'length';
    case 'stop_sequence':
      return 'stop';
    case null:
      return 'unknown';
    default:
      return 'other';
  }
}
