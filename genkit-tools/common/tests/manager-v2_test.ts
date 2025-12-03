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

import { afterEach, beforeEach, describe, expect, it } from '@jest/globals';
import WebSocket from 'ws';
import { RuntimeManagerV2 } from '../src/manager/manager-v2';
import { RuntimeEvent } from '../src/manager/types';

describe('RuntimeManagerV2', () => {
  let manager: RuntimeManagerV2;
  let wsClient: WebSocket;
  let port: number;

  beforeEach(async () => {
    manager = await RuntimeManagerV2.create({
      projectRoot: './',
    });
    port = manager.port!;
  });

  afterEach(async () => {
    if (wsClient) {
      wsClient.close();
    }
    // Clean up server
    await manager.close();
  });

  it('should accept connections and handle registration', (done) => {
    wsClient = new WebSocket(`ws://localhost:${port}`);

    wsClient.on('open', () => {
      const registerMessage = {
        jsonrpc: '2.0',
        method: 'register',
        params: {
          id: 'test-runtime-1',
          pid: 1234,
          name: 'Test Runtime',
          genkitVersion: '0.0.1',
          reflectionApiSpecVersion: 1,
        },
        id: 1,
      };
      wsClient.send(JSON.stringify(registerMessage));
    });

    manager.onRuntimeEvent((event, runtime) => {
      if (event === RuntimeEvent.ADD) {
        expect(runtime.id).toBe('test-runtime-1');
        expect(runtime.pid).toBe(1234);
        expect(manager.listRuntimes().length).toBe(1);
        done();
      }
    });
  });

  it('should send requests and handle responses', async () => {
    wsClient = new WebSocket(`ws://localhost:${port}`);

    await new Promise<void>((resolve) => {
      wsClient.on('open', () => {
        wsClient.send(
          JSON.stringify({
            jsonrpc: '2.0',
            method: 'register',
            params: { id: 'test-runtime-2', pid: 1234 },
            id: 1,
          })
        );
        // Wait for server to acknowledge or just wait a bit
        setTimeout(resolve, 100);
      });
    });

    // Mock runtime response to runAction
    wsClient.on('message', (data) => {
      const message = JSON.parse(data.toString());
      if (message.method === 'runAction') {
        const response = {
          jsonrpc: '2.0',
          result: {
            result: 'Hello World',
            telemetry: {
              traceId: '1234',
            },
          },
          id: message.id,
        };
        wsClient.send(JSON.stringify(response));
      }
    });

    const response = await manager.runAction({
      key: 'testAction',
      input: {},
    });

    expect(response.result).toBe('Hello World');
    expect(response.telemetry).toStrictEqual({
      traceId: '1234',
    });
  });

  it('should handle streaming', async () => {
    wsClient = new WebSocket(`ws://localhost:${port}`);

    await new Promise<void>((resolve) => {
      wsClient.on('open', () => {
        wsClient.send(
          JSON.stringify({
            jsonrpc: '2.0',
            method: 'register',
            params: { id: 'test-runtime-3', pid: 1234 },
            id: 1,
          })
        );
        setTimeout(resolve, 100);
      });
    });

    wsClient.on('message', (data) => {
      const message = JSON.parse(data.toString());
      if (message.method === 'runAction' && message.params.stream) {
        // Send chunk 1
        wsClient.send(
          JSON.stringify({
            jsonrpc: '2.0',
            method: 'streamChunk',
            params: { requestId: message.id, chunk: { content: 'Hello' } },
          })
        );
        // Send chunk 2
        wsClient.send(
          JSON.stringify({
            jsonrpc: '2.0',
            method: 'streamChunk',
            params: { requestId: message.id, chunk: { content: ' World' } },
          })
        );
        // Send final result
        wsClient.send(
          JSON.stringify({
            jsonrpc: '2.0',
            result: { result: 'Hello World', telemetry: {} },
            id: message.id,
          })
        );
      }
    });

    const chunks: any[] = [];
    const response = await manager.runAction(
      {
        key: 'testAction',
        input: {},
      },
      (chunk) => {
        chunks.push(chunk);
      }
    );

    expect(chunks).toHaveLength(2);
    expect(chunks[0]).toEqual({ content: 'Hello' });
    expect(chunks[1]).toEqual({ content: ' World' });
    expect(response.result).toBe('Hello World');
    expect(response.telemetry).toBeDefined();
  });

  it('should handle streaming errors and massage the error object', async () => {
    wsClient = new WebSocket(`ws://localhost:${port}`);

    await new Promise<void>((resolve) => {
      wsClient.on('open', () => {
        wsClient.send(
          JSON.stringify({
            jsonrpc: '2.0',
            method: 'register',
            params: { id: 'test-runtime-error', pid: 1234 },
            id: 1,
          })
        );
        setTimeout(resolve, 100);
      });
    });

    wsClient.on('message', (data) => {
      const message = JSON.parse(data.toString());
      if (message.method === 'runAction' && message.params.stream) {
        // Send chunk 1
        wsClient.send(
          JSON.stringify({
            jsonrpc: '2.0',
            method: 'streamChunk',
            params: { requestId: message.id, chunk: { content: 'Hello' } },
          })
        );
        // Send error
        const errorResponse = {
          code: -32000,
          message: 'Test Error',
          data: {
            code: 13,
            message: 'Test Error',
            details: {
              stack: 'Error stack...',
              traceId: 'trace-123',
            },
          },
        };
        wsClient.send(
          JSON.stringify({
            jsonrpc: '2.0',
            error: errorResponse,
            id: message.id,
          })
        );
      }
    });

    const chunks: any[] = [];
    try {
      await manager.runAction(
        {
          key: 'testAction',
          input: {},
        },
        (chunk) => {
          chunks.push(chunk);
        }
      );
      throw new Error('Should have thrown');
    } catch (err: any) {
      expect(chunks).toHaveLength(1);
      expect(chunks[0]).toEqual({ content: 'Hello' });
      expect(err.message).toBe('Test Error');
      expect(err.data).toBeDefined();
      expect(err.data.data.genkitErrorMessage).toBe('Test Error');
      expect(err.data.stack).toBe('Error stack...');
      expect(err.data.data.genkitErrorDetails).toEqual({
        stack: 'Error stack...',
        traceId: 'trace-123',
      });
    }
  });
});
