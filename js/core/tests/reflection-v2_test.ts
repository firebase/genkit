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

import * as assert from 'assert';
import { afterEach, beforeEach, describe, it } from 'node:test';
import { WebSocketServer } from 'ws';
import { z } from 'zod';
import { action } from '../src/action.js';
import { ReflectionServerV2 } from '../src/reflection-v2.js';
import { Registry } from '../src/registry.js';
import { initNodeFeatures } from '../src/node.js';

initNodeFeatures();

describe('ReflectionServerV2', () => {
  let wss: WebSocketServer;
  let server: ReflectionServerV2;
  let registry: Registry;
  let port: number;
  let serverWs: any;

  beforeEach(() => {
    return new Promise<void>((resolve) => {
      wss = new WebSocketServer({ port: 0 });
      wss.on('listening', () => {
        port = (wss.address() as any).port;
        resolve();
      });
      wss.on('connection', (ws) => {
        serverWs = ws;
      });
      registry = new Registry();
    });
  });

  afterEach(async () => {
    if (server) {
      await server.stop();
    }
    if (serverWs) {
      serverWs.terminate();
    }
    await new Promise<void>((resolve) => {
      wss.close(() => resolve());
    });
  });

  it('should connect to the server and register', async () => {
    const connected = new Promise<void>((resolve) => {
      wss.on('connection', (ws) => {
        ws.on('message', (data) => {
          const msg = JSON.parse(data.toString());
          if (msg.method === 'register') {
            assert.strictEqual(msg.params.name, 'test-app');
            resolve();
          }
        });
      });
    });

    server = new ReflectionServerV2(registry, {
      url: `ws://localhost:${port}`,
      name: 'test-app',
    });
    await server.start();
    await connected;
  });

  it('should handle listActions', async () => {
    // Register a dummy action
    const testAction = action(
      {
        name: 'testAction',
        description: 'A test action',
        inputSchema: z.object({ foo: z.string() }),
        outputSchema: z.object({ bar: z.string() }),
        actionType: 'custom',
      },
      async (input) => ({ bar: input.foo })
    );
    registry.registerAction('custom', testAction);

    const gotListActions = new Promise<void>((resolve) => {
      wss.on('connection', (ws) => {
        ws.on('message', (data) => {
          const msg = JSON.parse(data.toString());
          if (msg.method === 'register') {
            // After registration, request listActions
            ws.send(
              JSON.stringify({
                jsonrpc: '2.0',
                method: 'listActions',
                id: '123',
              })
            );
          } else if (msg.id === '123') {
            assert.ok(msg.result['/custom/testAction']);
            assert.strictEqual(
              msg.result['/custom/testAction'].name,
              'testAction'
            );
            resolve();
          }
        });
      });
    });

    server = new ReflectionServerV2(registry, {
      url: `ws://localhost:${port}`,
    });
    await server.start();
    await gotListActions;
  });

  it('should handle runAction', async () => {
    const testAction = action(
      {
        name: 'testAction',
        inputSchema: z.object({ foo: z.string() }),
        outputSchema: z.object({ bar: z.string() }),
        actionType: 'custom',
      },
      async (input) => ({ bar: input.foo })
    );
    registry.registerAction('custom', testAction);

    const actionRun = new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(
        () => reject(new Error('runAction timeout')),
        2000
      );
      wss.on('connection', (ws) => {
        ws.on('message', (data) => {
          try {
            const msg = JSON.parse(data.toString());
            if (msg.method === 'register') {
              ws.send(
                JSON.stringify({
                  jsonrpc: '2.0',
                  method: 'runAction',
                  params: {
                    key: '/custom/testAction',
                    input: { foo: 'baz' },
                  },
                  id: '456',
                })
              );
            } else if (msg.id === '456') {
              if (msg.error) {
                reject(new Error(`runAction error: ${JSON.stringify(msg.error)}`));
                return;
              }
              assert.strictEqual(msg.result.result.bar, 'baz');
              clearTimeout(timeout);
              resolve();
            }
          } catch (e) {
            clearTimeout(timeout);
            reject(e);
          }
        });
      });
    });

    server = new ReflectionServerV2(registry, {
      url: `ws://localhost:${port}`,
    });
    await server.start();
    await actionRun;
  });

  it('should handle streaming runAction', async () => {
    const streamAction = action(
      {
        name: 'streamAction',
        inputSchema: z.object({ foo: z.string() }),
        outputSchema: z.string(),
        actionType: 'custom',
      },
      async (input, { sendChunk }) => {
        sendChunk('chunk1');
        sendChunk('chunk2');
        return 'done';
      }
    );
    registry.registerAction('custom', streamAction);

    const chunks: any[] = [];
    const actionRun = new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(
        () => reject(new Error('streamAction timeout')),
        2000
      );
      wss.on('connection', (ws) => {
        ws.on('message', (data) => {
          try {
            const msg = JSON.parse(data.toString());
            if (msg.method === 'register') {
              ws.send(
                JSON.stringify({
                  jsonrpc: '2.0',
                  method: 'runAction',
                  params: {
                    key: '/custom/streamAction',
                    input: { foo: 'baz' },
                    stream: true,
                  },
                  id: '789',
                })
              );
            } else if (msg.method === 'streamChunk') {
              chunks.push(msg.params.chunk);
            } else if (msg.id === '789') {
              if (msg.error) {
                reject(new Error(`streamAction error: ${JSON.stringify(msg.error)}`));
                return;
              }
              assert.strictEqual(msg.result.result, 'done');
              assert.deepStrictEqual(chunks, ['chunk1', 'chunk2']);
              clearTimeout(timeout);
              resolve();
            }
          } catch (e) {
            clearTimeout(timeout);
            reject(e);
          }
        });
      });
    });

    server = new ReflectionServerV2(registry, {
      url: `ws://localhost:${port}`,
    });
    await server.start();
    await actionRun;
  });
});
