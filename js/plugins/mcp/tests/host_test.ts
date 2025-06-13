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
import { GenkitMcpHost, createMcpHost } from '../src/index.js';
import { FakeTransport, defineEchoModel } from './fakes.js';

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
      assert.strictEqual(activePrompts.length, 2);

      // Disable the first server
      await clientHost.disable('test-server');
      activePrompts = await clientHost.getActivePrompts(ai);
      assert.strictEqual(activePrompts.length, 1);

      // Enable the first server again
      await clientHost.enable('test-server');
      activePrompts = await clientHost.getActivePrompts(ai);
      assert.strictEqual(activePrompts.length, 2);
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

  describe('resources', () => {
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

      fakeTransport.resources.push({
        name: 'testResource',
        uri: 'test://foo/bar',
        description: 'test resource',
      });

      fakeTransport.resourceTemplates.push({
        name: 'tesetTemplate',
        uriTemplate: 'template://foo/{bar}',
        description: 'test resource template',
      });
    });

    afterEach(() => {
      clientHost?.close();
    });

    it('should list resource tools', async () => {
      assert.deepStrictEqual(
        (await clientHost.getActiveTools(ai, { resourceTools: true })).map(
          (t) => t.__action.name
        ),
        [
          'test-server/testTool',
          'test-mcp-host/list_resources',
          'test-mcp-host/read_resource',
        ]
      );
    });

    it('should list resources and templates', async () => {
      const listResourcesTool = (
        await clientHost.getActiveTools(ai, { resourceTools: true })
      ).find((t) => t.__action.name === 'test-mcp-host/list_resources');
      assert.ok(listResourcesTool);

      const response = await listResourcesTool({});
      assert.deepStrictEqual(response, {
        servers: {
          'test-mcp-host': {
            resources: [
              {
                description: 'test resource',
                name: 'testResource',
                uri: 'test://foo/bar',
              },
            ],
            resourceTemplates: [
              {
                description: 'test resource template',
                name: 'tesetTemplate',
                uriTemplate: 'template://foo/{bar}',
              },
            ],
          },
        },
      });
    });

    it('should read resources', async () => {
      fakeTransport.readResourceResult = {
        contents: [
          {
            uri: 'test://foo/bar',
            text: 'hello world',
          },
        ],
      };

      const readResourceTool = (
        await clientHost.getActiveTools(ai, { resourceTools: true })
      ).find((t) => t.__action.name === 'test-mcp-host/read_resource');
      assert.ok(readResourceTool);

      const response = await readResourceTool({
        server: 'test-server',
        uri: 'test://foo/bar',
      });
      assert.deepStrictEqual(response, {
        contents: [
          {
            text: 'hello world',
            uri: 'test://foo/bar',
          },
        ],
      });
    });
  });
});
