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

import { z } from '@genkit-ai/core';
import { Registry, runWithRegistry } from '@genkit-ai/core/registry';
import { toJsonSchema } from '@genkit-ai/core/schema';
import assert from 'node:assert';
import { beforeEach, describe, it } from 'node:test';
import {
  generate,
  GenerateOptions,
  GenerateResponse,
  GenerateResponseChunk,
  GenerationBlockedError,
  GenerationResponseError,
  Message,
  toGenerateRequest,
} from '../../src/generate.js';
import {
  defineModel,
  GenerateRequest,
  GenerateResponseChunkData,
  GenerateResponseData,
  ModelAction,
  ModelMiddleware,
} from '../../src/model.js';
import { defineTool } from '../../src/tool.js';

describe('GenerateResponse', () => {
  describe('#toJSON()', () => {
    const testCases = [
      {
        should: 'serialize correctly when custom is undefined',
        responseData: {
          message: {
            role: 'model',
            content: [{ text: '{"name": "Bob"}' }],
          },
          finishReason: 'stop',
          finishMessage: '',
          usage: {},
          // No 'custom' property
        },
        expectedOutput: {
          message: { content: [{ text: '{"name": "Bob"}' }], role: 'model' },
          finishReason: 'stop',
          usage: {},
          custom: {},
        },
      },
    ];

    for (const test of testCases) {
      it(test.should, () => {
        const response = new GenerateResponse(
          test.responseData as GenerateResponseData
        );
        assert.deepStrictEqual(response.toJSON(), test.expectedOutput);
      });
    }
  });

  describe('#output()', () => {
    const testCases = [
      {
        should: 'return structured data from the data part',
        responseData: {
          message: new Message({
            role: 'model',
            content: [{ data: { name: 'Alice', age: 30 } }],
          }),
          finishReason: 'stop',
          finishMessage: '',
          usage: {},
        },
        expectedOutput: { name: 'Alice', age: 30 },
      },
      {
        should: 'parse JSON from text when the data part is absent',
        responseData: {
          message: new Message({
            role: 'model',
            content: [{ text: '{"name": "Bob"}' }],
          }),
          finishReason: 'stop',
          finishMessage: '',
          usage: {},
        },
        expectedOutput: { name: 'Bob' },
      },
    ];

    for (const test of testCases) {
      it(test.should, () => {
        const response = new GenerateResponse(
          test.responseData as GenerateResponseData
        );
        assert.deepStrictEqual(response.output(), test.expectedOutput);
      });
    }
  });

  describe('#assertValid()', () => {
    it('throws GenerationBlockedError if finishReason is blocked', () => {
      const response = new GenerateResponse({
        finishReason: 'blocked',
        finishMessage: 'Content was blocked',
      });

      assert.throws(
        () => {
          response.assertValid();
        },
        (err: unknown) => {
          return err instanceof GenerationBlockedError;
        }
      );
    });

    it('throws GenerationResponseError if no message is generated', () => {
      const response = new GenerateResponse({
        finishReason: 'length',
        finishMessage: 'Reached max tokens',
      });

      assert.throws(
        () => {
          response.assertValid();
        },
        (err: unknown) => {
          return err instanceof GenerationResponseError;
        }
      );
    });

    it('throws error if output does not conform to schema', () => {
      const schema = z.object({
        name: z.string(),
        age: z.number(),
      });

      const response = new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: '{"name": "John", "age": "30"}' }],
        },
        finishReason: 'stop',
      });

      const request: GenerateRequest = {
        messages: [],
        output: {
          schema: toJsonSchema({ schema }),
        },
      };

      assert.throws(
        () => {
          response.assertValid(request);
        },
        (err: unknown) => {
          return err instanceof Error && err.message.includes('must be number');
        }
      );
    });

    it('does not throw if output conforms to schema', () => {
      const schema = z.object({
        name: z.string(),
        age: z.number(),
      });

      const response = new GenerateResponse({
        message: {
          role: 'model',
          content: [{ text: '{"name": "John", "age": 30}' }],
        },
        finishReason: 'stop',
      });

      const request: GenerateRequest = {
        messages: [],
        output: {
          schema: toJsonSchema({ schema }),
        },
      };

      assert.doesNotThrow(() => {
        response.assertValid(request);
      });
    });
  });

  describe('#toolRequests()', () => {
    it('returns empty array if no tools requests found', () => {
      const response = new GenerateResponse({
        message: new Message({
          role: 'model',
          content: [{ text: '{"abc":"123"}' }],
        }),
        finishReason: 'stop',
      });
      assert.deepStrictEqual(response.toolRequests(), []);
    });
    it('returns tool call if present', () => {
      const toolCall = {
        toolRequest: {
          name: 'foo',
          ref: 'abc',
          input: 'banana',
        },
      };
      const response = new GenerateResponse({
        message: new Message({
          role: 'model',
          content: [toolCall],
        }),
        finishReason: 'stop',
      });
      assert.deepStrictEqual(response.toolRequests(), [toolCall]);
    });
    it('returns all tool calls', () => {
      const toolCall1 = {
        toolRequest: {
          name: 'foo',
          ref: 'abc',
          input: 'banana',
        },
      };
      const toolCall2 = {
        toolRequest: {
          name: 'bar',
          ref: 'bcd',
          input: 'apple',
        },
      };
      const response = new GenerateResponse({
        message: new Message({
          role: 'model',
          content: [toolCall1, toolCall2],
        }),
        finishReason: 'stop',
      });
      assert.deepStrictEqual(response.toolRequests(), [toolCall1, toolCall2]);
    });
  });
});

