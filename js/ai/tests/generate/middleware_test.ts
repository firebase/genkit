/**
 * Copyright 2026 Google LLC
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
import { initNodeFeatures } from '@genkit-ai/core/node';
import { Registry } from '@genkit-ai/core/registry';
import * as assert from 'assert';
import { beforeEach, describe, it } from 'node:test';
import { generate, generateStream } from '../../src/generate.js';
import { generateMiddleware } from '../../src/generate/middleware.js';
import { defineModel } from '../../src/model.js';
import { ToolInterruptError, defineTool, tool } from '../../src/tool.js';

initNodeFeatures();

describe('generateMiddleware', () => {
  let registry: Registry;

  beforeEach(() => {
    registry = new Registry();
  });

  it('runs generate and model middleware in the correct order', async () => {
    const executionOrder: string[] = [];

    const mockModel = defineModel(
      registry,
      { name: 'mockModel' },
      async (req) => {
        executionOrder.push('modelExecution');
        return {
          message: {
            role: 'model',
            content: [{ text: 'response' }],
          },
        };
      }
    );

    const testMiddleware = generateMiddleware(
      { name: 'testMiddleware' },
      () => ({
        generate: async (req, ctx, next) => {
          executionOrder.push('generateBefore');
          const res = await next(req, ctx);
          executionOrder.push('generateAfter');
          return res;
        },
        model: async (req, ctx, next) => {
          executionOrder.push('modelBefore');
          const res = await next(req, ctx);
          executionOrder.push('modelAfter');
          return res;
        },
      })
    );

    await generate(registry, {
      model: mockModel,
      prompt: 'hi',
      use: [testMiddleware()],
    });

    assert.deepStrictEqual(executionOrder, [
      'generateBefore',
      'modelBefore',
      'modelExecution',
      'modelAfter',
      'generateAfter',
    ]);
  });

  it('runs tool middleware correctly', async () => {
    const executionOrder: string[] = [];

    const mockTool = defineTool(
      registry,
      {
        name: 'mockTool',
        description: 'A mock tool',
        inputSchema: z.object({}),
        outputSchema: z.string(),
      },
      async () => {
        executionOrder.push('toolExecution');
        return 'tool output';
      }
    );

    let turns = 0;
    const mockModel = defineModel(
      registry,
      { name: 'mockModelWithTool' },
      async (req) => {
        executionOrder.push('modelExecution');
        turns++;
        if (turns === 1) {
          return {
            message: {
              role: 'model',
              content: [
                {
                  toolRequest: {
                    name: mockTool.__action.name,
                    ref: '123',
                    input: {},
                  },
                },
              ],
            },
          };
        } else {
          return {
            message: {
              role: 'model',
              content: [{ text: 'final response' }],
            },
          };
        }
      }
    );

    const testMiddleware = generateMiddleware(
      { name: 'testMiddleware' },
      () => {
        let turnCount = 0;
        return {
          generate: async (req, ctx, next) => {
            const t = ++turnCount;
            executionOrder.push('generateBefore-' + t);
            const res = await next(req, ctx);
            executionOrder.push('generateAfter-' + t);
            return res;
          },
          model: async (req, ctx, next) => {
            executionOrder.push(`modelBefore-${turnCount}`);
            const res = await next(req, ctx);
            executionOrder.push(`modelAfter-${turnCount}`);
            return res;
          },
          tool: async (req, ctx, next) => {
            executionOrder.push(`toolBefore-${turnCount}`);
            const res = await next(req, ctx);
            executionOrder.push(`toolAfter-${turnCount}`);
            return res;
          },
        };
      }
    );

    await generate(registry, {
      model: mockModel,
      tools: [mockTool],
      prompt: 'hi',
      use: [testMiddleware()],
    });

    assert.deepStrictEqual(executionOrder, [
      'generateBefore-1',
      'modelBefore-1', // Turn 1
      'modelExecution',
      'modelAfter-1',
      'toolBefore-1', // Tool execution
      'toolExecution',
      'toolAfter-1',
      'generateBefore-2',
      'modelBefore-2', // Turn 2
      'modelExecution',
      'modelAfter-2',
      'generateAfter-2',
      'generateAfter-1',
    ]);
  });

  it('supports configuration and old-style function middleware', async () => {
    let configValue = '';

    const mockModel = defineModel(
      registry,
      { name: 'mockModel' },
      async (req) => {
        return {
          message: {
            role: 'model',
            content: [{ text: 'response' }],
          },
        };
      }
    );

    const testMiddleware = generateMiddleware(
      { name: 'configMw', configSchema: z.object({ val: z.string() }) },
      (config) => ({
        model: async (req, ctx, next) => {
          configValue = config?.val || '';
          return next(req, ctx);
        },
      })
    );

    let oldStyleExecuted = false;
    const oldStyleMiddleware = async (req: any, next: any) => {
      oldStyleExecuted = true;
      return next(req);
    };

    await generate(registry, {
      model: mockModel,
      prompt: 'test',
      use: [testMiddleware({ val: 'test_config' }), oldStyleMiddleware],
    });

    assert.strictEqual(configValue, 'test_config');
    assert.strictEqual(oldStyleExecuted, true);
  });

  it('supports pre-registered middleware (e.g. installed via plugin)', async () => {
    let executed = false;
    let configValue = '';

    const mockModel = defineModel(
      registry,
      { name: 'mockModel' },
      async (req) => {
        return {
          message: {
            role: 'model',
            content: [{ text: 'response' }],
          },
        };
      }
    );

    const preRegisteredMw = generateMiddleware(
      { name: 'preRegisteredMw', configSchema: z.object({ val: z.string() }) },
      (config) => ({
        model: async (req, ctx, next) => {
          executed = true;
          configValue = config?.val || '';
          return next(req, ctx);
        },
      })
    );

    // Act as a plugin registering the middleware
    const myPlugin = preRegisteredMw.plugin({ val: 'plugin_config' });
    assert.ok(myPlugin.generateMiddleware);
    myPlugin.generateMiddleware().forEach((mw: any) => {
      registry.registerValue('middleware', mw.name, mw);
    });

    await generate(registry, {
      model: mockModel,
      prompt: 'test',
      use: [{ name: 'preRegisteredMw' }],
    });

    assert.strictEqual(executed, true);
    assert.strictEqual(configValue, 'plugin_config');
  });

  it('throws an error if a middleware factory is passed without being called', async () => {
    const mockModel = defineModel(
      registry,
      { name: 'mockModel' },
      async () => ({
        message: { role: 'model', content: [{ text: 'done' }] },
        finishReason: 'stop',
      })
    );
    const streamModifyingMw = generateMiddleware({ name: 'dummy' }, () => ({}));

    await assert.rejects(
      async () => {
        await generate(registry, {
          model: mockModel,
          prompt: 'test',
          use: [streamModifyingMw as any],
        });
      },
      (err: any) => {
        assert.strictEqual(err.name, 'GenkitError');
        assert.match(err.message, /must be called with \(\)/);
        return true;
      }
    );
  });

  it('can intercept and modify the stream from model and generate interceptors', async () => {
    const chunkIntercepts: string[] = [];

    const mockStreamingModel = defineModel(
      registry,
      { name: 'mockStreamingModel' },
      async (req, streamingCallback) => {
        if (streamingCallback) {
          streamingCallback({ content: [{ text: 'chunk1' }] });
          streamingCallback({ content: [{ text: 'chunk2' }] });
        }
        return {
          message: {
            role: 'model',
            content: [{ text: 'chunk1chunk2' }],
          },
          finishReason: 'stop',
        };
      }
    );

    const streamModifyingMw = generateMiddleware(
      { name: 'streamModifier' },
      () => ({
        model: async (req, ctx, next) => {
          const originalOnChunk = ctx.onChunk;
          let interceptedCtx = ctx;
          if (originalOnChunk) {
            interceptedCtx = {
              ...ctx,
              onChunk: (chunk) => {
                chunkIntercepts.push(`model_mw: ${chunk.content[0].text}`);
                chunk.content[0].text = chunk.content[0].text.toUpperCase();
                originalOnChunk(chunk);
              },
            };
          }
          return next(req, interceptedCtx);
        },
        generate: async (req, ctx, next) => {
          const originalOnChunk = ctx.onChunk;
          let interceptedCtx = ctx;
          if (originalOnChunk) {
            interceptedCtx = {
              ...ctx,
              onChunk: (chunk) => {
                chunkIntercepts.push(`gen_mw: ${chunk.content[0].text}`);
                chunk.content[0].text = `[${chunk.content[0].text}]`;
                originalOnChunk(chunk);
              },
            };
          }
          const res = await next(req, interceptedCtx);
          if (res.message) {
            return {
              ...res,
              message: {
                ...res.message,
                content: [
                  { text: `modified_result: ${res.message.content[0].text}` },
                ],
              },
            };
          }
          return res;
        },
      })
    );

    let finalChunks: string[] = [];

    const { response, stream } = generateStream(registry, {
      model: mockStreamingModel,
      prompt: 'test streaming mw',
      use: [streamModifyingMw()],
    });

    for await (const chunk of stream) {
      finalChunks.push(chunk.text);
    }

    const res = await response;

    assert.deepStrictEqual(chunkIntercepts, [
      'model_mw: chunk1',
      'gen_mw: CHUNK1',
      'model_mw: chunk2',
      'gen_mw: CHUNK2',
    ]);

    assert.deepStrictEqual(finalChunks, ['[CHUNK1]', '[CHUNK2]']);
    assert.strictEqual(res.text, 'modified_result: chunk1chunk2');
  });

  it('executes multiple middleware in the correct order', async () => {
    const executionOrder: string[] = [];

    const mw1 = generateMiddleware({ name: 'mw1' }, () => ({
      async generate(opts, ctx, next) {
        executionOrder.push('mw1:gen:start');
        const res = await next(opts, ctx);
        executionOrder.push('mw1:gen:end');
        return res;
      },
      async model(req, ctx, next) {
        executionOrder.push('mw1:model:start');
        const res = await next(req, ctx);
        executionOrder.push('mw1:model:end');
        return res;
      },
    }));

    const mw2 = generateMiddleware({ name: 'mw2' }, () => ({
      async generate(opts, ctx, next) {
        executionOrder.push('mw2:gen:start');
        const res = await next(opts, ctx);
        executionOrder.push('mw2:gen:end');
        return res;
      },
      async model(req, ctx, next) {
        executionOrder.push('mw2:model:start');
        const res = await next(req, ctx);
        executionOrder.push('mw2:model:end');
        return res;
      },
    }));

    const mockModel = defineModel(
      registry,
      { name: 'mockModel' },
      async () => ({
        message: { role: 'model', content: [{ text: 'done' }] },
        finishReason: 'stop',
      })
    );

    await generate(registry, {
      model: mockModel,
      prompt: 'test multiple',
      use: [mw1(), mw2()],
    });

    // The entire 'generate' layer runs before we ever descend to the 'model' level
    assert.deepStrictEqual(executionOrder, [
      'mw1:gen:start',
      'mw2:gen:start',
      'mw1:model:start',
      'mw2:model:start',
      'mw2:model:end',
      'mw1:model:end',
      'mw2:gen:end',
      'mw1:gen:end',
    ]);
  });

  it('supports a combination of new middleware and old-style functional middleware', async () => {
    const executionOrder: string[] = [];

    const newMw = generateMiddleware({ name: 'newMw' }, () => ({
      async generate(opts, ctx, next) {
        executionOrder.push('newMw:gen:start');
        const res = await next(opts, ctx);
        executionOrder.push('newMw:gen:end');
        return res;
      },
      async model(req, ctx, next) {
        executionOrder.push('newMw:model:start');
        const res = await next(req, ctx);
        executionOrder.push('newMw:model:end');
        return res;
      },
    }));

    const oldMw1 = async (req: any, next: any) => {
      executionOrder.push('oldMw1:model:start');
      const res = await next(); // Validating 0-argument backwards-compatibility
      executionOrder.push('oldMw1:model:end');
      return res;
    };

    const oldMw2 = async (req: any, ctx: any, next: any) => {
      executionOrder.push('oldMw2:model:start');
      const res = await next(req, ctx);
      executionOrder.push('oldMw2:model:end');
      return res;
    };

    const mockModel = defineModel(
      registry,
      { name: 'mockModel' },
      async () => ({
        message: { role: 'model', content: [{ text: 'done' }] },
        finishReason: 'stop',
      })
    );

    await generate(registry, {
      model: mockModel,
      prompt: 'test mixed',
      use: [oldMw1, newMw(), oldMw2],
    });

    assert.deepStrictEqual(executionOrder, [
      'newMw:gen:start', // Generate level ALWAYS runs first across full array
      'oldMw1:model:start',
      'newMw:model:start',
      'oldMw2:model:start',
      'oldMw2:model:end',
      'newMw:model:end',
      'oldMw1:model:end',
      'newMw:gen:end',
    ]);
  });

  it('injects tools from new-style generateMiddleware and executes tool requests', async () => {
    let toolExecutionCount = 0;

    const injectedTool = tool(
      {
        name: 'injectedTool',
        description: 'injected tool description',
        inputSchema: z.object({ arg: z.string() }),
        outputSchema: z.string(),
      },
      async (input) => {
        toolExecutionCount++;
        return `Result: ${input.arg}`;
      }
    );

    const toolMiddleware = generateMiddleware({ name: 'toolMw' }, () => ({
      tools: [injectedTool],
    }));

    let callCount = 0;
    const mockToolModel = defineModel(
      registry,
      { name: 'mockToolModel' },
      async (req) => {
        callCount++;
        // Assert that the tools sent to the model include the injected tool
        assert.ok(req.tools?.find((t) => t.name === 'injectedTool'));

        if (callCount === 1) {
          return {
            message: {
              role: 'model',
              content: [
                {
                  toolRequest: {
                    name: 'injectedTool',
                    ref: 'call_1',
                    input: { arg: 'hello' },
                  },
                },
              ],
            },
            finishReason: 'stop',
          };
        } else {
          assert.strictEqual(req.messages[2].role, 'tool');
          const toolData = req.messages[2].content[0].toolResponse;
          assert.strictEqual(toolData?.name, 'injectedTool');
          assert.strictEqual(toolData?.output, 'Result: hello');

          return {
            message: { role: 'model', content: [{ text: 'final response' }] },
            finishReason: 'stop',
          };
        }
      }
    );

    const result = await generate(registry, {
      model: mockToolModel,
      prompt: 'test tools',
      use: [toolMiddleware()],
    });

    assert.strictEqual(result.text, 'final response');
    assert.strictEqual(toolExecutionCount, 1);
  });

  it('handles ToolInterruptError from middleware', async () => {
    const mockTool = defineTool(
      registry,
      {
        name: 'interruptTool',
        description: 'interrupts',
        inputSchema: z.object({}),
        outputSchema: z.string(),
      },
      async () => {
        return 'foo';
      }
    );

    const interruptMiddleware = generateMiddleware(
      { name: 'interruptMw' },
      () => ({
        tool: async (req, ctx, next) => {
          throw new ToolInterruptError({ some: 'metadata' });
        },
      })
    );

    const mockModel = defineModel(
      registry,
      { name: 'mockModelWithTool' },
      async (req) => {
        return {
          message: {
            role: 'model',
            content: [
              {
                toolRequest: {
                  name: mockTool.__action.name,
                  ref: '123',
                  input: {},
                },
              },
            ],
          },
        };
      }
    );

    const result = await generate(registry, {
      model: mockModel,
      prompt: 'hi',
      tools: ['interruptTool'],
      use: [interruptMiddleware()],
    });

    assert.strictEqual(result.finishReason, 'interrupted');
    const interruptPart = result.message?.content.find(
      (p) => p.metadata?.interrupt
    );
    assert.ok(interruptPart);
    assert.deepStrictEqual(interruptPart.metadata?.interrupt, {
      some: 'metadata',
    });
  });

  it('resumes tool execution with modified metadata after interrupt', async () => {
    const mockTool = defineTool(
      registry,
      {
        name: 'interruptTool',
        description: 'interrupts',
        inputSchema: z.object({}),
        outputSchema: z.string(),
      },
      async () => {
        return 'tool output';
      }
    );

    let middlewareRunCount = 0;
    const interruptMiddleware = generateMiddleware(
      { name: 'interruptMw' },
      () => ({
        tool: async (req, ctx, next) => {
          middlewareRunCount++;
          if (req.metadata?.['approved'] === true) {
            return next(req, ctx);
          }
          throw new ToolInterruptError({ some: 'metadata' });
        },
      })
    );

    let callCount = 0;
    const mockModel = defineModel(
      registry,
      { name: 'mockModelWithTool' },
      async (req) => {
        callCount++;
        if (callCount === 1) {
          return {
            message: {
              role: 'model',
              content: [
                {
                  toolRequest: {
                    name: mockTool.__action.name,
                    ref: '123',
                    input: {},
                  },
                },
              ],
            },
          };
        } else {
          return {
            message: {
              role: 'model',
              content: [{ text: 'final response' }],
            },
          };
        }
      }
    );

    const result = await generate(registry, {
      model: mockModel,
      prompt: 'hi',
      tools: ['interruptTool'],
      use: [interruptMiddleware()],
    });

    assert.strictEqual(result.finishReason, 'interrupted');
    const interruptPart = result.interrupts[0];
    assert.ok(interruptPart);
    assert.strictEqual(middlewareRunCount, 1);

    // Modify metadata
    if (interruptPart.metadata) {
      interruptPart.metadata = { ...interruptPart.metadata, approved: true };
    }

    const result2 = await generate(registry, {
      model: mockModel,
      messages: result.messages,
      tools: ['interruptTool'],
      use: [interruptMiddleware()],
      resume: {
        restart: [interruptPart],
      },
    });

    assert.strictEqual(result2.text, 'final response');
    // Middleware should have run again
    assert.strictEqual(middlewareRunCount, 2);
  });

  it('re-runs generate middleware after resuming tool execution', async () => {
    const mockTool = defineTool(
      registry,
      {
        name: 'interruptTool',
        description: 'interrupts',
        inputSchema: z.object({}),
        outputSchema: z.string(),
      },
      async () => {
        return 'tool output';
      }
    );

    let generateMiddlewareCallCount = 0;
    let seenToolResponseInGenerate = false;

    const testMiddleware = generateMiddleware(
      { name: 'testMw' },
      () => ({
        generate: async (req, ctx, next) => {
          generateMiddlewareCallCount++;
          const lastMsg = req.messages[req.messages.length - 1];
          if (lastMsg?.role === 'tool') {
            seenToolResponseInGenerate = true;
          }
          return next(req, ctx);
        },
        tool: async (req, ctx, next) => {
          if (req.metadata?.['approved'] === true) {
            return next(req, ctx);
          }
          throw new ToolInterruptError({ some: 'metadata' });
        },
      })
    );

    let callCount = 0;
    const mockModel = defineModel(
      registry,
      { name: 'mockModelWithTool2' },
      async (req) => {
        callCount++;
        if (callCount === 1) {
          return {
            message: {
              role: 'model',
              content: [
                {
                  toolRequest: {
                    name: mockTool.__action.name,
                    ref: '123',
                    input: {},
                  },
                },
              ],
            },
          };
        } else {
          return {
            message: {
              role: 'model',
              content: [{ text: 'final response' }],
            },
          };
        }
      }
    );

    const result = await generate(registry, {
      model: mockModel,
      prompt: 'hi',
      tools: ['interruptTool'],
      use: [testMiddleware()],
    });

    assert.strictEqual(result.finishReason, 'interrupted');
    const interruptPart = result.interrupts[0];
    assert.ok(interruptPart);

    // Modify metadata
    if (interruptPart.metadata) {
      interruptPart.metadata = { ...interruptPart.metadata, approved: true };
    }

    generateMiddlewareCallCount = 0; // Reset
    seenToolResponseInGenerate = false;

    await generate(registry, {
      model: mockModel,
      messages: result.messages,
      tools: ['interruptTool'],
      use: [testMiddleware()],
      resume: {
        restart: [interruptPart],
      },
    });

    assert.ok(
      seenToolResponseInGenerate,
      'Generate middleware should see the tool response'
    );
    assert.strictEqual(generateMiddlewareCallCount, 2);
  });
});
