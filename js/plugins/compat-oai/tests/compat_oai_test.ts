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

import { describe, expect, it, jest } from '@jest/globals';
import type {
  GenerateRequest,
  GenerateResponseData,
  MessageData,
  Part,
  Role,
} from 'genkit';
import type OpenAI from 'openai';
import type {
  ChatCompletion,
  ChatCompletionChunk,
  ChatCompletionMessageToolCall,
  ChatCompletionRole,
} from 'openai/resources/index.mjs';

import {
  fromOpenAIChoice,
  fromOpenAIChunkChoice,
  fromOpenAIToolCall,
  ModelRequestBuilder,
  openAIModelRunner,
  toOpenAIMessages,
  toOpenAIRequestBody,
  toOpenAIRole,
  toOpenAITextAndMedia,
} from '../src/model';

jest.mock('@genkit-ai/ai/model', () => ({
  ...(jest.requireActual('@genkit-ai/ai/model') as Record<string, unknown>),
  defineModel: jest.fn(),
}));

describe('toOpenAIRole', () => {
  const testCases: {
    genkitRole: Role;
    expectedOpenAiRole: ChatCompletionRole;
  }[] = [
    {
      genkitRole: 'user',
      expectedOpenAiRole: 'user',
    },
    {
      genkitRole: 'model',
      expectedOpenAiRole: 'assistant',
    },
    {
      genkitRole: 'system',
      expectedOpenAiRole: 'system',
    },
    {
      genkitRole: 'tool',
      expectedOpenAiRole: 'tool',
    },
  ];

  for (const test of testCases) {
    it(`should map Genkit "${test.genkitRole}" role to OpenAI "${test.expectedOpenAiRole}" role`, () => {
      const actualOutput = toOpenAIRole(test.genkitRole);
      expect(actualOutput).toBe(test.expectedOpenAiRole);
    });
  }

  it('should throw an error for unknown roles', () => {
    expect(() => toOpenAIRole('unknown' as Role)).toThrowError(
      "role unknown doesn't map to an OpenAI role."
    );
  });
});

describe('toOpenAiTextAndMedia', () => {
  it('should transform text content correctly', () => {
    const part: Part = { text: 'hi' };
    const actualOutput = toOpenAITextAndMedia(part, 'low');
    expect(actualOutput).toStrictEqual({ type: 'text', text: 'hi' });
  });

  it('should transform media content correctly', () => {
    const part: Part = {
      media: {
        contentType: 'image/jpeg',
        url: 'https://example.com/image.jpg',
      },
    };
    const actualOutput = toOpenAITextAndMedia(part, 'low');
    expect(actualOutput).toStrictEqual({
      type: 'image_url',
      image_url: {
        url: 'https://example.com/image.jpg',
        detail: 'low',
      },
    });
  });

  it('should throw an error for unknown parts', () => {
    const part: Part = { data: 'hi' };
    expect(() => toOpenAITextAndMedia(part, 'low')).toThrowError(
      `Unsupported genkit part fields encountered for current message role: {"data":"hi"}`
    );
  });
});

