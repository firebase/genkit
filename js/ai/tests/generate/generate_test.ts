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

import { PluginProvider, z } from '@genkit-ai/core';
import { Registry } from '@genkit-ai/core/registry';
import * as assert from 'assert';
import { beforeEach, describe, it } from 'node:test';
import {
  GenerateOptions,
  generate,
  generateStream,
  toGenerateRequest,
} from '../../src/generate.js';
import { ModelAction, ModelMiddleware, defineModel } from '../../src/model.js';
import { defineTool } from '../../src/tool.js';

describe('toGenerateRequest', () => {
  const registry = new Registry();
  // register tools
  const tellAFunnyJoke = defineTool(
    registry,
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
  );

  const namespacedPlugin: PluginProvider = {
    name: 'namespaced',
    initializer: async () => {},
  };
  registry.registerPluginProvider('namespaced', namespacedPlugin);

  defineTool(
    registry,
    {
      name: 'namespaced/add',
      description: 'add two numbers together',
      inputSchema: z.object({ a: z.number(), b: z.number() }),
      outputSchema: z.number(),
    },
    async ({ a, b }) => a + b
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
        docs: undefined,
        tools: [],
        output: {},
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
        docs: undefined,
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
        output: {},
      },
    },
    {
      should: 'strip namespaces from tools when passing to the model',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
        tools: ['namespaced/add'],
        prompt: 'Add 10 and 5.',
      },
      expectedOutput: {
        messages: [{ role: 'user', content: [{ text: 'Add 10 and 5.' }] }],
        config: undefined,
        docs: undefined,
        tools: [
          {
            description: 'add two numbers together',
            inputSchema: {
              $schema: 'http://json-schema.org/draft-07/schema#',
              additionalProperties: true,
              properties: { a: { type: 'number' }, b: { type: 'number' } },
              required: ['a', 'b'],
              type: 'object',
            },
            name: 'add',
            outputSchema: {
              $schema: 'http://json-schema.org/draft-07/schema#',
              type: 'number',
            },
            metadata: { originalName: 'namespaced/add' },
          },
        ],
        output: {},
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
        docs: undefined,
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
        output: {},
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
        docs: undefined,
        tools: [],
        output: {},
      },
    },
    {
      should: 'translate a prompt with history correctly',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
        messages: [
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
        docs: undefined,
        tools: [],
        output: {},
      },
    },
    {
      should: 'pass context through to the model',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
        prompt: 'Tell a joke with context.',
        docs: [{ content: [{ text: 'context here' }] }],
      },
      expectedOutput: {
        messages: [
          { content: [{ text: 'Tell a joke with context.' }], role: 'user' },
        ],
        config: undefined,
        docs: [{ content: [{ text: 'context here' }] }],
        tools: [],
        output: {},
      },
    },
    {
      should:
        'throw a FAILED_PRECONDITION error if trying to resume without a model message',
      prompt: {
        messages: [{ role: 'system', content: [{ text: 'sys' }] }],
        resume: {
          respond: { toolResponse: { name: 'test', output: { foo: 'bar' } } },
        },
      },
      throws: 'FAILED_PRECONDITION',
    },
    {
      should:
        'throw a FAILED_PRECONDITION error if trying to resume a model message without toolRequests',
      prompt: {
        messages: [
          { role: 'user', content: [{ text: 'hi' }] },
          { role: 'model', content: [{ text: 'there' }] },
        ],
        resume: {
          respond: { toolResponse: { name: 'test', output: { foo: 'bar' } } },
        },
      },
      throws: 'FAILED_PRECONDITION',
    },
    {
      should: 'passes through output options',
      prompt: {
        model: 'vertexai/gemini-1.0-pro',
        prompt: 'Tell a joke about dogs.',
        output: {
          constrained: true,
          format: 'banana',
        },
      },
      expectedOutput: {
        messages: [
          { role: 'user', content: [{ text: 'Tell a joke about dogs.' }] },
        ],
        config: undefined,
        docs: undefined,
        tools: [],
        output: {
          constrained: true,
          format: 'banana',
        },
      },
    },
  ];
  for (const test of testCases) {
    it(test.should, async () => {
      if (test.throws) {
        await assert.rejects(
          async () => {
            await toGenerateRequest(registry, test.prompt as GenerateOptions);
          },
          { name: 'GenkitError', status: test.throws }
        );
      } else {
        const actualOutput = await toGenerateRequest(
          registry,
          test.prompt as GenerateOptions
        );
        assert.deepStrictEqual(actualOutput, test.expectedOutput);
      }
    });
  }
});

describe('generate', () => {
  let registry: Registry;
  var echoModel: ModelAction;

  beforeEach(() => {
    registry = new Registry();
    echoModel = defineModel(
      registry,
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

    const response = await generate(registry, {
      prompt: 'banana',
      model: echoModel,
      use: [wrapRequest, wrapResponse],
    });
    const want = '[Echo: (banana)]';
    assert.deepStrictEqual(response.text, want);
  });
});

describe('generate', () => {
  let registry: Registry;
  beforeEach(() => {
    registry = new Registry();

    defineModel(
      registry,
      { name: 'echo', supports: { tools: true } },
      async (input) => ({
        message: input.messages[0],
        finishReason: 'stop',
      })
    );
  });

  it('should preserve the request in the returned response, enabling .messages', async () => {
    const response = await generate(registry, {
      model: 'echo',
      prompt: 'Testing messages',
    });
    assert.deepEqual(
      response.messages.map((m) => m.content[0].text),
      ['Testing messages', 'Testing messages']
    );
  });

  describe('generateStream', () => {
    it('should stream out chunks', async () => {
      let registry = new Registry();

      defineModel(
        registry,
        { name: 'echo-streaming', supports: { tools: true } },
        async (input, streamingCallback) => {
          streamingCallback!({ content: [{ text: 'hello, ' }] });
          streamingCallback!({ content: [{ text: 'world!' }] });
          return {
            message: input.messages[0],
            finishReason: 'stop',
          };
        }
      );

      const { response, stream } = generateStream(registry, {
        model: 'echo-streaming',
        prompt: 'Testing streaming',
      });

      let streamed: any[] = [];
      for await (const chunk of stream) {
        streamed.push(chunk.toJSON());
      }
      assert.deepStrictEqual(streamed, [
        {
          index: 0,
          role: 'model',
          content: [{ text: 'hello, ' }],
        },
        {
          index: 0,
          role: 'model',
          content: [{ text: 'world!' }],
        },
      ]);
      assert.deepEqual(
        (await response).messages.map((m) => m.content[0].text),
        ['Testing streaming', 'Testing streaming']
      );
    });
  });
});