describe('toGenerateRequest', () => {
  const registry = new Registry();
  // register tools
  const tellAFunnyJoke = runWithRegistry(registry, () =>
    defineTool(
      {
        name: 'tellAFunnyJoke',
        description:
          'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
        inputSchema: z.object({ topic: z.string() }),
        outputSchema: z.string(),
      },
      async (input) => {
        return `Why did the ${input.topic} cross the road?`;
      }
    )
  );

  const testCases = [
    {
      should: 'translate a string prompt correctly',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
        prompt: 'Tell a joke about dogs.',
      },
      expectedOutput: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        config: undefined,
        context: undefined,
        tools: [],
        output: { format: 'text' },
      },
    },
    {
      should:
        'translate a string prompt correctly with tools referenced by their name',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
        tools: ['tellAFunnyJoke'],
        prompt: 'Tell a joke about dogs.',
      },
      expectedOutput: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        config: undefined,
        context: undefined,
        tools: [
          {
            name: 'tellAFunnyJoke',
            description:
              'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
            outputSchema: {
              type: 'string',
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
            inputSchema: {
              type: 'object',
              properties: { topic: { type: 'string' } },
              required: ['topic'],
              additionalProperties: true,
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
        ],
        output: { format: 'text' },
      },
    },
    {
      should:
        'translate a string prompt correctly with tools referenced by their action',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
        tools: [tellAFunnyJoke],
        prompt: 'Tell a joke about dogs.',
      },
      expectedOutput: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        config: undefined,
        context: undefined,
        tools: [
          {
            name: 'tellAFunnyJoke',
            description:
              'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
            outputSchema: {
              type: 'string',
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
            inputSchema: {
              type: 'object',
              properties: { topic: { type: 'string' } },
              required: ['topic'],
              additionalProperties: true,
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
        ],
        output: { format: 'text' },
      },
    },
    {
      should: 'translate a media prompt correctly',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
        prompt: [
          { text: 'describe the following image:' },
          {
            media: {
              url: 'https://picsum.photos/200',
              contentType: 'image/jpeg',
            },
          },
        ],
      },
      expectedOutput: {
        messages: [
          {
            role: 'user',
            content: [
              { text: 'describe the following image:' },
              {
                media: {
                  url: 'https://picsum.photos/200',
                  contentType: 'image/jpeg',
                },
              },
            ],
          },
        ],
        config: undefined,
        context: undefined,
        tools: [],
        output: { format: 'text' },
      },
    },
    {
      should: 'translate a prompt with history correctly',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
        history: [
          { content: [{ text: 'hi' }], role: 'user' },
          { content: [{ text: 'how can I help you' }], role: 'model' },
        ],
        prompt: 'Tell a joke about dogs.',
      },
      expectedOutput: {
        messages: [
          { content: [{ text: 'hi' }], role: 'user' },
          { content: [{ text: 'how can I help you' }], role: 'model' },
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        config: undefined,
        context: undefined,
        tools: [],
        output: { format: 'text' },
      },
    },
    {
      should: 'pass context through to the model',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
        prompt: 'Tell a joke with context.',
        context: [{ content: [{ text: 'context here' }] }],
      },
      expectedOutput: {
        messages: [
          { content: [{ text: 'Tell a joke with context.' }], role: 'user' },
        ],
        config: undefined,
        context: [{ content: [{ text: 'context here' }] }],
        tools: [],
        output: { format: 'text' },
      },
    },
  ];
  for (const test of testCases) {
    it(test.should, async () => {
      assert.deepStrictEqual(
        await runWithRegistry(registry, () =>
          toGenerateRequest(test.prompt as GenerateOptions)
        ),
        test.expectedOutput
      );
    });
  }
});

