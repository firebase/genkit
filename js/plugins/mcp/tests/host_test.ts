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
import { Genkit, genkit, ToolAction } from 'genkit';
import { logger } from 'genkit/logging';
import { afterEach, beforeEach, describe, it } from 'node:test';
import { createMcpHost, GenkitMcpHost } from '../src/index.js';
import { defineEchoModel, FakeTransport } from './fakes.js';

logger.setLogLevel('debug');

describe('createMcpHost', () => {
  let ai: Genkit;

  beforeEach(async () => {
    ai = genkit({});
    defineEchoModel(ai);
  });

  describe('host', () => {
    let fakeTransport1: FakeTransport;
    let fakeTransport2: FakeTransport;
    let clientHost: GenkitMcpHost;

    beforeEach(() => {
      clientHost = createMcpHost({
        name: 'test-mcp-host',
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
      await clientHost?.close();
    });

    it('should dynamically connect clients', async () => {
      // no server connected, no tools
      assert.deepStrictEqual(
        (await clientHost.getActiveTools(ai)).map((t) => t.__action.name),
        []
      );

      // connect fakeTransport1
      await clientHost.connect('test-mcp-host1', {
        transport: fakeTransport1,
      });

      assert.deepStrictEqual(
        (await clientHost.getActiveTools(ai)).map((t) => t.__action.name),
        ['test-mcp-host1/testTool1']
      );

      // connect fakeTransport2
      await clientHost.connect('test-mcp-host2', {
        transport: fakeTransport2,
      });

      assert.deepStrictEqual(
        (await clientHost.getActiveTools(ai)).map((t) => t.__action.name),
        ['test-mcp-host1/testTool1', 'test-mcp-host2/testTool2']
      );

      // disable
      await clientHost.disable('test-mcp-host1');

      assert.deepStrictEqual(
        (await clientHost.getActiveTools(ai)).map((t) => t.__action.name),
        ['test-mcp-host2/testTool2']
      );

      // reconnect
      await clientHost.enable('test-mcp-host1');

      assert.deepStrictEqual(
        (await clientHost.getActiveTools(ai)).map((t) => t.__action.name),
        ['test-mcp-host1/testTool1', 'test-mcp-host2/testTool2']
      );

      // disconnect
      await clientHost.disconnect('test-mcp-host1');

      assert.deepStrictEqual(
        (await clientHost.getActiveTools(ai)).map((t) => t.__action.name),
        ['test-mcp-host2/testTool2']
      );
    });

    it('updated roots', async () => {
      // no server connected, no tools
      assert.deepStrictEqual(
        (await clientHost.getActiveTools(ai)).map((t) => t.__action.name),
        []
      );

      // connect fakeTransport1
      await clientHost.connect('test-mcp-host1', {
        transport: fakeTransport1,
        roots: [
          {
            uri: `file:///foo`,
            name: 'foo',
          },
        ],
      });

      // MCP communicates roots async...
      await new Promise((r) => setTimeout(r, 10));

      assert.deepStrictEqual(fakeTransport1.roots, [
        {
          name: 'foo',
          uri: 'file:///foo',
        },
      ]);

      await clientHost.getClient('test-mcp-host1').updateRoots([
        {
          uri: `file:///bar`,
          name: 'bar',
        },
      ]);
      // MCP communicates roots async...
      await new Promise((r) => setTimeout(r, 10));

      assert.deepStrictEqual(fakeTransport1.roots, [
        {
          name: 'bar',
          uri: 'file:///bar',
        },
      ]);
    });
  });

  describe('tools', () => {
    let fakeTransport: FakeTransport;
    let clientHost: GenkitMcpHost;

    beforeEach(() => {
      fakeTransport = new FakeTransport();
      clientHost = createMcpHost({
        name: 'test-mcp-host',
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
      clientHost?.close();
    });

    it('should list tools', async () => {
      assert.deepStrictEqual(
        (await clientHost.getActiveTools(ai)).map((t) => t.__action.name),
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

      const tool: ToolAction = (await clientHost.getActiveTools(ai))[0];
      const response = await tool(
        {
          foo: 'bar',
        },
        { context: { mcp: { _meta: { soMeta: true } } } }
      );
      assert.deepStrictEqual(response, 'yep {"foo":"bar"}{"soMeta":true}');
    });

    it('should call the tool with _meta', async () => {
      fakeTransport.callToolResult = {
        content: [
          {
            type: 'text',
            text: 'yep {"foo":"bar"}',
          },
        ],
      };

      const tool = (await clientHost.getActiveTools(ai))[0];
      const response = await tool({
        foo: 'bar',
      });
      assert.deepStrictEqual(response, 'yep {"foo":"bar"}');
    });
  });

  describe('prompts', () => {
    let fakeTransport: FakeTransport;
    let clientHost: GenkitMcpHost;

    beforeEach(() => {
      fakeTransport = new FakeTransport();

      clientHost = createMcpHost({
        name: 'test-mcp-host',
        mcpServers: {
          'test-server': {
            transport: fakeTransport,
          },
        },
      });

      // Note: fakeTransport.prompts.push({ name: 'testPrompt' }); is moved to specific tests
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
      clientHost?.close();
    });

    it('should list active prompts', async () => {
      // Initially no prompts
      assert.deepStrictEqual(await clientHost.getActivePrompts(ai), []);

      // Add a prompt to the first transport
      fakeTransport.prompts.push({
        name: 'testPrompt1',
        arguments: [
          {
            name: 'foo',
            description: 'foo arg',
            required: false,
          },
        ],
        description: 'descr',
      });
      let activePrompts = await clientHost.getActivePrompts(ai);
      assert.strictEqual(activePrompts.length, 1);
      assert.deepStrictEqual(await activePrompts[0].render(), {
        messages: [
          {
            role: 'user',
            content: [
              {
                text: 'prompt says: hello',
              },
            ],
          },
        ],
      });

      // Add a second transport with another prompt
      const fakeTransport2 = new FakeTransport();
      fakeTransport2.prompts.push({
        name: 'testPrompt2',
      });
      await clientHost.connect('test-server-2', {
        transport: fakeTransport2,
      });

      activePrompts = await clientHost.getActivePrompts(ai);
      assert.deepStrictEqual(activePrompts[0].ref.metadata, {
        arguments: [
          {
            description: 'foo arg',
            name: 'foo',
            required: false,
          },
        ],
        description: 'descr',
      });
      assert.deepStrictEqual(
        activePrompts.map((p) => p.ref.name),
        ['testPrompt1', 'testPrompt2']
      );

      // Disable the first server
      await clientHost.disable('test-server');
      activePrompts = await clientHost.getActivePrompts(ai);
      assert.deepStrictEqual(
        activePrompts.map((p) => p.ref.name),
        ['testPrompt2']
      );

      // Enable the first server again
      await clientHost.enable('test-server');
      activePrompts = await clientHost.getActivePrompts(ai);
      assert.deepStrictEqual(
        activePrompts.map((p) => p.ref.name),
        ['testPrompt1', 'testPrompt2']
      );
    });

    it('should execute prompt', async () => {
      fakeTransport.prompts.push({
        name: 'testPrompt',
      });
      const prompt = await clientHost.getPrompt(
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
      fakeTransport.prompts.push({
        name: 'testPrompt',
      });
      const prompt = await clientHost.getPrompt(
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

    it('should render prompt with _meta', async () => {
      fakeTransport.prompts.push({
        name: 'testPrompt',
      });
      const prompt = await clientHost.getPrompt(
        ai,
        'test-server',
        'testPrompt',
        { model: 'echoModel', config: { temperature: 11 } }
      );
      assert.ok(prompt);
      const request = await prompt.render(
        {
          input: 'hello',
        },
        { context: { mcp: { _meta: { soMeta: true } } } }
      );

      assert.deepStrictEqual(request.messages, [
        { role: 'user', content: [{ text: 'prompt says: hello' }] },
        { role: 'model', content: [{ text: '{"soMeta":true}' }] },
      ]);
    });

    it('should stream prompt', async () => {
      fakeTransport.prompts.push({
        name: 'testPrompt',
      });
      const prompt = await clientHost.getPrompt(
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
