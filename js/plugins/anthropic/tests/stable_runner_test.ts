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

import { claudeModel, claudeRunner } from '../src/models.js';
import { Runner } from '../src/runner/stable.js';
import type { AnthropicConfigSchema } from '../src/types.js';
import {
  createMockAnthropicClient,
  mockContentBlockStart,
  mockTextChunk,
} from './mocks/anthropic-client.js';

// Test helper: Create a Runner instance for testing converter methods
// Type interface to access protected methods in tests
type RunnerProtectedMethods = {
  toAnthropicRole: (
    role: Role,
    toolMessageType?: 'tool_use' | 'tool_result'
  ) => 'user' | 'assistant';
  toAnthropicToolResponseContent: (part: Part) => any;
  toAnthropicMessageContent: (part: Part) => any;
  toAnthropicMessages: (messages: MessageData[]) => {
    system?: string;
    messages: any[];
  };
  toAnthropicTool: (tool: ToolDefinition) => any;
  toAnthropicRequestBody: (
    modelName: string,
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    cacheSystemPrompt?: boolean
  ) => any;
  toAnthropicStreamingRequestBody: (
    modelName: string,
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    cacheSystemPrompt?: boolean
  ) => any;
  fromAnthropicContentBlockChunk: (
    event: MessageStreamEvent
  ) => Part | undefined;
  fromAnthropicStopReason: (reason: Message['stop_reason']) => any;
  fromAnthropicResponse: (message: Message) => GenerateResponseData;
};

const mockClient = createMockAnthropicClient();
const testRunner = new Runner('test-model', mockClient) as Runner &
  RunnerProtectedMethods;

const createUsage = (
  overrides: Partial<Message['usage']> = {}
): Message['usage'] => ({
  cache_creation: null,
  cache_creation_input_tokens: 0,
  cache_read_input_tokens: 0,
  input_tokens: 0,
  output_tokens: 0,
  server_tool_use: null,
  service_tier: null,
  ...overrides,
});

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
      const actualOutput = testRunner.toAnthropicRole(
        test.genkitRole,
        test.toolMessageType
      );
      assert.strictEqual(actualOutput, test.expectedAnthropicRole);
    });
  }

  it('should throw an error for unknown roles', () => {
    assert.throws(
      () => testRunner.toAnthropicRole('unknown' as Role),
      /Unsupported genkit role: unknown/
    );
  });
});

describe('toAnthropicToolResponseContent', () => {
  it('should not throw for parts without toolResponse', () => {
    // toAnthropicToolResponseContent expects part.toolResponse to exist
    // but will just return stringified undefined/empty object if not
    const part: Part = { data: 'hi' } as Part;
    const result = testRunner.toAnthropicToolResponseContent(part);
    assert.ok(result);
    assert.strictEqual(result.type, 'text');
  });
});