describe('GenerateResponseChunk', () => {
  describe('#output()', () => {
    const testCases = [
      {
        should: 'parse ``` correctly',
        accumulatedChunksTexts: ['```'],
        correctJson: null,
      },
      {
        should: 'parse valid json correctly',
        accumulatedChunksTexts: [`{"foo":"bar"}`],
        correctJson: { foo: 'bar' },
      },
      {
        should: 'if json invalid, return null',
        accumulatedChunksTexts: [`invalid json`],
        correctJson: null,
      },
      {
        should: 'handle missing closing brace',
        accumulatedChunksTexts: [`{"foo":"bar"`],
        correctJson: { foo: 'bar' },
      },
      {
        should: 'handle missing closing bracket in nested object',
        accumulatedChunksTexts: [`{"foo": {"bar": "baz"`],
        correctJson: { foo: { bar: 'baz' } },
      },
      {
        should: 'handle multiple chunks',
        accumulatedChunksTexts: [`{"foo": {"bar"`, `: "baz`],
        correctJson: { foo: { bar: 'baz' } },
      },
      {
        should: 'handle multiple chunks with nested objects',
        accumulatedChunksTexts: [`\`\`\`json{"foo": {"bar"`, `: {"baz": "qux`],
        correctJson: { foo: { bar: { baz: 'qux' } } },
      },
      {
        should: 'handle array nested in object',
        accumulatedChunksTexts: [`{"foo": ["bar`],
        correctJson: { foo: ['bar'] },
      },
      {
        should: 'handle array nested in object with multiple chunks',
        accumulatedChunksTexts: [`\`\`\`json{"foo": {"bar"`, `: ["baz`],
        correctJson: { foo: { bar: ['baz'] } },
      },
    ];

    for (const test of testCases) {
      if (test.should) {
        it(test.should, () => {
          const accumulatedChunks: GenerateResponseChunkData[] =
            test.accumulatedChunksTexts.map((text, index) => ({
              index,
              content: [{ text }],
            }));

          const chunkData = accumulatedChunks[accumulatedChunks.length - 1];

          const responseChunk: GenerateResponseChunk =
            new GenerateResponseChunk(chunkData, accumulatedChunks);

          const output = responseChunk.output();

          assert.deepStrictEqual(output, test.correctJson);
        });
      }
    }
  });
});

describe('generate', () => {
  let registry: Registry;
  var echoModel: ModelAction;

  beforeEach(() => {
    registry = new Registry();
    echoModel = runWithRegistry(registry, () =>
      defineModel(
        {
          name: 'echoModel',
        },
        async (request) => {
          return {
            message: {
              role: 'model',
              content: [
                {
                  text:
                    'Echo: ' +
                    request.messages
                      .map((m) => m.content.map((c) => c.text).join())
                      .join(),
                },
              ],
            },
            finishReason: 'stop',
          };
        }
      )
    );
  });

  it('applies middleware', async () => {
    const wrapRequest: ModelMiddleware = async (req, next) => {
      return next({
        ...req,
        messages: [
          {
            role: 'user',
            content: [
              {
                text:
                  '(' +
                  req.messages
                    .map((m) => m.content.map((c) => c.text).join())
                    .join() +
                  ')',
              },
            ],
          },
        ],
      });
    };
    const wrapResponse: ModelMiddleware = async (req, next) => {
      const res = await next(req);
      return {
        message: {
          role: 'model',
          content: [
            {
              text: '[' + res.message!.content.map((c) => c.text).join() + ']',
            },
          ],
        },
        finishReason: res.finishReason,
      };
    };

    const response = await runWithRegistry(registry, () =>
      generate({
        prompt: 'banana',
        model: echoModel,
        use: [wrapRequest, wrapResponse],
      })
    );

    const want = '[Echo: (banana)]';
    assert.deepStrictEqual(response.text(), want);
  });
});

describe('generate', () => {
  let registry: Registry;
  beforeEach(() => {
    registry = new Registry();
    runWithRegistry(registry, () =>
      defineModel(
        { name: 'echo', supports: { tools: true } },
        async (input) => ({
          message: input.messages[0],
          finishReason: 'stop',
        })
      )
    );
  });
  it('should preserve the request in the returned response, enabling toHistory()', async () => {
    const response = await runWithRegistry(registry, () =>
      generate({
        model: 'echo',
        prompt: 'Testing toHistory',
      })
    );

    assert.deepEqual(
      response.toHistory().map((m) => m.content[0].text),
      ['Testing toHistory', 'Testing toHistory']
    );
  });
});