describe('toOpenAiMessages', () => {
  const testCases = [
    {
      should: 'should transform tool request content correctly',
      inputMessages: [
        {
          role: 'model',
          content: [
            {
              toolRequest: {
                ref: 'call_SVDpFV2l2fW88QRFtv85FWwM',
                name: 'tellAFunnyJoke',
                input: { topic: 'bob' },
              },
            },
          ],
        },
      ],
      expectedOutput: [
        {
          role: 'assistant',
          tool_calls: [
            {
              id: 'call_SVDpFV2l2fW88QRFtv85FWwM',
              type: 'function',
              function: {
                name: 'tellAFunnyJoke',
                arguments: '{"topic":"bob"}',
              },
            },
          ],
        },
      ],
    },
    {
      should: 'should transform tool response text content correctly',
      inputMessages: [
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                ref: 'call_SVDpFV2l2fW88QRFtv85FWwM',
                name: 'tellAFunnyJoke',
                output: 'Why did the bob cross the road?',
              },
            },
          ],
        },
      ],
      expectedOutput: [
        {
          role: 'tool',
          tool_call_id: 'call_SVDpFV2l2fW88QRFtv85FWwM',
          content: 'Why did the bob cross the road?',
        },
      ],
    },
    {
      should: 'should transform tool response json content correctly',
      inputMessages: [
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                ref: 'call_SVDpFV2l2fW88QRFtv85FWwM',
                name: 'tellAFunnyJoke',
                output: { test: 'example' },
              },
            },
          ],
        },
      ],
      expectedOutput: [
        {
          role: 'tool',
          tool_call_id: 'call_SVDpFV2l2fW88QRFtv85FWwM',
          content: JSON.stringify({ test: 'example' }),
        },
      ],
    },
    {
      should: 'should transform text content correctly',
      inputMessages: [
        { role: 'user', content: [{ text: 'hi' }] },
        { role: 'model', content: [{ text: 'how can I help you?' }] },
        { role: 'user', content: [{ text: 'I am testing' }] },
      ],
      expectedOutput: [
        { role: 'user', content: 'hi' },
        { role: 'assistant', content: 'how can I help you?' },
        { role: 'user', content: 'I am testing' },
      ],
    },
    {
      should: 'should transform multi-modal (text + media) content correctly',
      inputMessages: [
        {
          role: 'user',
          content: [
            { text: 'describe the following image:' },
            {
              media: {
                contentType: 'image/jpeg',
                url: 'https://img.freepik.com/free-photo/abstract-autumn-beauty-multi-colored-leaf-vein-pattern-generated-by-ai_188544-9871.jpg?size=626&ext=jpg&ga=GA1.1.735520172.1710720000&semt=ais',
              },
            },
          ],
        },
      ],
      expectedOutput: [
        {
          role: 'user',
          content: [
            { type: 'text', text: 'describe the following image:' },
            {
              type: 'image_url',
              image_url: {
                url: 'https://img.freepik.com/free-photo/abstract-autumn-beauty-multi-colored-leaf-vein-pattern-generated-by-ai_188544-9871.jpg?size=626&ext=jpg&ga=GA1.1.735520172.1710720000&semt=ais',
                detail: 'auto',
              },
            },
          ],
        },
      ],
    },
    {
      should: 'should transform system messages correctly',
      inputMessages: [
        { role: 'system', content: [{ text: 'system message' }] },
      ],
      expectedOutput: [{ role: 'system', content: 'system message' }],
    },
  ];

  for (const test of testCases) {
    it(test.should, () => {
      const actualOutput = toOpenAIMessages(
        test.inputMessages as MessageData[]
      );
      expect(actualOutput).toStrictEqual(test.expectedOutput);
    });
  }
});

describe('fromOpenAiToolCall', () => {
  it('should transform tool call correctly', () => {
    const toolCall: ChatCompletionMessageToolCall = {
      id: 'call_SVDpFV2l2fW88QRFtv85FWwM',
      type: 'function',
      function: {
        name: 'tellAFunnyJoke',
        arguments: '{"topic":"bob"}',
      },
    };
    const actualOutput = fromOpenAIToolCall(toolCall, {
      message: { tool_calls: [toolCall] },
      finish_reason: 'tool_calls',
    } as ChatCompletion.Choice);
    expect(actualOutput).toStrictEqual({
      toolRequest: {
        ref: 'call_SVDpFV2l2fW88QRFtv85FWwM',
        name: 'tellAFunnyJoke',
        input: { topic: 'bob' },
      },
    });
  });

  it('should proxy null-ish arguments', () => {
    const toolCall: ChatCompletionMessageToolCall = {
      id: 'call_SVDpFV2l2fW88QRFtv85FWwM',
      type: 'function',
      function: {
        name: 'tellAFunnyJoke',
        arguments: '',
      },
    };
    const actualOutput = fromOpenAIToolCall(toolCall, {
      message: { tool_calls: [toolCall] },
      finish_reason: 'tool_calls',
    } as ChatCompletion.Choice);
    expect(actualOutput).toStrictEqual({
      toolRequest: {
        ref: 'call_SVDpFV2l2fW88QRFtv85FWwM',
        name: 'tellAFunnyJoke',
        input: '',
      },
    });
  });

  it('should throw an error if tool call is missing required fields', () => {
    const toolCall: ChatCompletionMessageToolCall = {
      id: 'call_SVDpFV2l2fW88QRFtv85FWwM',
      type: 'function',
      function: undefined as any,
    };

    expect(() =>
      fromOpenAIToolCall(toolCall, {
        message: { tool_calls: [toolCall] },
        finish_reason: 'tool_calls',
      } as ChatCompletion.Choice)
    ).toThrowError(
      'Unexpected openAI chunk choice. tool_calls was provided but one or more tool_calls is missing.'
    );
  });
});

