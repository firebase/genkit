/**
 * Copyright 2025 Google LLC
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

import type Anthropic from '@anthropic-ai/sdk';
import type {
  Message,
  MessageCreateParams,
  MessageParam,
  MessageStreamEvent,
} from '@anthropic-ai/sdk/resources/messages.mjs';
import * as assert from 'assert';
import type {
  GenerateRequest,
  GenerateResponseData,
  MessageData,
  Part,
  Role,
} from 'genkit';
import type { CandidateData, ToolDefinition } from 'genkit/model';
import { describe, it, mock } from 'node:test';

import type { AnthropicConfigSchema } from '../src/claude.js';
import {
  claudeModel,
  claudeRunner,
  fromAnthropicContentBlockChunk,
  fromAnthropicResponse,
  fromAnthropicStopReason,
  toAnthropicMessageContent,
  toAnthropicMessages,
  toAnthropicRequestBody,
  toAnthropicRole,
  toAnthropicTool,
  toAnthropicToolResponseContent,
} from '../src/claude.js';
import { createMockAnthropicClient } from './mocks/anthropic-client.js';

describe('toAnthropicRole', () => {
  const testCases: {
    genkitRole: Role;
    toolMessageType?: 'tool_use' | 'tool_result';
    expectedAnthropicRole: MessageParam['role'];
  }[] = [
    {
      genkitRole: 'user',
      expectedAnthropicRole: 'user',
    },
    {
      genkitRole: 'model',
      expectedAnthropicRole: 'assistant',
    },
    {
      genkitRole: 'tool',
      toolMessageType: 'tool_use',
      expectedAnthropicRole: 'assistant',
    },
    {
      genkitRole: 'tool',
      toolMessageType: 'tool_result',
      expectedAnthropicRole: 'user',
    },
  ];

  for (const test of testCases) {
    it(`should map Genkit "${test.genkitRole}" role to Anthropic "${test.expectedAnthropicRole}" role${
      test.toolMessageType
        ? ` when toolMessageType is "${test.toolMessageType}"`
        : ''
    }`, () => {
      const actualOutput = toAnthropicRole(
        test.genkitRole,
        test.toolMessageType
      );
      assert.strictEqual(actualOutput, test.expectedAnthropicRole);
    });
  }

  it('should throw an error for unknown roles', () => {
    assert.throws(
      () => toAnthropicRole('unknown' as Role),
      /role unknown doesn't map to an Anthropic role\./
    );
  });
});

describe('toAnthropicToolResponseContent', () => {
  it('should throw an error for unknown parts', () => {
    const part: Part = { data: 'hi' } as Part;
    assert.throws(
      () => toAnthropicToolResponseContent(part),
      /Invalid genkit part provided to toAnthropicToolResponseContent: {"data":"hi"}/
    );
  });
});

describe('toAnthropicMessageContent', () => {
  it('should throw if a media part contains invalid media', () => {
    assert.throws(
      () =>
        toAnthropicMessageContent({
          media: {
            url: '',
          },
        }),
      /Invalid genkit part media provided to toAnthropicMessageContent: {"url":""}/
    );
  });

  it('should throw if the provided part is invalid', () => {
    assert.throws(
      () => toAnthropicMessageContent({ fake: 'part' } as Part),
      /Unsupported genkit part fields encountered for current message role: {"fake":"part"}/
    );
  });
});

describe('toAnthropicMessages', () => {
  const testCases: {
    should: string;
    inputMessages: MessageData[];
    expectedOutput: {
      messages: MessageParam[];
      system?: string;
    };
  }[] = [
    {
      should: 'should transform tool request content correctly',
      inputMessages: [
        {
          role: 'model',
          content: [
            {
              toolRequest: {
                ref: 'toolu_01A09q90qw90lq917835lq9',
                name: 'tellAFunnyJoke',
                input: { topic: 'bob' },
              },
            },
          ],
        },
      ],
      expectedOutput: {
        messages: [
          {
            role: 'assistant',
            content: [
              {
                type: 'tool_use',
                id: 'toolu_01A09q90qw90lq917835lq9',
                name: 'tellAFunnyJoke',
                input: { topic: 'bob' },
              },
            ],
          },
        ],
        system: undefined,
      },
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
      expectedOutput: {
        messages: [
          {
            role: 'user',
            content: [
              {
                type: 'tool_result',
                tool_use_id: 'call_SVDpFV2l2fW88QRFtv85FWwM',
                content: [
                  {
                    type: 'text',
                    text: 'Why did the bob cross the road?',
                  },
                ],
              },
            ],
          },
        ],
        system: undefined,
      },
    },
    {
      should: 'should transform tool response media content correctly',
      inputMessages: [
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                ref: 'call_SVDpFV2l2fW88QRFtv85FWwM',
                name: 'tellAFunnyJoke',
                output: {
                  url: 'data:image/gif;base64,R0lGODlhAQABAAAAACw=',
                  contentType: 'image/gif',
                },
              },
            },
          ],
        },
      ],
      expectedOutput: {
        messages: [
          {
            role: 'user',
            content: [
              {
                type: 'tool_result',
                tool_use_id: 'call_SVDpFV2l2fW88QRFtv85FWwM',
                content: [
                  {
                    type: 'image',
                    source: {
                      type: 'base64',
                      data: 'R0lGODlhAQABAAAAACw=',
                      media_type: 'image/gif',
                    },
                  },
                ],
              },
            ],
          },
        ],
        system: undefined,
      },
    },
    {
      should:
        'should transform tool response base64 image url content correctly',
      inputMessages: [
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                ref: 'call_SVDpFV2l2fW88QRFtv85FWwM',
                name: 'tellAFunnyJoke',
                output: 'data:image/gif;base64,R0lGODlhAQABAAAAACw=',
              },
            },
          ],
        },
      ],
      expectedOutput: {
        messages: [
          {
            role: 'user',
            content: [
              {
                type: 'tool_result',
                tool_use_id: 'call_SVDpFV2l2fW88QRFtv85FWwM',
                content: [
                  {
                    type: 'image',
                    source: {
                      type: 'base64',
                      data: 'R0lGODlhAQABAAAAACw=',
                      media_type: 'image/gif',
                    },
                  },
                ],
              },
            ],
          },
        ],
        system: undefined,
      },
    },
    {
      should: 'should transform text content correctly',
      inputMessages: [
        { role: 'user', content: [{ text: 'hi' }] },
        { role: 'model', content: [{ text: 'how can I help you?' }] },
        { role: 'user', content: [{ text: 'I am testing' }] },
      ],
      expectedOutput: {
        messages: [
          {
            content: [
              {
                text: 'hi',
                type: 'text',
                citations: null,
              },
            ],
            role: 'user',
          },
          {
            content: [
              {
                text: 'how can I help you?',
                type: 'text',
                citations: null,
              },
            ],
            role: 'assistant',
          },
          {
            content: [
              {
                text: 'I am testing',
                type: 'text',
                citations: null,
              },
            ],
            role: 'user',
          },
        ],
        system: undefined,
      },
    },
    {
      should: 'should transform initial system prompt correctly',
      inputMessages: [
        { role: 'system', content: [{ text: 'You are an helpful assistant' }] },
        { role: 'user', content: [{ text: 'hi' }] },
      ],
      expectedOutput: {
        messages: [
          {
            content: [
              {
                text: 'hi',
                type: 'text',
                citations: null,
              },
            ],
            role: 'user',
          },
        ],
        system: 'You are an helpful assistant',
      },
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
                url: 'data:image/gif;base64,R0lGODlhAQABAAAAACw=',
                contentType: 'image/gif',
              },
            },
          ],
        },
      ],
      expectedOutput: {
        messages: [
          {
            content: [
              {
                text: 'describe the following image:',
                type: 'text',
                citations: null,
              },
              {
                source: {
                  type: 'base64',
                  data: 'R0lGODlhAQABAAAAACw=',
                  media_type: 'image/gif',
                },
                type: 'image',
              },
            ],
            role: 'user',
          },
        ],
        system: undefined,
      },
    },
  ];

  for (const test of testCases) {
    it(test.should, () => {
      const actualOutput = toAnthropicMessages(test.inputMessages);
      assert.deepStrictEqual(actualOutput, test.expectedOutput);
    });
  }
});

describe('toAnthropicTool', () => {
  it('should transform Genkit tool definition to an Anthropic tool', () => {
    const tool: ToolDefinition = {
      name: 'tellAJoke',
      description: 'Tell a joke',
      inputSchema: {
        type: 'object',
        properties: {
          topic: { type: 'string' },
        },
        required: ['topic'],
      },
    };
    const actualOutput = toAnthropicTool(tool);
    assert.deepStrictEqual(actualOutput, {
      name: 'tellAJoke',
      description: 'Tell a joke',
      input_schema: {
        type: 'object',
        properties: {
          topic: { type: 'string' },
        },
        required: ['topic'],
      },
    });
  });
});

describe('fromAnthropicContentBlockChunk', () => {
  const testCases: {
    should: string;
    event: MessageStreamEvent;
    expectedOutput: Part | undefined;
  }[] = [
    {
      should: 'should return text part from content_block_start event',
      event: {
        index: 0,
        type: 'content_block_start',
        content_block: {
          type: 'text',
          text: 'Hello, World!',
          citations: null,
        },
      },
      expectedOutput: { text: 'Hello, World!' },
    },
    {
      should: 'should return text delta part from content_block_delta event',
      event: {
        index: 0,
        type: 'content_block_delta',
        delta: {
          type: 'text_delta',
          text: 'Hello, World!',
        },
      },
      expectedOutput: { text: 'Hello, World!' },
    },
    {
      should: 'should return tool use requests',
      event: {
        index: 0,
        type: 'content_block_start',
        content_block: {
          type: 'tool_use',
          id: 'abc123',
          name: 'tellAJoke',
          input: { topic: 'dogs' },
        },
      },
      expectedOutput: {
        toolRequest: {
          name: 'tellAJoke',
          input: { topic: 'dogs' },
          ref: 'abc123',
        },
      },
    },
    {
      should: 'should return undefined for any other event',
      event: {
        type: 'message_stop',
      },
      expectedOutput: undefined,
    },
  ];

  for (const test of testCases) {
    it(test.should, () => {
      const actualOutput = fromAnthropicContentBlockChunk(test.event);
      assert.deepStrictEqual(actualOutput, test.expectedOutput);
    });
  }
});

describe('fromAnthropicStopReason', () => {
  const testCases: {
    inputStopReason: Message['stop_reason'];
    expectedFinishReason: CandidateData['finishReason'];
  }[] = [
    {
      inputStopReason: 'max_tokens',
      expectedFinishReason: 'length',
    },
    {
      inputStopReason: 'end_turn',
      expectedFinishReason: 'stop',
    },
    {
      inputStopReason: 'stop_sequence',
      expectedFinishReason: 'stop',
    },
    {
      inputStopReason: 'tool_use',
      expectedFinishReason: 'stop',
    },
    {
      inputStopReason: null,
      expectedFinishReason: 'unknown',
    },
    {
      inputStopReason: 'unknown' as any,
      expectedFinishReason: 'other',
    },
  ];

  for (const test of testCases) {
    it(`should map Anthropic stop reason "${test.inputStopReason}" to Genkit finish reason "${test.expectedFinishReason}"`, () => {
      const actualOutput = fromAnthropicStopReason(test.inputStopReason);
      assert.strictEqual(actualOutput, test.expectedFinishReason);
    });
  }
});

describe('fromAnthropicResponse', () => {
  const testCases: {
    should: string;
    message: Message;
    expectedOutput: Omit<GenerateResponseData, 'custom'>;
  }[] = [
    {
      should: 'should work with text content',
      message: {
        id: 'abc123',
        model: 'whatever',
        type: 'message',
        role: 'assistant',
        stop_reason: 'max_tokens',
        stop_sequence: null,
        content: [
          {
            type: 'text',
            text: 'Tell a joke about dogs.',
            citations: null,
          },
        ],
        usage: {
          input_tokens: 10,
          output_tokens: 20,
          cache_creation_input_tokens: null,
          cache_read_input_tokens: null,
        },
      },
      expectedOutput: {
        candidates: [
          {
            index: 0,
            finishReason: 'length',
            message: {
              role: 'model',
              content: [{ text: 'Tell a joke about dogs.' }],
            },
          },
        ],
        usage: {
          inputTokens: 10,
          outputTokens: 20,
        },
      },
    },
    {
      should: 'should work with tool use content',
      message: {
        id: 'abc123',
        model: 'whatever',
        type: 'message',
        role: 'assistant',
        stop_reason: 'tool_use',
        stop_sequence: null,
        content: [
          {
            type: 'tool_use',
            id: 'abc123',
            name: 'tellAJoke',
            input: { topic: 'dogs' },
          },
        ],
        usage: {
          input_tokens: 10,
          output_tokens: 20,
          cache_creation_input_tokens: null,
          cache_read_input_tokens: null,
        },
      },
      expectedOutput: {
        candidates: [
          {
            index: 0,
            finishReason: 'stop',
            message: {
              role: 'model',
              content: [
                {
                  toolRequest: {
                    name: 'tellAJoke',
                    input: { topic: 'dogs' },
                    ref: 'abc123',
                  },
                },
              ],
            },
          },
        ],
        usage: {
          inputTokens: 10,
          outputTokens: 20,
        },
      },
    },
  ];

  for (const test of testCases) {
    it(test.should, () => {
      const actualOutput = fromAnthropicResponse(test.message);
      // Check custom field exists and is the message
      assert.ok(actualOutput.custom);
      assert.strictEqual(actualOutput.custom, test.message);
      // Check the rest
      assert.deepStrictEqual(
        {
          candidates: actualOutput.candidates,
          usage: actualOutput.usage,
        },
        test.expectedOutput
      );
    });
  }
});

describe('toAnthropicRequestBody', () => {
  const testCases: {
    should: string;
    modelName: string;
    genkitRequest: GenerateRequest<typeof AnthropicConfigSchema>;
    expectedOutput: MessageCreateParams;
  }[] = [
    {
      should: '(claude-3-5-haiku) handles request with text messages',
      modelName: 'claude-3-5-haiku',
      genkitRequest: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        output: { format: 'text' },
        config: {
          metadata: {
            user_id: 'exampleUser123',
          },
        },
      },
      expectedOutput: {
        max_tokens: 4096,
        messages: [
          {
            content: [
              {
                text: 'Tell a joke about dogs.',
                type: 'text',
                citations: null,
              },
            ],
            role: 'user',
          },
        ],
        model: 'claude-3-5-haiku-latest',
        metadata: {
          user_id: 'exampleUser123',
        },
      },
    },
    {
      should: '(claude-3-haiku) handles request with text messages',
      modelName: 'claude-3-haiku',
      genkitRequest: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        output: { format: 'text' },
        config: {
          metadata: {
            user_id: 'exampleUser123',
          },
        },
      },
      expectedOutput: {
        max_tokens: 4096,
        messages: [
          {
            content: [
              {
                text: 'Tell a joke about dogs.',
                type: 'text',
                citations: null,
              },
            ],
            role: 'user',
          },
        ],
        model: 'claude-3-haiku-20240307',
        metadata: {
          user_id: 'exampleUser123',
        },
      },
    },
  ];
  for (const test of testCases) {
    it(test.should, () => {
      const actualOutput = toAnthropicRequestBody(
        test.modelName,
        test.genkitRequest
      );
      assert.deepStrictEqual(actualOutput, test.expectedOutput);
    });
  }

  it('should throw if model is not supported', () => {
    assert.throws(
      () =>
        toAnthropicRequestBody('fake-model', {
          messages: [],
        } as GenerateRequest<typeof AnthropicConfigSchema>),
      /Unsupported model: fake-model/
    );
  });

  it('should throw if output format is not text', () => {
    assert.throws(
      () =>
        toAnthropicRequestBody('claude-3-5-haiku', {
          messages: [],
          tools: [],
          output: { format: 'media' },
        } as GenerateRequest<typeof AnthropicConfigSchema>),
      /Only text output format is supported for Claude models currently/
    );
  });

  it('should apply system prompt caching when enabled', () => {
    const request: GenerateRequest<typeof AnthropicConfigSchema> = {
      messages: [
        { role: 'system', content: [{ text: 'You are a helpful assistant' }] },
        { role: 'user', content: [{ text: 'Hi' }] },
      ],
      output: { format: 'text' },
    };

    // Test with caching enabled
    const outputWithCaching = toAnthropicRequestBody(
      'claude-3-5-haiku',
      request,
      false,
      true
    );
    assert.deepStrictEqual(outputWithCaching.system, [
      {
        type: 'text',
        text: 'You are a helpful assistant',
        cache_control: { type: 'ephemeral' },
      },
    ]);

    // Test with caching disabled
    const outputWithoutCaching = toAnthropicRequestBody(
      'claude-3-5-haiku',
      request,
      false,
      false
    );
    assert.strictEqual(
      outputWithoutCaching.system,
      'You are a helpful assistant'
    );
  });
});

describe('claudeRunner', () => {
  it('should correctly run non-streaming requests', async () => {
    const mockClient = createMockAnthropicClient({
      messageResponse: {
        content: [{ type: 'text', text: 'response', citations: null }],
        usage: {
          input_tokens: 10,
          output_tokens: 20,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
        },
      },
    });

    const runner = claudeRunner('claude-3-5-haiku', mockClient);
    const abortSignal = new AbortController().signal;
    await runner(
      { messages: [] },
      { streamingRequested: false, sendChunk: () => {}, abortSignal }
    );

    const createStub = mockClient.messages.create as any;
    assert.strictEqual(createStub.mock.calls.length, 1);
    assert.deepStrictEqual(createStub.mock.calls[0].arguments, [
      {
        model: 'claude-3-5-haiku-latest',
        max_tokens: 4096,
      },
      {
        signal: abortSignal,
      },
    ]);
  });

  it('should correctly run streaming requests', async () => {
    const mockClient = createMockAnthropicClient({
      streamChunks: [
        {
          type: 'content_block_start',
          index: 0,
          content_block: {
            type: 'text',
            text: 'res',
          },
        } as MessageStreamEvent,
      ],
      messageResponse: {
        content: [{ type: 'text', text: 'response', citations: null }],
        usage: {
          input_tokens: 10,
          output_tokens: 20,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
        },
      },
    });

    const streamingCallback = mock.fn();
    const runner = claudeRunner('claude-3-5-haiku', mockClient);
    const abortSignal = new AbortController().signal;
    await runner(
      { messages: [] },
      { streamingRequested: true, sendChunk: streamingCallback, abortSignal }
    );

    const streamStub = mockClient.messages.stream as any;
    assert.strictEqual(streamStub.mock.calls.length, 1);
    assert.deepStrictEqual(streamStub.mock.calls[0].arguments, [
      {
        model: 'claude-3-5-haiku-latest',
        max_tokens: 4096,
        stream: true,
      },
      {
        signal: abortSignal,
      },
    ]);
  });
});

describe('claudeModel', () => {
  it('should correctly define supported Claude models', () => {
    const mockClient = createMockAnthropicClient();
    const modelName = 'claude-3-5-haiku';
    const modelAction = claudeModel(modelName, mockClient);

    // Verify the model action is returned
    assert.ok(modelAction);
    assert.strictEqual(typeof modelAction, 'function');
  });

  it('should throw for unsupported models', () => {
    assert.throws(
      () => claudeModel('unsupported-model', {} as Anthropic),
      /Unsupported model: unsupported-model/
    );
  });

  it.todo('should handle streaming with multiple text chunks');

  it.todo('should handle tool use in streaming mode');

  it.todo('should handle streaming errors and partial responses');

  it.todo('should handle abort signal during streaming');
});
