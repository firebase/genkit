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

import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import * as assert from 'assert';
import express from 'express';
import { Genkit, genkit, z } from 'genkit';
import { logger } from 'genkit/logging';
import { ModelAction } from 'genkit/model';
import getPort from 'get-port';
import * as http from 'http';
import { afterEach, beforeEach, describe, it } from 'node:test';
import {
  GenkitMcpManager,
  createMcpManager,
  createMcpServer,
} from '../src/index.js';
import { GenkitMcpServer } from '../src/server.js';

logger.setLogLevel('debug');

describe('mcp', async () => {
  let ai: Genkit;
  let mcpServer: GenkitMcpServer;
  let mcpHttpServer: http.Server;
  let port: number;
  let clientManager: GenkitMcpManager;

  beforeEach(async () => {
    ai = genkit({});

    defineEchoModel(ai);

    ai.definePrompt({
      name: 'testPrompt',
      model: 'echoModel',
      prompt: 'prompt says: {{input}}',
    });

    ai.defineTool(
      {
        name: 'testTool',
        description: 'test tool',
        inputSchema: z.object({ foo: z.string() }),
      },
      async (input) => `yep ${JSON.stringify(input)}`
    );

    mcpServer = createMcpServer(ai, { name: 'orders', version: '0.0.1' });

    const app = express();
    let transport: SSEServerTransport | null = null;

    app.get('/sse', (req, res) => {
      transport = new SSEServerTransport('/messages', res);
      mcpServer.server!.connect(transport);
    });

    app.post('/messages', (req, res) => {
      if (transport) {
        transport.handlePostMessage(req, res);
      }
    });

    port = await getPort();
    mcpHttpServer = app.listen(port, () => {
      console.log(`MCP server listening on http://localhost:${port}`);
    });
  });

  afterEach(() => {
    mcpHttpServer.close();
    mcpServer.server?.close();
  });

  describe('tools', () => {
    beforeEach(() => {
      clientManager = createMcpManager({
        name: 'test-mcp-manager',
        mcpServers: {
          'test-server': {
            url: `http://localhost:${port}/sse`,
          },
        },
      });
    });

    afterEach(() => {
      clientManager?.close();
    });

    it('should list tools', async () => {
      assert.deepStrictEqual(
        (await clientManager.getActiveTools(ai)).map((t) => t.__action.name),
        ['test-server/testTool']
      );
    });

    it('should call the tool', async () => {
      const response = await (
        await clientManager.getActiveTools(ai)
      )[0]({
        foo: 'bar',
      });
      assert.deepStrictEqual(response, 'yep {"foo":"bar"}');
    });
  });

  describe('prompts', () => {
    beforeEach(() => {
      clientManager = createMcpManager({
        name: 'test-mcp-manager',
        mcpServers: {
          'test-server': {
            url: `http://localhost:${port}/sse`,
          },
        },
      });
    });

    afterEach(() => {
      clientManager?.close();
    });

    it('should execute prompt', async () => {
      const prompt = await clientManager.getPrompt(
        ai,
        'test-server',
        'testPrompt',
        { model: 'echoModel', config: { temperature: 11 } }
      );
      assert.ok(prompt);
      const { text } = await prompt({
        input: 'hello',
      });

      assert.strictEqual(
        text,
        'Echo: prompt says: hello; config: {"temperature":11}'
      );
    });

    it('should render prompt', async () => {
      const prompt = await clientManager.getPrompt(
        ai,
        'test-server',
        'testPrompt',
        { model: 'echoModel', config: { temperature: 11 } }
      );
      assert.ok(prompt);
      const request = await prompt.render({
        input: 'hello',
      });

      assert.deepStrictEqual(request.messages, [
        { role: 'user', content: [{ text: 'prompt says: hello' }] },
      ]);
    });

    it('should stream prompt', async () => {
      const prompt = await clientManager.getPrompt(
        ai,
        'test-server',
        'testPrompt',
        { model: 'echoModel', config: { temperature: 11 } }
      );
      assert.ok(prompt);
      const { stream, response } = prompt.stream({
        input: 'hello',
      });

      const chunks = [] as string[];
      for await (const chunk of stream) {
        chunks.push(chunk.text);
      }

      assert.deepStrictEqual(chunks, ['3', '2', '1']);
      assert.strictEqual(
        (await response).text,
        'Echo: prompt says: hello; config: {"temperature":11}'
      );
    });
  });
});

export function defineEchoModel(ai: Genkit): ModelAction {
  const model = ai.defineModel(
    {
      name: 'echoModel',
    },
    async (request, streamingCallback) => {
      (model as any).__test__lastRequest = request;
      (model as any).__test__lastStreamingCallback = streamingCallback;
      if (streamingCallback) {
        streamingCallback({
          content: [
            {
              text: '3',
            },
          ],
        });
        streamingCallback({
          content: [
            {
              text: '2',
            },
          ],
        });
        streamingCallback({
          content: [
            {
              text: '1',
            },
          ],
        });
      }
      return {
        message: {
          role: 'model',
          content: [
            {
              text:
                'Echo: ' +
                request.messages
                  .map(
                    (m) =>
                      (m.role === 'user' || m.role === 'model'
                        ? ''
                        : `${m.role}: `) + m.content.map((c) => c.text).join()
                  )
                  .join(),
            },
            {
              text: '; config: ' + JSON.stringify(request.config),
            },
          ],
        },
        finishReason: 'stop',
      };
    }
  );
  return model;
}