describe('fromOpenAiChoice', () => {
  const testCases: {
    should: string;
    choice: ChatCompletion.Choice;
    jsonMode?: boolean;
    expectedOutput: GenerateResponseData;
  }[] = [
    {
      should: 'should work with text',
      choice: {
        index: 0,
        message: {
          role: 'assistant',
          content: 'Tell a joke about dogs.',
          refusal: null,
        },
        finish_reason: 'whatever' as any,
        logprobs: null,
      },
      expectedOutput: {
        finishReason: 'other',
        message: {
          role: 'model',
          content: [{ text: 'Tell a joke about dogs.' }],
        },
      },
    },
    {
      should: 'should work with json',
      choice: {
        index: 0,
        message: {
          role: 'assistant',
          content: JSON.stringify({ json: 'test' }),
          refusal: null,
        },
        finish_reason: 'content_filter',
        logprobs: null,
      },
      jsonMode: true,
      expectedOutput: {
        finishReason: 'blocked',
        message: {
          role: 'model',
          content: [{ data: { json: 'test' } }],
        },
      },
    },
    {
      should: 'should work with tools',
      choice: {
        index: 0,
        message: {
          role: 'assistant',
          content: 'Tool call',
          refusal: null,
          tool_calls: [
            {
              id: 'ref123',
              type: 'function',
              function: {
                name: 'exampleTool',
                arguments: JSON.stringify({ param: 'value' }),
              },
            },
          ],
        },
        finish_reason: 'tool_calls',
        logprobs: null,
      },
      expectedOutput: {
        message: {
          role: 'model',
          content: [
            {
              toolRequest: {
                name: 'exampleTool',
                input: { param: 'value' },
                ref: 'ref123',
              },
            },
          ],
        },
        finishReason: 'stop',
      },
    },
  ];

  for (const test of testCases) {
    it(test.should, () => {
      const actualOutput = fromOpenAIChoice(test.choice, test.jsonMode);
      expect(actualOutput).toStrictEqual(test.expectedOutput);
    });
  }
});

describe('fromOpenAiChunkChoice', () => {
  const testCases: {
    should: string;
    chunkChoice: ChatCompletionChunk.Choice;
    jsonMode?: boolean;
    expectedOutput: GenerateResponseData;
  }[] = [
    {
      should: 'should work with text',
      chunkChoice: {
        index: 0,
        delta: {
          role: 'assistant',
          content: 'Tell a joke about dogs.',
        },
        finish_reason: 'whatever' as any,
      },
      expectedOutput: {
        finishReason: 'other',
        message: {
          role: 'model',
          content: [{ text: 'Tell a joke about dogs.' }],
        },
      },
    },
    {
      should: 'should work with json',
      chunkChoice: {
        index: 0,
        delta: {
          role: 'assistant',
          content: JSON.stringify({ json: 'test' }),
        },
        finish_reason: null,
        logprobs: null,
      },
      jsonMode: true,
      expectedOutput: {
        finishReason: 'unknown',
        message: {
          role: 'model',
          content: [{ data: { json: 'test' } }],
        },
      },
    },
    {
      should: 'should work with tools',
      chunkChoice: {
        index: 0,
        delta: {
          role: 'assistant',
          content: 'Tool call',
          tool_calls: [
            {
              index: 0,
              id: 'ref123',
              function: {
                name: 'exampleTool',
                arguments: JSON.stringify({ param: 'value' }),
              },
            },
          ],
        },
        finish_reason: 'tool_calls',
      },
      expectedOutput: {
        message: {
          role: 'model',
          content: [
            {
              toolRequest: {
                name: 'exampleTool',
                input: { param: 'value' },
                ref: 'ref123',
              },
            },
          ],
        },
        finishReason: 'stop',
      },
    },
  ];

  for (const test of testCases) {
    it(test.should, () => {
      const actualOutput = fromOpenAIChunkChoice(
        test.chunkChoice,
        test.jsonMode
      );
      expect(actualOutput).toStrictEqual(test.expectedOutput);
    });
  }
});