describe('toAnthropicMessageContent', () => {
  it('should throw if a media part contains invalid media', () => {
    assert.throws(
      () =>
        testRunner.toAnthropicMessageContent({
          media: {
            url: '',
          },
        }),
      /Invalid genkit part media provided to toAnthropicMessageContent: {"url":""}/
    );
  });

  it('should throw if the provided part is invalid', () => {
    assert.throws(
      () => testRunner.toAnthropicMessageContent({ fake: 'part' } as Part),
      /Unsupported genkit part fields encountered for current message role: {"fake":"part"}/
    );
  });

  it('should throw if media with file URL cannot be processed as image', () => {
    // File URLs without contentType cannot be processed (they're not data URLs)
    // This will fall through to image handling which requires data URLs
    assert.throws(
      () =>
        testRunner.toAnthropicMessageContent({
          media: {
            url: 'https://example.com/document.pdf',
            // contentType missing - won't be recognized as PDF
          },
        }),
      /Invalid genkit part media provided to toAnthropicMessageContent/
    );
  });

  it('should handle PDF with base64 data URL correctly', () => {
    const result = testRunner.toAnthropicMessageContent({
      media: {
        url: 'data:application/pdf;base64,JVBERi0xLjQKJ',
        contentType: 'application/pdf',
      },
    });

    assert.deepStrictEqual(result, {
      type: 'document',
      source: {
        type: 'base64',
        media_type: 'application/pdf',
        data: 'JVBERi0xLjQKJ',
      },
    });
  });

  it('should handle PDF with HTTP/HTTPS URL correctly', () => {
    const result = testRunner.toAnthropicMessageContent({
      media: {
        url: 'https://example.com/document.pdf',
        contentType: 'application/pdf',
      },
    });

    assert.deepStrictEqual(result, {
      type: 'document',
      source: {
        type: 'url',
        url: 'https://example.com/document.pdf',
      },
    });
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
    {
      should: 'should transform PDF with base64 data URL correctly',
      inputMessages: [
        {
          role: 'user',
          content: [
            {
              media: {
                url: 'data:application/pdf;base64,JVBERi0xLjQKJ',
                contentType: 'application/pdf',
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
                type: 'document',
                source: {
                  type: 'base64',
                  media_type: 'application/pdf',
                  data: 'JVBERi0xLjQKJ',
                },
              },
            ],
            role: 'user',
          },
        ],
        system: undefined,
      },
    },
    {
      should: 'should transform PDF with HTTP/HTTPS URL correctly',
      inputMessages: [
        {
          role: 'user',
          content: [
            {
              media: {
                url: 'https://example.com/document.pdf',
                contentType: 'application/pdf',
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
                type: 'document',
                source: {
                  type: 'url',
                  url: 'https://example.com/document.pdf',
                },
              },
            ],
            role: 'user',
          },
        ],
        system: undefined,
      },
    },
    {
      should: 'should transform PDF alongside text and images correctly',
      inputMessages: [
        {
          role: 'user',
          content: [
            { text: 'Analyze this PDF and image:' },
            {
              media: {
                url: 'data:application/pdf;base64,JVBERi0xLjQKJ',
                contentType: 'application/pdf',
              },
            },
            {
              media: {
                url: 'data:image/png;base64,R0lGODlhAQABAAAAACw=',
                contentType: 'image/png',
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
                text: 'Analyze this PDF and image:',
                type: 'text',
                citations: null,
              },
              {
                type: 'document',
                source: {
                  type: 'base64',
                  media_type: 'application/pdf',
                  data: 'JVBERi0xLjQKJ',
                },
              },
              {
                source: {
                  type: 'base64',
                  data: 'R0lGODlhAQABAAAAACw=',
                  media_type: 'image/png',
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
      const actualOutput = testRunner.toAnthropicMessages(test.inputMessages);
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
    const actualOutput = testRunner.toAnthropicTool(tool);
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
      const actualOutput = testRunner.fromAnthropicContentBlockChunk(
        test.event
      );
      assert.deepStrictEqual(actualOutput, test.expectedOutput);
    });
  }

  it('should throw for unsupported tool input streaming deltas', () => {
    assert.throws(
      () =>
        testRunner.fromAnthropicContentBlockChunk({
          index: 0,
          type: 'content_block_delta',
          delta: {
            type: 'input_json_delta',
            partial_json: '{"foo":',
          },
        } as MessageStreamEvent),
      /Anthropic streaming tool input \(input_json_delta\) is not yet supported/
    );
  });
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
      const actualOutput = testRunner.fromAnthropicStopReason(
        test.inputStopReason
      );
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
        usage: createUsage({
          input_tokens: 10,
          output_tokens: 20,
          cache_creation_input_tokens: null,
          cache_read_input_tokens: null,
        }),
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
        usage: createUsage({
          input_tokens: 10,
          output_tokens: 20,
          cache_creation_input_tokens: null,
          cache_read_input_tokens: null,
        }),
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
      const actualOutput = testRunner.fromAnthropicResponse(test.message);
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
      const actualOutput = testRunner.toAnthropicRequestBody(
        test.modelName,
        test.genkitRequest
      );
      assert.deepStrictEqual(actualOutput, test.expectedOutput);
    });
  }

  it('should accept any model name and use it directly', () => {
    // Following Google GenAI pattern: accept any model name, let API validate
    const result = testRunner.toAnthropicRequestBody('fake-model', {
      messages: [],
    } as GenerateRequest<typeof AnthropicConfigSchema>);

    // Should not throw, and should use the model name directly
    assert.strictEqual(result.model, 'fake-model');
  });

  it('should throw if output format is not text', () => {
    assert.throws(
      () =>
        testRunner.toAnthropicRequestBody('claude-3-5-haiku', {
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
    const outputWithCaching = testRunner.toAnthropicRequestBody(
      'claude-3-5-haiku',
      request,
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
    const outputWithoutCaching = testRunner.toAnthropicRequestBody(
      'claude-3-5-haiku',
      request,
      false
    );
    assert.strictEqual(
      outputWithoutCaching.system,
      'You are a helpful assistant'
    );
  });
});

describe('toAnthropicStreamingRequestBody', () => {
  it('should set stream to true', () => {
    const request: GenerateRequest<typeof AnthropicConfigSchema> = {
      messages: [{ role: 'user', content: [{ text: 'Hello' }] }],
      output: { format: 'text' },
    };

    const output = testRunner.toAnthropicStreamingRequestBody(
      'claude-3-5-haiku',
      request
    );

    assert.strictEqual(output.stream, true);
    assert.strictEqual(output.model, 'claude-3-5-haiku-latest');
    assert.strictEqual(output.max_tokens, 4096);
  });

  it('should support system prompt caching in streaming mode', () => {
    const request: GenerateRequest<typeof AnthropicConfigSchema> = {
      messages: [
        { role: 'system', content: [{ text: 'You are a helpful assistant' }] },
        { role: 'user', content: [{ text: 'Hello' }] },
      ],
      output: { format: 'text' },
    };

    const outputWithCaching = testRunner.toAnthropicStreamingRequestBody(
      'claude-3-5-haiku',
      request,
      true
    );
    assert.deepStrictEqual(outputWithCaching.system, [
      {
        type: 'text',
        text: 'You are a helpful assistant',
        cache_control: { type: 'ephemeral' },
      },
    ]);
    assert.strictEqual(outputWithCaching.stream, true);

    const outputWithoutCaching = testRunner.toAnthropicStreamingRequestBody(
      'claude-3-5-haiku',
      request,
      false
    );
    assert.strictEqual(
      outputWithoutCaching.system,
      'You are a helpful assistant'
    );
    assert.strictEqual(outputWithoutCaching.stream, true);
  });
});

describe('claudeRunner', () => {
  it('should correctly run non-streaming requests', async () => {
    const mockClient = createMockAnthropicClient({
      messageResponse: {
        content: [{ type: 'text', text: 'response', citations: null }],
        usage: createUsage({
          input_tokens: 10,
          output_tokens: 20,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
        }),
      },
    });

    const runner = claudeRunner({
      name: 'claude-3-5-haiku',
      client: mockClient,
    });
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
        messages: [],
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
        usage: createUsage({
          input_tokens: 10,
          output_tokens: 20,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
        }),
      },
    });

    const streamingCallback = mock.fn();
    const runner = claudeRunner({
      name: 'claude-3-5-haiku',
      client: mockClient,
    });
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
        messages: [],
        stream: true,
      },
      {
        signal: abortSignal,
      },
    ]);
  });

  it('should use beta API when apiVersion is beta', async () => {
    const mockClient = createMockAnthropicClient({
      messageResponse: {
        content: [{ type: 'text', text: 'response', citations: null }],
        usage: createUsage({
          input_tokens: 10,
          output_tokens: 20,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
        }),
      },
    });

    const runner = claudeRunner({
      name: 'claude-3-5-haiku',
      client: mockClient,
    });
    const abortSignal = new AbortController().signal;
    await runner(
      {
        messages: [],
        config: { apiVersion: 'beta' },
      },
      { streamingRequested: false, sendChunk: () => {}, abortSignal }
    );

    const betaCreateStub = mockClient.beta.messages.create as any;
    assert.strictEqual(betaCreateStub.mock.calls.length, 1);

    const regularCreateStub = mockClient.messages.create as any;
    assert.strictEqual(regularCreateStub.mock.calls.length, 0);
  });

  it('should use beta API when defaultApiVersion is beta', async () => {
    const mockClient = createMockAnthropicClient({
      messageResponse: {
        content: [{ type: 'text', text: 'response', citations: null }],
        usage: createUsage({
          input_tokens: 10,
          output_tokens: 20,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
        }),
      },
    });

    const runner = claudeRunner({
      name: 'claude-3-5-haiku',
      client: mockClient,
      defaultApiVersion: 'beta',
    });
    const abortSignal = new AbortController().signal;
    await runner(
      {
        messages: [],
      },
      { streamingRequested: false, sendChunk: () => {}, abortSignal }
    );

    const betaCreateStub = mockClient.beta.messages.create as any;
    assert.strictEqual(betaCreateStub.mock.calls.length, 1);

    const regularCreateStub = mockClient.messages.create as any;
    assert.strictEqual(regularCreateStub.mock.calls.length, 0);
  });

  it('should use request apiVersion over defaultApiVersion', async () => {
    const mockClient = createMockAnthropicClient({
      messageResponse: {
        content: [{ type: 'text', text: 'response', citations: null }],
        usage: createUsage({
          input_tokens: 10,
          output_tokens: 20,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
        }),
      },
    });

    // defaultApiVersion is 'stable', but request overrides to 'beta'
    const runner = claudeRunner(
      'claude-3-5-haiku',
      mockClient,
      undefined,
      'stable'
    );
    const abortSignal = new AbortController().signal;
    await runner(
      {
        messages: [],
        config: { apiVersion: 'beta' },
      },
      { streamingRequested: false, sendChunk: () => {}, abortSignal }
    );

    const betaCreateStub = mockClient.beta.messages.create as any;
    assert.strictEqual(betaCreateStub.mock.calls.length, 1);

    const regularCreateStub = mockClient.messages.create as any;
    assert.strictEqual(regularCreateStub.mock.calls.length, 0);
  });

  it('should use stable API when defaultApiVersion is beta but request overrides to stable', async () => {
    const mockClient = createMockAnthropicClient({
      messageResponse: {
        content: [{ type: 'text', text: 'response', citations: null }],
        usage: createUsage({
          input_tokens: 10,
          output_tokens: 20,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
        }),
      },
    });

    // defaultApiVersion is 'beta', but request overrides to 'stable'
    const runner = claudeRunner(
      'claude-3-5-haiku',
      mockClient,
      undefined,
      'beta'
    );
    const abortSignal = new AbortController().signal;
    await runner(
      {
        messages: [],
        config: { apiVersion: 'stable' },
      },
      { streamingRequested: false, sendChunk: () => {}, abortSignal }
    );

    const betaCreateStub = mockClient.beta.messages.create as any;
    assert.strictEqual(betaCreateStub.mock.calls.length, 0);

    const regularCreateStub = mockClient.messages.create as any;
    assert.strictEqual(regularCreateStub.mock.calls.length, 1);
  });
});

describe('claudeRunner param object', () => {
  it('should run requests when constructed with params object', async () => {
    const mockClient = createMockAnthropicClient();
    const runner = claudeRunner({
      name: 'claude-3-5-haiku',
      client: mockClient,
      cacheSystemPrompt: true,
    });
    const abortSignal = new AbortController().signal;

    await runner(
      { messages: [{ role: 'user', content: [{ text: 'hi' }] }] },
      { streamingRequested: false, sendChunk: () => {}, abortSignal }
    );

    const createStub = mockClient.messages.create as any;
    assert.strictEqual(createStub.mock.calls.length, 1);
    assert.strictEqual(
      createStub.mock.calls[0].arguments[0].messages[0].content[0].text,
      'hi'
    );
  });

  it('should route to beta runner when defaultApiVersion is beta', async () => {
    const mockClient = createMockAnthropicClient();
    const runner = claudeRunner({
      name: 'claude-3-5-haiku',
      client: mockClient,
      defaultApiVersion: 'beta',
    });
    await runner(
      { messages: [] },
      {
        streamingRequested: false,
        sendChunk: () => {},
        abortSignal: new AbortController().signal,
      }
    );

    const betaCreateStub = mockClient.beta.messages.create as any;
    assert.strictEqual(betaCreateStub.mock.calls.length, 1);
  });

  it('should throw when client is omitted from params object', () => {
    assert.throws(() => {
      claudeRunner('claude-3-5-haiku', undefined as unknown as Anthropic);
    }, /Anthropic client is required to create a runner/);
  });
});

describe('claudeModel', () => {
  it('should fall back to generic metadata for unknown models', async () => {
    const mockClient = createMockAnthropicClient();
    const modelAction = claudeModel({
      name: 'unknown-model',
      client: mockClient,
    });

    const abortSignal = new AbortController().signal;
    await (modelAction as any)(
      { messages: [{ role: 'user', content: [{ text: 'hi' }] }] },
      {
        streamingRequested: false,
        sendChunk: () => {},
        abortSignal,
      }
    );

    const createStub = mockClient.messages.create as any;
    assert.strictEqual(createStub.mock.calls.length, 1);
    const request = createStub.mock.calls[0].arguments[0];
    assert.strictEqual(request.model, 'unknown-model');
  });
  it('should support params object configuration', async () => {
    const mockClient = createMockAnthropicClient();
    const modelAction = claudeModel({
      name: 'claude-3-5-haiku',
      client: mockClient,
      defaultApiVersion: 'beta',
      cacheSystemPrompt: true,
    });

    const abortSignal = new AbortController().signal;
    await (modelAction as any)(
      { messages: [], config: { maxOutputTokens: 128 } },
      {
        streamingRequested: false,
        sendChunk: () => {},
        abortSignal,
      }
    );

    const betaCreateStub = mockClient.beta.messages.create as any;
    assert.strictEqual(betaCreateStub.mock.calls.length, 1);
    assert.strictEqual(
      betaCreateStub.mock.calls[0].arguments[0].max_tokens,
      128
    );
  });

  it('should throw when client is omitted in params object', () => {
    assert.throws(
      () => claudeModel('claude-3-5-haiku'),
      /Anthropic client is required to create a model action/
    );
  });

  it('should correctly define supported Claude models', () => {
    const mockClient = createMockAnthropicClient();
    const modelName = 'claude-3-5-haiku';
    const modelAction = claudeModel(modelName, mockClient);

    // Verify the model action is returned
    assert.ok(modelAction);
    assert.strictEqual(typeof modelAction, 'function');
  });

  it('should accept any model name and create a model action', () => {
    // Following Google GenAI pattern: accept any model name, let API validate
    const modelAction = claudeModel('unsupported-model', {} as Anthropic);
    assert.ok(modelAction, 'Should create model action for any model name');
    assert.strictEqual(typeof modelAction, 'function');
  });

  it('should handle streaming with multiple text chunks', async () => {
    const mockClient = createMockAnthropicClient({
      streamChunks: [
        mockContentBlockStart('Hello'),
        mockTextChunk(' world'),
        mockTextChunk('!'),
      ],
      messageResponse: {
        content: [{ type: 'text', text: 'Hello world!', citations: null }],
        usage: createUsage({
          input_tokens: 5,
          output_tokens: 10,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
        }),
      },
    });

    const chunks: any[] = [];
    const streamingCallback = mock.fn((chunk: any) => {
      chunks.push(chunk);
    });

    const runner = claudeRunner('claude-3-5-haiku', mockClient);
    const abortSignal = new AbortController().signal;

    const result = await runner(
      { messages: [{ role: 'user', content: [{ text: 'Hi' }] }] },
      { streamingRequested: true, sendChunk: streamingCallback, abortSignal }
    );

    // Verify we received all the streaming chunks
    assert.ok(chunks.length > 0, 'Should have received streaming chunks');
    assert.strictEqual(chunks.length, 3, 'Should have received 3 chunks');

    // Verify the final result
    assert.ok(result.candidates);
    assert.strictEqual(
      result.candidates[0].message.content[0].text,
      'Hello world!'
    );
    assert.ok(result.usage);
    assert.strictEqual(result.usage.inputTokens, 5);
    assert.strictEqual(result.usage.outputTokens, 10);
  });

  it('should handle tool use in streaming mode', async () => {
    const streamChunks = [
      {
        type: 'content_block_start',
        index: 0,
        content_block: {
          type: 'tool_use',
          id: 'toolu_123',
          name: 'get_weather',
          input: { city: 'NYC' },
        },
      } as MessageStreamEvent,
    ];
    const mockClient = createMockAnthropicClient({
      streamChunks,
      messageResponse: {
        content: [
          {
            type: 'tool_use',
            id: 'toolu_123',
            name: 'get_weather',
            input: { city: 'NYC' },
          },
        ],
        stop_reason: 'tool_use',
        usage: createUsage({
          input_tokens: 15,
          output_tokens: 25,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
        }),
      },
    });

    const chunks: any[] = [];
    const streamingCallback = mock.fn((chunk: any) => {
      chunks.push(chunk);
    });

    const runner = claudeRunner('claude-3-5-haiku', mockClient);
    const abortSignal = new AbortController().signal;

    const result = await runner(
      {
        messages: [
          { role: 'user', content: [{ text: 'What is the weather?' }] },
        ],
        tools: [
          {
            name: 'get_weather',
            description: 'Get the weather for a city',
            inputSchema: {
              type: 'object',
              properties: {
                city: { type: 'string' },
              },
              required: ['city'],
            },
          },
        ],
      },
      { streamingRequested: true, sendChunk: streamingCallback, abortSignal }
    );

    // Verify we received the tool use chunk
    assert.ok(chunks.length > 0, 'Should have received chunks');

    // Verify the final result contains tool use
    assert.ok(result.candidates);
    const toolRequest = result.candidates[0].message.content.find(
      (p) => p.toolRequest
    );
    assert.ok(toolRequest, 'Should have a tool request');
    assert.strictEqual(toolRequest.toolRequest?.name, 'get_weather');
    assert.deepStrictEqual(toolRequest.toolRequest?.input, { city: 'NYC' });
  });

  it('should handle streaming errors and partial responses', async () => {
    const streamError = new Error('Network error during streaming');
    const mockClient = createMockAnthropicClient({
      streamChunks: [mockContentBlockStart('Hello'), mockTextChunk(' world')],
      streamErrorAfterChunk: 1, // Throw error after first chunk
      streamError: streamError,
      messageResponse: {
        content: [{ type: 'text', text: 'Hello world', citations: null }],
        usage: createUsage({
          input_tokens: 5,
          output_tokens: 10,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
        }),
      },
    });

    const runner = claudeRunner('claude-3-5-haiku', mockClient);
    const abortSignal = new AbortController().signal;
    const chunks: any[] = [];
    const sendChunk = (chunk: any) => {
      chunks.push(chunk);
    };

    // Should throw error during streaming
    await assert.rejects(
      async () => {
        await runner(
          { messages: [{ role: 'user', content: [{ text: 'Hi' }] }] },
          {
            streamingRequested: true,
            sendChunk,
            abortSignal,
          }
        );
      },
      (error: Error) => {
        // Verify error is propagated
        assert.strictEqual(error.message, 'Network error during streaming');
        // Verify we received at least one chunk before error
        assert.ok(
          chunks.length > 0,
          'Should have received some chunks before error'
        );
        return true;
      }
    );
  });

  it('should handle abort signal during streaming', async () => {
    const mockClient = createMockAnthropicClient({
      streamChunks: [
        mockContentBlockStart('Hello'),
        mockTextChunk(' world'),
        mockTextChunk('!'),
      ],
      messageResponse: {
        content: [{ type: 'text', text: 'Hello world!', citations: null }],
        usage: createUsage({
          input_tokens: 5,
          output_tokens: 15,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
        }),
      },
    });

    const runner = claudeRunner('claude-3-5-haiku', mockClient);
    const abortController = new AbortController();
    const chunks: any[] = [];
    const sendChunk = (chunk: any) => {
      chunks.push(chunk);
      // Abort after first chunk
      if (chunks.length === 1) {
        abortController.abort();
      }
    };

    // Should throw AbortError when signal is aborted
    await assert.rejects(
      async () => {
        await runner(
          { messages: [{ role: 'user', content: [{ text: 'Hi' }] }] },
          {
            streamingRequested: true,
            sendChunk,
            abortSignal: abortController.signal,
          }
        );
      },
      (error: Error) => {
        // Verify abort error is thrown
        assert.ok(
          error.name === 'AbortError' || error.message.includes('AbortError'),
          'Should throw AbortError'
        );
        return true;
      }
    );
  });

  it('should handle unknown models using generic settings', async () => {
    const mockClient = createMockAnthropicClient();
    const modelAction = claudeModel({
      name: 'unknown-model',
      client: mockClient,
    });

    const abortSignal = new AbortController().signal;
    await (modelAction as any)(
      { messages: [{ role: 'user', content: [{ text: 'hi' }] }] },
      {
        streamingRequested: false,
        sendChunk: () => {},
        abortSignal,
      }
    );

    const createStub = mockClient.messages.create as any;
    assert.strictEqual(createStub.mock.calls.length, 1);
    assert.strictEqual(
      createStub.mock.calls[0].arguments[0].model,
      'unknown-model'
    );
  });
});

describe('BaseRunner helper utilities', () => {
  it('should throw descriptive errors for invalid PDF data URLs', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new Runner('claude-3-5-haiku', mockClient);

    assert.throws(
      () =>
        runner['toPdfDocumentSource']({
          url: 'data:text/plain;base64,AAA',
          contentType: 'application/pdf',
        } as any),
      /PDF contentType mismatch/
    );
  });

  it('should stringify non-media tool responses', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new Runner('claude-3-5-haiku', mockClient);

    const result = runner['toAnthropicToolResponseContent']({
      toolResponse: {
        ref: 'call_1',
        name: 'tool',
        output: { value: 42 },
      },
    } as any);

    assert.deepStrictEqual(result, {
      type: 'text',
      text: JSON.stringify({ value: 42 }),
    });
  });

  it('should parse image data URLs', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new Runner('claude-3-5-haiku', mockClient);

    const source = runner['toImageSource']({
      url: 'data:image/png;base64,AAA',
      contentType: 'image/png',
    });

    assert.strictEqual(source.mediaType, 'image/png');
    assert.strictEqual(source.data, 'AAA');
  });
});

