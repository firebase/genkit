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

const TEST_PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=';

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

    it('should call the tool (v1)', async () => {
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

    it('should call the tool with _meta (v1)', async () => {
      fakeTransport.callToolResult = {
        content: [
          {
            type: 'text',
            text: 'yep {"foo":"bar"}',
          },
        ],
      };

      const tool = (await clientHost.getActiveTools(ai))[0];
      const response = await tool(
        {
          foo: 'bar',
        },
        { context: { mcp: { _meta: { soMeta: true } } } }
      );
      assert.deepStrictEqual(response, 'yep {"foo":"bar"}{"soMeta":true}');
    });

    it('should call the tool with _meta (v2)', async () => {
      const v2Host = createMcpHost({
        name: 'v2-host',
        multipart: true,
        mcpServers: {
          'v2-server': {
            transport: fakeTransport,
          },
        },
      });

      fakeTransport.callToolResult = {
        content: [
          {
            type: 'text',
            text: 'yep {"foo":"bar"}',
          },
        ],
      };

      const tool = (await v2Host.getActiveTools(ai))[0];
      const response = await tool(
        {
          foo: 'bar',
        },
        { context: { mcp: { _meta: { soMeta: true } } } }
      );
      assert.deepStrictEqual(response, {
        content: [
          {
            text: 'yep {"foo":"bar"}',
          },
          {
            text: '{"soMeta":true}',
          },
        ],
        output: 'yep {"foo":"bar"}{"soMeta":true}',
      });

      await v2Host.close();
    });

    it('should call the tool as a v2 multipart tool', async () => {
      const v2Host = createMcpHost({
        name: 'v2-host',
        multipart: true,
        mcpServers: {
          'v2-server': {
            transport: fakeTransport,
          },
        },
      });

      fakeTransport.callToolResult = {
        content: [
          {
            type: 'image',
            data: TEST_PNG_BASE64,
            mimeType: 'image/png',
          },
          {
            type: 'text',
            text: 'yep {"foo":"bar"}',
          },
        ],
      };

      const tool = (await v2Host.getActiveTools(ai))[0];
      const response = await tool({
        foo: 'bar',
      });

      assert.deepStrictEqual(response, {
        content: [
          {
            media: {
              contentType: 'image/png',
              url: `data:image/png;base64,${TEST_PNG_BASE64}`,
            },
          },
          { text: 'yep {"foo":"bar"}' },
        ],
        output: fakeTransport.callToolResult,
      });

      await v2Host.close();
    });

    it('should handle tool errors gracefully (v1)', async () => {
      fakeTransport.callToolResult = {
        isError: true,
        content: [
          {
            type: 'text',
            text: 'An error occurred during tool execution',
          },
        ],
      };

      const tool = (await clientHost.getActiveTools(ai))[0];
      const response = await tool({
        foo: 'bar',
      });
      assert.deepStrictEqual(response, {
        error: 'An error occurred during tool execution',
      });
    });

    it('should handle tool errors gracefully (v2)', async () => {
      const v2Host = createMcpHost({
        name: 'v2-host',
        multipart: true,
        mcpServers: {
          'v2-server': {
            transport: fakeTransport,
          },
        },
      });

      fakeTransport.callToolResult = {
        isError: true,
        content: [
          {
            type: 'text',
            text: 'An error occurred during tool execution',
          },
        ],
      };

      const tool = (await v2Host.getActiveTools(ai))[0];
      const response = await tool({
        foo: 'bar',
      });
      assert.deepStrictEqual(response, {
        output: { error: 'An error occurred during tool execution' },
      });

      await v2Host.close();
    });

    it('should parse rich content like images (v1)', async () => {
      fakeTransport.callToolResult = {
        content: [
          {
            type: 'text',
            text: 'Here is your image:',
          },
          {
            type: 'image',
            data: TEST_PNG_BASE64,
            mimeType: 'image/png',
          },
        ],
      };

      const tool = (await clientHost.getActiveTools(ai))[0];
      const response = await tool({
        foo: 'bar',
      });

      assert.deepStrictEqual(response, fakeTransport.callToolResult);
    });

    it('should parse rich content like images (v2)', async () => {
      const v2Host = createMcpHost({
        name: 'v2-host',
        multipart: true,
        mcpServers: {
          'v2-server': {
            transport: fakeTransport,
          },
        },
      });

      fakeTransport.callToolResult = {
        content: [
          {
            type: 'text',
            text: 'Here is your image:',
          },
          {
            type: 'image',
            data: TEST_PNG_BASE64,
            mimeType: 'image/png',
          },
        ],
      };

      const tool = (await v2Host.getActiveTools(ai))[0];
      const response = await tool({
        foo: 'bar',
      });

      assert.deepStrictEqual(response, {
        content: [
          { text: 'Here is your image:' },
          {
            media: {
              contentType: 'image/png',
              url: `data:image/png;base64,${TEST_PNG_BASE64}`,
            },
          },
        ],
        output: fakeTransport.callToolResult,
      });

      await v2Host.close();
    });

    it('should return raw responses when rawToolResponses config is enabled (v1)', async () => {
      const rawHost = createMcpHost({
        name: 'raw-host',
        rawToolResponses: true,
        mcpServers: {
          'raw-server': {
            transport: fakeTransport,
          },
        },
      });

      fakeTransport.callToolResult = {
        content: [
          {
            type: 'text',
            text: 'raw content only',
          },
        ],
      };

      const tool = (await rawHost.getActiveTools(ai))[0];
      const response = await tool({
        foo: 'bar',
      });

      assert.deepStrictEqual(response, fakeTransport.callToolResult);

      await rawHost.close();
    });

    it('should return raw responses when rawToolResponses config is enabled (v2)', async () => {
      const rawHost = createMcpHost({
        name: 'raw-host',
        multipart: true,
        rawToolResponses: true,
        mcpServers: {
          'raw-server': {
            transport: fakeTransport,
          },
        },
      });

      fakeTransport.callToolResult = {
        content: [
          {
            type: 'text',
            text: 'raw content only',
          },
        ],
      };

      const tool = (await rawHost.getActiveTools(ai))[0];
      const response = await tool({
        foo: 'bar',
      });

      // The v2 wrapper puts the raw response into output if rawToolResponses is true
      assert.deepStrictEqual(response, {
        output: fakeTransport.callToolResult,
      });

      await rawHost.close();
    });

    it('should parse JSON string responses (v1)', async () => {
      fakeTransport.callToolResult = {
        content: [
          {
            type: 'text',
            text: '{"foo":"bar"}',
          },
        ],
      };

      const tool = (await clientHost.getActiveTools(ai))[0];
      const response = await tool({
        foo: 'bar',
      });
      assert.deepStrictEqual(response, { foo: 'bar' });
    });

    it('should parse JSON string responses (v2)', async () => {
      const v2Host = createMcpHost({
        name: 'v2-host',
        multipart: true,
        mcpServers: {
          'v2-server': {
            transport: fakeTransport,
          },
        },
      });

      fakeTransport.callToolResult = {
        content: [
          {
            type: 'text',
            text: '{"foo":"bar"}',
          },
        ],
      };

      const tool = (await v2Host.getActiveTools(ai))[0];
      const response = await tool({
        foo: 'bar',
      });

      assert.deepStrictEqual(response, {
        content: [
          {
            text: '{"foo":"bar"}',
          },
        ],
        output: { foo: 'bar' },
      });

      await v2Host.close();
    });

    it('should handle CompatibilityCallToolResult (v1)', async () => {
      // FakeTransport usually expects CallToolResult, but for testing
      // we can force it to return CompatibilityCallToolResult
      fakeTransport.callToolResult = {
        toolResult: { legacy: true },
      } as any;

      const tool = (await clientHost.getActiveTools(ai))[0];
      const response = await tool({
        foo: 'bar',
      });
      assert.deepStrictEqual(response, { legacy: true });
    });

    it('should handle CompatibilityCallToolResult (v2)', async () => {
      const v2Host = createMcpHost({
        name: 'v2-host',
        multipart: true,
        mcpServers: {
          'v2-server': {
            transport: fakeTransport,
          },
        },
      });

      fakeTransport.callToolResult = {
        toolResult: { legacy: true },
      } as any;

      const tool = (await v2Host.getActiveTools(ai))[0];
      const response = await tool({
        foo: 'bar',
      });

      assert.deepStrictEqual(response, {
        output: { legacy: true },
      });

      await v2Host.close();
    });

    it('should call the tool (v2)', async () => {
      const v2Host = createMcpHost({
        name: 'v2-host',
        multipart: true,
        mcpServers: {
          'v2-server': {
            transport: fakeTransport,
          },
        },
      });

      fakeTransport.callToolResult = {
        content: [
          {
            type: 'text',
            text: 'yep {"foo":"bar"}',
          },
        ],
      };

      const tool = (await v2Host.getActiveTools(ai))[0];
      const response = await tool({
        foo: 'bar',
      });

      assert.deepStrictEqual(response, {
        content: [
          {
            text: 'yep {"foo":"bar"}',
          },
        ],
        output: 'yep {"foo":"bar"}',
      });

      await v2Host.close();
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
        _meta: { foo: true },
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
        mcp: { _meta: { foo: true } },
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
    });

    afterEach(() => {
      clientHost?.close();
    });

    it('should list active resources', async () => {
      // Initially no prompts
      assert.deepStrictEqual(await clientHost.getActiveResources(ai), []);

      // Add a prompt to the first transport
      fakeTransport.resources.push({
        name: 'testResource1',
        uri: 'test://resource/1',
        description: 'test resource 1',
        _meta: { foo: true },
      });
      fakeTransport.resourceTemplates.push({
        name: 'testResourceTmpl',
        uriTemplate: 'test://resource/{id}',
        description: 'test resource template',
        _meta: { foo: true },
      });
      let activeResources = await clientHost.getActiveResources(ai);
      assert.strictEqual(activeResources.length, 2);

      // Add a second transport with another prompt
      const fakeTransport2 = new FakeTransport();
      fakeTransport2.resources.push({
        name: 'testResource2',
        uri: 'test://resource/2',
        description: 'test resource 2',
        _meta: { foo: true },
      });
      await clientHost.connect('test-server-2', {
        transport: fakeTransport2,
      });

      activeResources = await clientHost.getActiveResources(ai);
      assert.deepStrictEqual(activeResources[0].__action.metadata, {
        type: 'resource',
        dynamic: true,
        resource: {
          template: undefined,
          uri: 'test://resource/1',
        },
        mcp: { _meta: { foo: true } },
      });
      assert.deepStrictEqual(
        activeResources.map((p) => p.__action.name),
        [
          'test-server/testResource1',
          'test-server/testResourceTmpl',
          'test-server-2/testResource2',
        ]
      );

      // Disable the first server
      await clientHost.disable('test-server');
      activeResources = await clientHost.getActiveResources(ai);
      assert.deepStrictEqual(
        activeResources.map((p) => p.__action.name),
        ['test-server-2/testResource2']
      );

      // Enable the first server again
      await clientHost.enable('test-server');
      activeResources = await clientHost.getActiveResources(ai);
      assert.deepStrictEqual(
        activeResources.map((p) => p.__action.name),
        [
          'test-server/testResource1',
          'test-server/testResourceTmpl',
          'test-server-2/testResource2',
        ]
      );
    });

    it('should render resource', async () => {
      fakeTransport.resources.push({
        name: 'testResource1',
        uri: 'test://resource/1',
        description: 'test resource 1',
        _meta: { foo: true },
      });
      fakeTransport.readResourceResult = {
        contents: [
          {
            uri: 'test://resource/1',
            text: 'text resource',
          },
          {
            uri: 'test://resource/1',
            blob: 'UmVzb3VyY2UgMjogVGhpcyBpcyBhIGJhc2U2NCBibG9i',
            mimeType: 'application/png',
          },
        ],
      };
      const prompt = (await clientHost.getActiveResources(ai))[0];
      assert.ok(prompt);

      const response = await prompt.attach(ai.registry)({
        uri: 'test://resource/1',
      });

      assert.deepStrictEqual(response, {
        content: [
          {
            text: 'text resource',
            metadata: {
              resource: {
                uri: 'test://resource/1',
              },
            },
          },
          {
            media: {
              contentType: 'application/png',
              url: 'data:application/png;base64,UmVzb3VyY2UgMjogVGhpcyBpcyBhIGJhc2U2NCBibG9i',
            },
            metadata: {
              resource: {
                uri: 'test://resource/1',
              },
            },
          },
        ],
      });
    });
  });
});
