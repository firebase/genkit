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
import * as assert from 'assert';
import { beforeEach, describe, it } from 'node:test';
import { modelRef } from '../../ai/src/model';
import { Genkit, genkit } from '../src/genkit';
import {
  ProgrammableModel,
  defineEchoModel,
  defineProgrammableModel,
  runAsync,
} from './helpers';

describe('generate', () => {
  describe('default model', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({
        model: 'echoModel',
      });
      defineEchoModel(ai);
    });

    it('calls the default model', async () => {
      const response = await ai.generate({
        prompt: 'hi',
      });
      assert.strictEqual(response.text, 'Echo: hi; config: {}');
    });

    it('calls the default model with just a string prompt', async () => {
      const response = await ai.generate('hi');
      assert.strictEqual(response.text, 'Echo: hi; config: {}');
    });

    it('calls the default model with just parts prompt', async () => {
      const response = await ai.generate([{ text: 'hi' }]);
      assert.strictEqual(response.text, 'Echo: hi; config: {}');
    });

    it('calls the default model system', async () => {
      const response = await ai.generate({
        prompt: 'hi',
        system: 'talk like a pirate',
      });
      assert.strictEqual(
        response.text,
        'Echo: system: talk like a pirate,hi; config: {}'
      );
      assert.deepStrictEqual(response.request, {
        config: {
          version: undefined,
        },
        docs: undefined,
        messages: [
          {
            role: 'system',
            content: [{ text: 'talk like a pirate' }],
          },
          {
            role: 'user',
            content: [{ text: 'hi' }],
          },
        ],
        output: {},
        tools: [],
      });
    });

    it('calls the default model with tool choice', async () => {
      const response = await ai.generate({
        prompt: 'hi',
        toolChoice: 'required',
      });
      assert.strictEqual(response.text, 'Echo: hi; config: {}');
      assert.deepStrictEqual(response.request, {
        config: {
          version: undefined,
        },
        docs: undefined,
        messages: [
          {
            role: 'user',
            content: [{ text: 'hi' }],
          },
        ],
        output: {},
        tools: [],
        toolChoice: 'required',
      });
    });

    it('streams the default model', async () => {
      const { response, stream } = await ai.generateStream('hi');

      const chunks: string[] = [];
      for await (const chunk of stream) {
        chunks.push(chunk.text);
      }
      assert.strictEqual((await response).text, 'Echo: hi; config: {}');
      assert.deepStrictEqual(chunks, ['3', '2', '1']);
    });
  });

  describe('explicit model', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({});
      defineEchoModel(ai);
    });

    it('calls the explicitly passed in model', async () => {
      const response = await ai.generate({
        model: 'echoModel',
        prompt: 'hi',
      });
      assert.strictEqual(response.text, 'Echo: hi; config: {}');
    });

    it('rejects on invalid model', async () => {
      const response = ai.generate({
        model: 'modelThatDoesNotExist',
        prompt: 'hi',
      });
      await assert.rejects(response, 'Model modelThatDoesNotExist not found');
    });
  });

  describe('streaming', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({});
    });

    it('rethrows response errors', async () => {
      ai.defineModel(
        {
          name: 'blockingModel',
        },
        async (request, streamingCallback) => {
          if (streamingCallback) {
            await runAsync(() => {
              streamingCallback({
                content: [
                  {
                    text: '3',
                  },
                ],
              });
            });
            await runAsync(() => {
              streamingCallback({
                content: [
                  {
                    text: '2',
                  },
                ],
              });
            });
            await runAsync(() => {
              streamingCallback({
                content: [
                  {
                    text: '1',
                  },
                ],
              });
            });
          }
          return await runAsync(() => ({
            message: {
              role: 'model',
              content: [],
            },
            finishReason: 'blocked',
          }));
        }
      );

      await assert.rejects(async () => {
        const { response, stream } = ai.generateStream({
          prompt: 'hi',
          model: 'blockingModel',
        });
        for await (const chunk of stream) {
          // nothing
        }
        await response;
      });
    });

    it('rethrows initialization errors', async () => {
      await assert.rejects(
        (async () => {
          const { stream } = ai.generateStream({
            prompt: 'hi',
            model: 'modelNotFound',
          });
          for await (const chunk of stream) {
            // nothing
          }
        })(), (e: Error) => {
          return e.message.includes('Model modelNotFound not found');
        }
      );
    });

    it('passes the streaming callback to the model', async () => {
      const model = defineEchoModel(ai);
      const flow = ai.defineFlow('wrapper', async (_, streamingCallback) => {
        const response = await ai.generate({
          model: model,
          prompt: 'hi',
          onChunk: console.log,
        });
        return response.text;
      });
      const text = await flow();
      assert.ok((model as any).__test__lastStreamingCallback);
    });

    it('strips out the noop streaming callback', async () => {
      const model = defineEchoModel(ai);
      const flow = ai.defineFlow('wrapper', async (_, streamingCallback) => {
        const response = await ai.generate({
          model: model,
          prompt: 'hi',
          onChunk: streamingCallback,
        });
        return response.text;
      });
      const text = await flow();
      assert.ok(!(model as any).__test__lastStreamingCallback);
    });
  });

  describe('config', () => {
    let ai: Genkit;

    beforeEach(() => {
      ai = genkit({});
      defineEchoModel(ai);
    });

    it('takes config passed to generate', async () => {
      const response = await ai.generate({
        prompt: 'hi',
        model: 'echoModel',
        config: {
          temperature: 11,
        },
      });
      assert.strictEqual(response.text, 'Echo: hi; config: {"temperature":11}');
    });

    it('merges config from the ref', async () => {
      const response = await ai.generate({
        prompt: 'hi',
        model: modelRef({ name: 'echoModel' }).withConfig({
          version: 'abc',
        }),
        config: {
          temperature: 11,
        },
      });
      assert.strictEqual(
        response.text,
        'Echo: hi; config: {"version":"abc","temperature":11}'
      );
    });

    it('picks up the top-level version from the ref', async () => {
      const response = await ai.generate({
        prompt: 'hi',
        model: modelRef({ name: 'echoModel' }).withVersion('bcd'),
        config: {
          temperature: 11,
        },
      });
      assert.strictEqual(
        response.text,
        'Echo: hi; config: {"version":"bcd","temperature":11}'
      );
    });
  });

  describe('tools', () => {
    let ai: Genkit;
    let pm: ProgrammableModel;

    beforeEach(() => {
      ai = genkit({
        model: 'programmableModel',
      });
      pm = defineProgrammableModel(ai);
      defineEchoModel(ai);
    });

    it('call the tool', async () => {
      ai.defineTool(
        { name: 'testTool', description: 'description' },
        async () => 'tool called'
      );

      // first response be tools call, the subsequent just text response from agent b.
      let reqCounter = 0;
      pm.handleResponse = async (req, sc) => {
        return {
          message: {
            role: 'model',
            content: [
              reqCounter++ === 0
                ? {
                    toolRequest: {
                      name: 'testTool',
                      input: {},
                      ref: 'ref123',
                    },
                  }
                : { text: 'done' },
            ],
          },
        };
      };

      const { text } = await ai.generate({
        prompt: 'call the tool',
        tools: ['testTool'],
      });

      assert.strictEqual(text, 'done');
      assert.deepStrictEqual(
        pm.lastRequest,

        {
          config: {},
          messages: [
            {
              role: 'user',
              content: [{ text: 'call the tool' }],
            },
            {
              role: 'model',
              content: [
                {
                  toolRequest: {
                    input: {},
                    name: 'testTool',
                    ref: 'ref123',
                  },
                },
              ],
            },
            {
              role: 'tool',
              content: [
                {
                  toolResponse: {
                    name: 'testTool',
                    output: 'tool called',
                    ref: 'ref123',
                  },
                },
              ],
            },
          ],
          output: {},
          tools: [
            {
              description: 'description',
              inputSchema: {
                $schema: 'http://json-schema.org/draft-07/schema#',
              },
              name: 'testTool',
              outputSchema: {
                $schema: 'http://json-schema.org/draft-07/schema#',
              },
            },
          ],
        }
      );
    });

    it('call the tool with output schema', async () => {
      const schema = z.object({
        foo: z.string(),
      });

      ai.defineTool(
        {
          name: 'testTool',
          description: 'description',
          inputSchema: schema,
          outputSchema: schema,
        },
        async () => {
          return {
            foo: 'bar',
          };
        }
      );

      // first response be tools call, the subsequent just text response from agent b.
      let reqCounter = 0;
      pm.handleResponse = async (req, sc) => {
        return {
          message: {
            role: 'model',
            content: [
              reqCounter++ === 0
                ? {
                    toolRequest: {
                      name: 'testTool',
                      input: { foo: 'fromTool' },
                      ref: 'ref123',
                    },
                  }
                : {
                    text: "```\n{foo: 'fromModel'}\n```",
                  },
            ],
          },
        };
      };
      const { text, output } = await ai.generate({
        output: { schema },
        prompt: 'call the tool',
        tools: ['testTool'],
      });
      assert.strictEqual(text, "```\n{foo: 'fromModel'}\n```");
      assert.deepStrictEqual(output, {
        foo: 'fromModel',
      });
    });

    it('should propagate context to the tool', async () => {
      const schema = z.object({
        foo: z.string(),
      });

      ai.defineTool(
        {
          name: 'testTool',
          description: 'description',
          inputSchema: schema,
          outputSchema: schema,
        },
        async (_, { context }) => {
          return {
            foo: `bar ${context.auth?.email}`,
          };
        }
      );

      // first response be tools call, the subsequent just text response from agent b.
      let reqCounter = 0;
      pm.handleResponse = async (req, sc) => {
        return {
          message: {
            role: 'model',
            content: [
              reqCounter++ === 0
                ? {
                    toolRequest: {
                      name: 'testTool',
                      input: { foo: 'fromTool' },
                      ref: 'ref123',
                    },
                  }
                : {
                    text: req.messages
                      .splice(-1)
                      .map((m) =>
                        m.content
                          .map(
                            (c) =>
                              c.text || JSON.stringify(c.toolResponse?.output)
                          )
                          .join()
                      )
                      .join(),
                  },
            ],
          },
        };
      };
      const { text } = await ai.generate({
        prompt: 'call the tool',
        tools: ['testTool'],
        context: { auth: { email: 'a@b.c' } },
      });
      assert.strictEqual(text, '{"foo":"bar a@b.c"}');
    });

    it('streams the tool responses', async () => {
      ai.defineTool(
        { name: 'testTool', description: 'description' },
        async () => 'tool called'
      );

      // first response be tools call, the subsequent just text response from agent b.
      let reqCounter = 0;
      pm.handleResponse = async (req, sc) => {
        if (sc) {
          sc({
            content: [
              reqCounter === 0
                ? {
                    toolRequest: {
                      name: 'testTool',
                      input: {},
                      ref: 'ref123',
                    },
                  }
                : { text: 'done' },
            ],
          });
        }
        return {
          message: {
            role: 'model',
            content: [
              reqCounter++ === 0
                ? {
                    toolRequest: {
                      name: 'testTool',
                      input: {},
                      ref: 'ref123',
                    },
                  }
                : { text: 'done' },
            ],
          },
        };
      };

      const { stream, response } = await ai.generateStream({
        prompt: 'call the tool',
        tools: ['testTool'],
      });

      const chunks: any[] = [];
      for await (const chunk of stream) {
        chunks.push(chunk.toJSON());
      }

      assert.strictEqual((await response).text, 'done');
      assert.deepStrictEqual(chunks, [
        {
          content: [
            {
              toolRequest: {
                input: {},
                name: 'testTool',
                ref: 'ref123',
              },
            },
          ],
          index: 0,
          role: 'model',
        },
        {
          content: [
            {
              toolResponse: {
                name: 'testTool',
                output: 'tool called',
                ref: 'ref123',
              },
            },
          ],
          index: 1,
          role: 'model',
        },
        {
          content: [{ text: 'done' }],
          index: 2,
          role: 'model',
        },
      ]);
    });

    it('throws when exceeding max tool call iterations', async () => {
      ai.defineTool(
        { name: 'testTool', description: 'description' },
        async () => 'tool called'
      );

      // this will result in the tool getting called infinitely in a loop.
      pm.handleResponse = async () => {
        return {
          message: {
            role: 'model',
            content: [
              {
                toolRequest: {
                  name: 'testTool',
                  input: {},
                  ref: 'ref123',
                },
              },
            ],
          },
        };
      };

      await assert.rejects(
        ai.generate({
          prompt: 'call the tool',
          tools: ['testTool'],
          maxTurns: 17,
        }),
        (err: Error) => {
          return err.message.includes(
            'Exceeded maximum tool call iterations (17)'
          );
        }
      );
    });

    it('interrupts tool execution', async () => {
      ai.defineTool(
        { name: 'simpleTool', description: 'description' },
        async (input) => `response: ${input.name}`
      );
      ai.defineTool(
        { name: 'interruptingTool', description: 'description' },
        async (input, { interrupt }) =>
          interrupt({ confirm: 'is it a banana?' })
      );

      // first response be tools call, the subsequent just text response from agent b.
      let reqCounter = 0;
      pm.handleResponse = async (req, sc) => {
        return {
          message: {
            role: 'model',
            content:
              reqCounter++ === 0
                ? [
                    {
                      text: 'reasoning',
                    },
                    {
                      toolRequest: {
                        name: 'interruptingTool',
                        input: {},
                        ref: 'ref123',
                      },
                    },
                    {
                      toolRequest: {
                        name: 'simpleTool',
                        input: { name: 'foo' },
                        ref: 'ref123',
                      },
                    },
                  ]
                : [{ text: 'done' }],
          },
        };
      };

      const response = await ai.generate({
        prompt: 'call the tool',
        tools: ['interruptingTool', 'simpleTool'],
      });

      assert.strictEqual(reqCounter, 1);
      assert.deepStrictEqual(response.toolRequests, [
        {
          metadata: {
            pendingToolResponse: {
              name: 'simpleTool',
              output: 'response: foo',
              ref: 'ref123',
            },
          },
          toolRequest: {
            input: {
              name: 'foo',
            },
            name: 'simpleTool',
            ref: 'ref123',
          },
        },
        {
          toolRequest: {
            input: {},
            name: 'interruptingTool',
            ref: 'ref123',
          },
          metadata: {
            interrupt: {
              confirm: 'is it a banana?',
            },
          },
        },
      ]);
      assert.deepStrictEqual(response.message?.toJSON(), {
        role: 'model',
        content: [
          {
            text: 'reasoning',
          },
          {
            metadata: {
              pendingToolResponse: {
                name: 'simpleTool',
                output: 'response: foo',
                ref: 'ref123',
              },
            },
            toolRequest: {
              input: {
                name: 'foo',
              },
              name: 'simpleTool',
              ref: 'ref123',
            },
          },
          {
            metadata: {
              interrupt: {
                confirm: 'is it a banana?',
              },
            },
            toolRequest: {
              input: {},
              name: 'interruptingTool',
              ref: 'ref123',
            },
          },
        ],
      });
      assert.deepStrictEqual(pm.lastRequest, {
        config: {},
        messages: [
          {
            role: 'user',
            content: [{ text: 'call the tool' }],
          },
        ],
        output: {},
        tools: [
          {
            description: 'description',
            inputSchema: {
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
            name: 'interruptingTool',
            outputSchema: {
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
          {
            description: 'description',
            inputSchema: {
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
            name: 'simpleTool',
            outputSchema: {
              $schema: 'http://json-schema.org/draft-07/schema#',
            },
          },
        ],
      });
    });
  });
});