describe('Runner request bodies and error branches', () => {
  it('should include optional config fields in non-streaming request body', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new Runner('claude-3-5-haiku', mockClient, true) as Runner &
      RunnerProtectedMethods;

    const body = runner['toAnthropicRequestBody'](
      'claude-3-5-haiku',
      {
        messages: [
          {
            role: 'system',
            content: [{ text: 'You are helpful.' }],
          },
          {
            role: 'user',
            content: [{ text: 'Tell me a joke' }],
          },
        ],
        config: {
          maxOutputTokens: 256,
          topK: 3,
          topP: 0.75,
          temperature: 0.6,
          stopSequences: ['END'],
          metadata: { user_id: 'user-xyz' },
          tool_choice: { type: 'auto' },
        },
        tools: [
          {
            name: 'get_weather',
            description: 'Returns the weather',
            inputSchema: { type: 'object' },
          },
        ],
      } as unknown as GenerateRequest<typeof AnthropicConfigSchema>,
      true
    );

    assert.strictEqual(body.model, 'claude-3-5-haiku-latest');
    assert.ok(Array.isArray(body.system));
    assert.strictEqual(body.system?.[0].cache_control?.type, 'ephemeral');
    assert.strictEqual(body.max_tokens, 256);
    assert.strictEqual(body.top_k, 3);
    assert.strictEqual(body.top_p, 0.75);
    assert.strictEqual(body.temperature, 0.6);
    assert.deepStrictEqual(body.stop_sequences, ['END']);
    assert.deepStrictEqual(body.metadata, { user_id: 'user-xyz' });
    assert.deepStrictEqual(body.tool_choice, { type: 'auto' });
    assert.strictEqual(body.tools?.length, 1);
  });

  it('should include optional config fields in streaming request body', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new Runner('claude-3-5-haiku', mockClient, true) as Runner &
      RunnerProtectedMethods;

    const body = runner['toAnthropicStreamingRequestBody'](
      'claude-3-5-haiku',
      {
        messages: [
          {
            role: 'system',
            content: [{ text: 'Stay brief.' }],
          },
          {
            role: 'user',
            content: [{ text: 'Summarize the weather.' }],
          },
        ],
        config: {
          maxOutputTokens: 64,
          topK: 2,
          topP: 0.6,
          temperature: 0.4,
          stopSequences: ['STOP'],
          metadata: { user_id: 'user-abc' },
          tool_choice: { type: 'any' },
        },
        tools: [
          {
            name: 'summarize_weather',
            description: 'Summarizes a forecast',
            inputSchema: { type: 'object' },
          },
        ],
      } as unknown as GenerateRequest<typeof AnthropicConfigSchema>,
      true
    );

    assert.strictEqual(body.stream, true);
    assert.ok(Array.isArray(body.system));
    assert.strictEqual(body.max_tokens, 64);
    assert.strictEqual(body.top_k, 2);
    assert.strictEqual(body.top_p, 0.6);
    assert.strictEqual(body.temperature, 0.4);
    assert.deepStrictEqual(body.stop_sequences, ['STOP']);
    assert.deepStrictEqual(body.metadata, { user_id: 'user-abc' });
    assert.deepStrictEqual(body.tool_choice, { type: 'any' });
    assert.strictEqual(body.tools?.length, 1);
  });

  it('should throw descriptive errors for missing tool refs', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new Runner('claude-3-5-haiku', mockClient, false) as Runner &
      RunnerProtectedMethods;

    assert.throws(
      () =>
        runner['toAnthropicMessageContent']({
          toolRequest: {
            name: 'get_weather',
            input: {},
          },
        } as any),
      /Tool request ref is required/
    );

    assert.throws(
      () =>
        runner['toAnthropicMessageContent']({
          toolResponse: {
            ref: undefined,
            name: 'get_weather',
            output: 'Sunny',
          },
        } as any),
      /Tool response ref is required/
    );

    assert.throws(
      () =>
        runner['toAnthropicMessageContent']({
          data: 'unexpected',
        } as any),
      /Unsupported genkit part fields/
    );
  });
});
