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
import { Genkit, genkit } from 'genkit';
import { logger } from 'genkit/logging';
import { afterEach, beforeEach, describe, it } from 'node:test';
import { GenkitMcpManager, createMcpManager } from '../src/index.js';
import { FakeTransport, defineEchoModel } from './utils.js';

logger.setLogLevel('debug');

describe('createMcpManager', () => {
  let ai: Genkit;

  beforeEach(async () => {
    ai = genkit({});
    defineEchoModel(ai);
  });

  describe('manager', () => {
    let fakeTransport1: FakeTransport;
    let fakeTransport2: FakeTransport;
    let clientManager: GenkitMcpManager;

    beforeEach(() => {
      clientManager = createMcpManager({
        name: 'test-mcp-manager',
      });

      fakeTransport1 = new FakeTransport();
      fakeTransport1.tools.push({
        name: 'testTool1',
        inputSchema: {
          type: 'object',
          properties: {
            foo: {
              type: 'string',
            },
          },
          required: ['foo'],
          additionalProperties: true,
          $schema: 'http://json-schema.org/draft-07/schema#',
        },
        description: 'test tool 1',
      });

      fakeTransport2 = new FakeTransport();
      fakeTransport2.tools.push({
        name: 'testTool2',
        inputSchema: {
          type: 'object',
          properties: {
            foo: {
              type: 'string',
            },
          },
          required: ['foo'],
          additionalProperties: true,
          $schema: 'http://json-schema.org/draft-07/schema#',
        },
        description: 'test tool 2',
      });
    });

    afterEach(async () => {
      await clientManager?.close();
    });

    it('should dynamically connect clients', async () => {
      // no server connected, no tools
      assert.deepStrictEqual(
        (await clientManager.getActiveTools(ai)).map((t) => t.__action.name),
        []
      );

      // connect fakeTransport1
      await clientManager.connect('test-mcp-manager1', {
        transport: fakeTransport1,
      });

      assert.deepStrictEqual(
        (await clientManager.getActiveTools(ai)).map((t) => t.__action.name),
        ['test-mcp-manager1/testTool1']
      );

      // connect fakeTransport2
      await clientManager.connect('test-mcp-manager2', {
        transport: fakeTransport2,
      });

      assert.deepStrictEqual(
        (await clientManager.getActiveTools(ai)).map((t) => t.__action.name),
        ['test-mcp-manager1/testTool1', 'test-mcp-manager2/testTool2']
      );

      // disable
      await clientManager.disable('test-mcp-manager1');

      assert.deepStrictEqual(
        (await clientManager.getActiveTools(ai)).map((t) => t.__action.name),
        ['test-mcp-manager2/testTool2']
      );

      // reconnect
      await clientManager.enable('test-mcp-manager1');

      assert.deepStrictEqual(
        (await clientManager.getActiveTools(ai)).map((t) => t.__action.name),
        ['test-mcp-manager1/testTool1', 'test-mcp-manager2/testTool2']
      );

      // disconnect
      await clientManager.disconnect('test-mcp-manager1');

      assert.deepStrictEqual(
        (await clientManager.getActiveTools(ai)).map((t) => t.__action.name),
        ['test-mcp-manager2/testTool2']
      );
    });
  });

  describe('tools', () => {
    let fakeTransport: FakeTransport;
    let clientManager: GenkitMcpManager;

    beforeEach(() => {
      fakeTransport = new FakeTransport();
      clientManager = createMcpManager({
        name: 'test-mcp-manager',
        mcpServers: {
          'test-server': {
            transport: fakeTransport,
          },
        },
      });

      fakeTransport.tools.push({
        name: 'testTool',
        inputSchema: {
          type: 'object',
          properties: {
            foo: {
              type: 'string',
            },
          },
          required: ['foo'],
          additionalProperties: true,
          $schema: 'http://json-schema.org/draft-07/schema#',
        },
        description: 'test tool',
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
      fakeTransport.callToolResult = {
        content: [
          {
            type: 'text',
            text: 'yep {"foo":"bar"}',
          },
        ],
      };

      const tool = (await clientManager.getActiveTools(ai))[0];
      const response = await tool({
        foo: 'bar',
      });
      assert.deepStrictEqual(response, 'yep {"foo":"bar"}');
    });
  });

  describe('prompts', () => {
    let fakeTransport: FakeTransport;
    let clientManager: GenkitMcpManager;

    beforeEach(() => {
      fakeTransport = new FakeTransport();

      clientManager = createMcpManager({
        name: 'test-mcp-manager',
        mcpServers: {
          'test-server': {
            transport: fakeTransport,
          },
        },
      });

      fakeTransport.prompts.push({
        name: 'testPrompt',
      });
      fakeTransport.getPromptResult = {
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: 'prompt says: hello',
            },
          },
        ],
      };
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