describe('toOpenAiRequestBody', () => {
  const testCases = [
    {
      should: '(gpt-3.5-turbo) handles request with text messages',
      modelName: 'gpt-3.5-turbo',
      genkitRequest: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        tools: [],
        output: { format: 'text' },
        config: {
          topP: 1,
          frequency_penalty: 0.7,
          logit_bias: {
            science: 12,
            technology: 8,
            politics: -5,
            sports: 3,
          },
          logprobs: true,
          presence_penalty: -0.3,
          seed: 42,
          top_logprobs: 10,
          user: 'exampleUser123',
        },
      },
      expectedOutput: {
        messages: [
          {
            role: 'user',
            content: 'Tell a joke about dogs.',
          },
        ],
        model: 'gpt-3.5-turbo',
        response_format: { type: 'text' },
        top_p: 1,
        frequency_penalty: 0.7,
        logit_bias: {
          science: 12,
          technology: 8,
          politics: -5,
          sports: 3,
        },
        logprobs: true,
        presence_penalty: -0.3,
        seed: 42,
        top_logprobs: 10,
        user: 'exampleUser123',
      },
    },
    {
      should: '(gpt-3.5-turbo) handles request with text messages and tools',
      modelName: 'gpt-3.5-turbo',
      genkitRequest: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
          {
            role: 'model',
            content: [
              {
                toolRequest: {
                  ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                  name: 'tellAFunnyJoke',
                  input: { topic: 'dogs' },
                },
              },
            ],
          },
          {
            role: 'tool',
            content: [
              {
                toolResponse: {
                  ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                  name: 'tellAFunnyJoke',
                  output: 'Why did the dogs cross the road?',
                },
              },
            ],
          },
        ],
        tools: [
          {
            name: 'tellAFunnyJoke',
            description:
              'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
            inputSchema: {
              type: 'object',
              properties: { topic: { type: 'string' } },
              required: ['topic'],
              additionalProperties: false,
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
            outputSchema: {
              type: 'string',
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
        ],
        output: { format: 'text' },
      },
      expectedOutput: {
        messages: [
          {
            role: 'user',
            content: 'Tell a joke about dogs.',
          },
          {
            role: 'assistant',
            tool_calls: [
              {
                id: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                type: 'function',
                function: {
                  name: 'tellAFunnyJoke',
                  arguments: '{"topic":"dogs"}',
                },
              },
            ],
          },
          {
            role: 'tool',
            tool_call_id: 'call_yTnDw3xY3KH3pkvDvccCizn1',
            content: 'Why did the dogs cross the road?',
          },
        ],
        tools: [
          {
            type: 'function',
            function: {
              name: 'tellAFunnyJoke',
              parameters: {
                type: 'object',
                properties: { topic: { type: 'string' } },
                required: ['topic'],
                additionalProperties: false,
                $schema: 'http://json-schema.org/draft-07/schema#',
              },
            },
          },
        ],
        model: 'gpt-3.5-turbo',
        response_format: {
          type: 'text',
        },
      },
    },
    {
      should: '(gpt-3.5-turbo) sets response_format if output.format=json',
      modelName: 'gpt-3.5-turbo',
      genkitRequest: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
          {
            role: 'model',
            content: [
              {
                toolRequest: {
                  ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                  name: 'tellAFunnyJoke',
                  input: { topic: 'dogs' },
                },
              },
            ],
          },
          {
            role: 'tool',
            content: [
              {
                toolResponse: {
                  ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                  name: 'tellAFunnyJoke',
                  output: 'Why did the dogs cross the road?',
                },
              },
            ],
          },
        ],
        tools: [
          {
            name: 'tellAFunnyJoke',
            description:
              'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
            inputSchema: {
              type: 'object',
              properties: { topic: { type: 'string' } },
              required: ['topic'],
              additionalProperties: false,
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
            outputSchema: {
              type: 'string',
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
        ],
        output: { format: 'json' },
      },
      expectedOutput: {
        messages: [
          {
            role: 'user',
            content: 'Tell a joke about dogs.',
          },
          {
            role: 'assistant',
            tool_calls: [
              {
                id: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                type: 'function',
                function: {
                  name: 'tellAFunnyJoke',
                  arguments: '{"topic":"dogs"}',
                },
              },
            ],
          },
          {
            role: 'tool',
            tool_call_id: 'call_yTnDw3xY3KH3pkvDvccCizn1',
            content: 'Why did the dogs cross the road?',
          },
        ],
        tools: [
          {
            type: 'function',
            function: {
              name: 'tellAFunnyJoke',
              parameters: {
                type: 'object',
                properties: { topic: { type: 'string' } },
                required: ['topic'],
                additionalProperties: false,
                $schema: 'http://json-schema.org/draft-07/schema#',
              },
            },
          },
        ],
        model: 'gpt-3.5-turbo',
        response_format: { type: 'json_object' },
      },
    },
    {
      should: '(gpt-4-turbo) sets response_format if output.format=json',
      modelName: 'gpt-4-turbo',
      genkitRequest: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
          {
            role: 'model',
            content: [
              {
                toolRequest: {
                  ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                  name: 'tellAFunnyJoke',
                  input: { topic: 'dogs' },
                },
              },
            ],
          },
          {
            role: 'tool',
            content: [
              {
                toolResponse: {
                  ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                  name: 'tellAFunnyJoke',
                  output: 'Why did the dogs cross the road?',
                },
              },
            ],
          },
        ],
        tools: [
          {
            name: 'tellAFunnyJoke',
            description:
              'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
            inputSchema: {
              type: 'object',
              properties: { topic: { type: 'string' } },
              required: ['topic'],
              additionalProperties: false,
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
            outputSchema: {
              type: 'string',
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
        ],
        output: { format: 'json' },
      },
      expectedOutput: {
        messages: [
          {
            role: 'user',
            content: 'Tell a joke about dogs.',
          },
          {
            role: 'assistant',
            tool_calls: [
              {
                id: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                type: 'function',
                function: {
                  name: 'tellAFunnyJoke',
                  arguments: '{"topic":"dogs"}',
                },
              },
            ],
          },
          {
            role: 'tool',
            tool_call_id: 'call_yTnDw3xY3KH3pkvDvccCizn1',
            content: 'Why did the dogs cross the road?',
          },
        ],
        tools: [
          {
            type: 'function',
            function: {
              name: 'tellAFunnyJoke',
              parameters: {
                type: 'object',
                properties: { topic: { type: 'string' } },
                required: ['topic'],
                additionalProperties: false,
                $schema: 'http://json-schema.org/draft-07/schema#',
              },
            },
          },
        ],
        model: 'gpt-4-turbo',
        response_format: { type: 'json_object' },
      },
    },
    {
      should: '(gpt-4o) sets response_format if output.format=json',
      modelName: 'gpt-4o',
      genkitRequest: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
          {
            role: 'model',
            content: [
              {
                toolRequest: {
                  ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                  name: 'tellAFunnyJoke',
                  input: { topic: 'dogs' },
                },
              },
            ],
          },
          {
            role: 'tool',
            content: [
              {
                toolResponse: {
                  ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                  name: 'tellAFunnyJoke',
                  output: 'Why did the dogs cross the road?',
                },
              },
            ],
          },
        ],
        tools: [
          {
            name: 'tellAFunnyJoke',
            description:
              'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
            inputSchema: {
              type: 'object',
              properties: { topic: { type: 'string' } },
              required: ['topic'],
              additionalProperties: false,
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
            outputSchema: {
              type: 'string',
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
        ],
        output: { format: 'json' },
      },
      expectedOutput: {
        messages: [
          {
            role: 'user',
            content: 'Tell a joke about dogs.',
          },
          {
            role: 'assistant',
            tool_calls: [
              {
                id: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                type: 'function',
                function: {
                  name: 'tellAFunnyJoke',
                  arguments: '{"topic":"dogs"}',
                },
              },
            ],
          },
          {
            role: 'tool',
            tool_call_id: 'call_yTnDw3xY3KH3pkvDvccCizn1',
            content: 'Why did the dogs cross the road?',
          },
        ],
        tools: [
          {
            type: 'function',
            function: {
              name: 'tellAFunnyJoke',
              parameters: {
                type: 'object',
                properties: { topic: { type: 'string' } },
                required: ['topic'],
                additionalProperties: false,
                $schema: 'http://json-schema.org/draft-07/schema#',
              },
            },
          },
        ],
        model: 'gpt-4o',
        response_format: { type: 'json_object' },
      },
    },
  ];
  for (const test of testCases) {
    it(test.should, () => {
      const actualOutput = toOpenAIRequestBody(
        test.modelName,
        test.genkitRequest as GenerateRequest
      );
      expect(actualOutput).toStrictEqual(test.expectedOutput);
    });
  }

  it('(gpt4) does NOT set response_format in openai request body', () => {
    // In either case - output.format='json' or output.format='text' - do NOT set response_format in the OpenAI request body explicitly.
    const modelName = 'gpt-4';
    const genkitRequestTextFormat = {
      messages: [
        { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        {
          role: 'model',
          content: [
            {
              toolRequest: {
                ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                name: 'tellAFunnyJoke',
                input: { topic: 'dogs' },
              },
            },
          ],
        },
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                name: 'tellAFunnyJoke',
                output: 'Why did the dogs cross the road?',
              },
            },
          ],
        },
      ],
      tools: [
        {
          name: 'tellAFunnyJoke',
          description:
            'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
          inputSchema: {
            type: 'object',
            properties: { topic: { type: 'string' } },
            required: ['topic'],
            additionalProperties: false,
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
          outputSchema: {
            type: 'string',
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
        },
      ],
      output: { format: 'text' },
    };
    const genkitRequestJsonFormat = {
      messages: [
        { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        {
          role: 'model',
          content: [
            {
              toolRequest: {
                ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                name: 'tellAFunnyJoke',
                input: { topic: 'dogs' },
              },
            },
          ],
        },
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                name: 'tellAFunnyJoke',
                output: 'Why did the dogs cross the road?',
              },
            },
          ],
        },
      ],
      tools: [
        {
          name: 'tellAFunnyJoke',
          description:
            'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
          inputSchema: {
            type: 'object',
            properties: { topic: { type: 'string' } },
            required: ['topic'],
            additionalProperties: false,
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
          outputSchema: {
            type: 'string',
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
        },
      ],
      output: { format: 'json' },
    };
    const expectedOutput = {
      messages: [
        {
          role: 'user',
          content: 'Tell a joke about dogs.',
        },
        {
          role: 'assistant',
          tool_calls: [
            {
              id: 'call_yTnDw3xY3KH3pkvDvccCizn1',
              type: 'function',
              function: {
                name: 'tellAFunnyJoke',
                arguments: '{"topic":"dogs"}',
              },
            },
          ],
        },
        {
          role: 'tool',
          tool_call_id: 'call_yTnDw3xY3KH3pkvDvccCizn1',
          content: 'Why did the dogs cross the road?',
        },
      ],
      tools: [
        {
          type: 'function',
          function: {
            name: 'tellAFunnyJoke',
            parameters: {
              type: 'object',
              properties: { topic: { type: 'string' } },
              required: ['topic'],
              additionalProperties: false,
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
        },
      ],
      model: 'gpt-4',
    };
    const actualOutput1 = toOpenAIRequestBody(
      modelName,
      genkitRequestTextFormat as GenerateRequest
    );
    const actualOutput2 = toOpenAIRequestBody(
      modelName,
      genkitRequestJsonFormat as GenerateRequest
    );
    expect(actualOutput1).toStrictEqual({
      ...expectedOutput,
      response_format: {
        type: 'text',
      },
    });
    expect(actualOutput2).toStrictEqual({
      ...expectedOutput,
      response_format: {
        type: 'json_object',
      },
    });
  });
  it('(gpt4-vision) sets response_format in openai request body', () => {
    // In either case - output.format='json' or output.format='text' - do NOT set response_format in the OpenAI request body explicitly.
    const modelName = 'gpt-4-vision';
    const genkitRequestTextFormat = {
      messages: [
        { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        {
          role: 'model',
          content: [
            {
              toolRequest: {
                ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                name: 'tellAFunnyJoke',
                input: { topic: 'dogs' },
              },
            },
          ],
        },
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                name: 'tellAFunnyJoke',
                output: 'Why did the dogs cross the road?',
              },
            },
          ],
        },
      ],
      tools: [
        {
          name: 'tellAFunnyJoke',
          description:
            'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
          inputSchema: {
            type: 'object',
            properties: { topic: { type: 'string' } },
            required: ['topic'],
            additionalProperties: false,
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
          outputSchema: {
            type: 'string',
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
        },
      ],
      output: { format: 'text' },
    };
    const genkitRequestJsonFormat = {
      messages: [
        { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        {
          role: 'model',
          content: [
            {
              toolRequest: {
                ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                name: 'tellAFunnyJoke',
                input: { topic: 'dogs' },
              },
            },
          ],
        },
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                ref: 'call_yTnDw3xY3KH3pkvDvccCizn1',
                name: 'tellAFunnyJoke',
                output: 'Why did the dogs cross the road?',
              },
            },
          ],
        },
      ],
      tools: [
        {
          name: 'tellAFunnyJoke',
          description:
            'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
          inputSchema: {
            type: 'object',
            properties: { topic: { type: 'string' } },
            required: ['topic'],
            additionalProperties: false,
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
          outputSchema: {
            type: 'string',
            $schema: 'http://json-schema.org/draft-07/schema#',
          },
        },
      ],
      output: { format: 'json' },
    };
    const expectedOutput = {
      messages: [
        {
          role: 'user',
          content: 'Tell a joke about dogs.',
        },
        {
          role: 'assistant',
          tool_calls: [
            {
              id: 'call_yTnDw3xY3KH3pkvDvccCizn1',
              type: 'function',
              function: {
                name: 'tellAFunnyJoke',
                arguments: '{"topic":"dogs"}',
              },
            },
          ],
        },
        {
          role: 'tool',
          tool_call_id: 'call_yTnDw3xY3KH3pkvDvccCizn1',
          content: 'Why did the dogs cross the road?',
        },
      ],
      tools: [
        {
          type: 'function',
          function: {
            name: 'tellAFunnyJoke',
            parameters: {
              type: 'object',
              properties: { topic: { type: 'string' } },
              required: ['topic'],
              additionalProperties: false,
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
        },
      ],
      model: 'gpt-4-vision',
    };
    const actualOutput1 = toOpenAIRequestBody(
      modelName,
      genkitRequestTextFormat as GenerateRequest
    );
    const actualOutput2 = toOpenAIRequestBody(
      modelName,
      genkitRequestJsonFormat as GenerateRequest
    );
    expect(actualOutput1).toStrictEqual({
      ...expectedOutput,
      response_format: {
        type: 'text',
      },
    });
    expect(actualOutput2).toStrictEqual({
      ...expectedOutput,
      response_format: {
        type: 'json_object',
      },
    });
  });
});

describe('openAIModelRunner', () => {
  it('should correctly run non-streaming requests', async () => {
    const openaiClient = {
      chat: {
        completions: {
          create: jest.fn(async () => ({
            choices: [{ message: { content: 'response' } }],
          })),
        },
      },
    };
    const runner = openAIModelRunner(
      'gpt-4o',
      openaiClient as unknown as OpenAI
    );
    await runner({ messages: [] });
    expect(openaiClient.chat.completions.create).toHaveBeenCalledWith(
      {
        model: 'gpt-4o',
      },
      { signal: undefined }
    );
  });

  it('should correctly run streaming requests', async () => {
    const openaiClient = {
      beta: {
        chat: {
          completions: {
            stream: jest.fn(
              () =>
                // Simulate OpenAI SDK request streaming
                new (class {
                  isFirstRequest = true;
                  [Symbol.asyncIterator]() {
                    return {
                      next: async () => {
                        const returnValue = this.isFirstRequest
                          ? {
                              value: {
                                choices: [{ delta: { content: 'response' } }],
                              },
                              done: false,
                            }
                          : { done: true };
                        this.isFirstRequest = false;
                        return returnValue;
                      },
                    };
                  }
                  async finalChatCompletion() {
                    return { choices: [{ message: { content: 'response' } }] };
                  }
                })()
            ),
          },
        },
      },
    };
    const sendChunk = jest.fn();
    const abortSignal = jest.fn();
    const runner = openAIModelRunner(
      'gpt-4o',
      openaiClient as unknown as OpenAI
    );
    await runner(
      { messages: [] },
      {
        sendChunk,
        streamingRequested: true,
        abortSignal: abortSignal as unknown as AbortSignal,
      }
    );
    expect(openaiClient.beta.chat.completions.stream).toHaveBeenCalledWith(
      {
        model: 'gpt-4o',
        stream: true,
        stream_options: {
          include_usage: true,
        },
      },
      { signal: abortSignal }
    );
  });

  it('should run with requestBuilder', async () => {
    const openaiClient = {
      chat: {
        completions: {
          create: jest.fn(async () => ({
            choices: [{ message: { content: 'response' } }],
          })),
        },
      },
    };
    const requestBuilder: ModelRequestBuilder = (req, params) => {
      (params as any).foo = 'bar';
    };
    const runner = openAIModelRunner(
      'gpt-4o',
      openaiClient as unknown as OpenAI,
      requestBuilder
    );
    await runner({ messages: [], config: { temperature: 0.1 } });
    expect(openaiClient.chat.completions.create).toHaveBeenCalledWith(
      {
        model: 'gpt-4o',
        foo: 'bar',
        temperature: 0.1,
      },
      { signal: undefined }
    );
  });
});
