/**
 * Copyright 2025 Google LLC
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
import type { Part } from 'genkit';
import { describe, it } from 'node:test';

import { BetaRunner } from '../src/runner/beta.js';
import { createMockAnthropicClient } from './mocks/anthropic-client.js';

describe('BetaRunner.toAnthropicMessageContent', () => {
  function createRunner() {
    return new BetaRunner({
      name: 'anthropic/claude-3-5-haiku',
      client: createMockAnthropicClient(),
      cacheSystemPrompt: false,
    });
  }

  it('converts PDF media parts into document blocks', () => {
    const runner = createRunner();
    const part: Part = {
      media: {
        contentType: 'application/pdf',
        url: 'data:application/pdf;base64,UEsDBAoAAAAAAD',
      },
    };

    const result = (runner as any).toAnthropicMessageContent(part);

    assert.strictEqual(result.type, 'document');
    assert.ok(result.source);
    assert.strictEqual(result.source.type, 'base64');
    assert.strictEqual(result.source.media_type, 'application/pdf');
    assert.ok(result.source.data);
  });

  it('throws when tool request ref is missing', () => {
    const runner = createRunner();
    const part: Part = {
      toolRequest: {
        name: 'do_something',
        input: { foo: 'bar' },
      },
    };

    assert.throws(() => {
      (runner as any).toAnthropicMessageContent(part);
    }, /Tool request ref is required/);
  });

  it('maps tool request with ref into tool_use block', () => {
    const runner = createRunner();
    const part: Part = {
      toolRequest: {
        ref: 'tool-123',
        name: 'do_something',
        input: { foo: 'bar' },
      },
    };

    const result = (runner as any).toAnthropicMessageContent(part);

    assert.strictEqual(result.type, 'tool_use');
    assert.strictEqual(result.id, 'tool-123');
    assert.strictEqual(result.name, 'do_something');
    assert.deepStrictEqual(result.input, { foo: 'bar' });
  });

  it('throws when tool response ref is missing', () => {
    const runner = createRunner();
    const part: Part = {
      toolResponse: {
        name: 'do_something',
        output: 'done',
      },
    };

    assert.throws(() => {
      (runner as any).toAnthropicMessageContent(part);
    }, /Tool response ref is required/);
  });

  it('maps tool response into tool_result block containing text response', () => {
    const runner = createRunner();
    const part: Part = {
      toolResponse: {
        name: 'do_something',
        ref: 'tool-abc',
        output: 'done',
      },
    };

    const result = (runner as any).toAnthropicMessageContent(part);

    assert.strictEqual(result.type, 'tool_result');
    assert.strictEqual(result.tool_use_id, 'tool-abc');
    assert.deepStrictEqual(result.content, [{ type: 'text', text: 'done' }]);
  });

  it('should handle WEBP image data URLs', () => {
    const runner = createRunner();
    const part: Part = {
      media: {
        contentType: 'image/webp',
        url: 'data:image/webp;base64,AAA',
      },
    };

    const result = (runner as any).toAnthropicMessageContent(part);

    assert.strictEqual(result.type, 'image');
    assert.strictEqual(result.source.type, 'base64');
    assert.strictEqual(result.source.media_type, 'image/webp');
    assert.strictEqual(result.source.data, 'AAA');
  });

  it('should prefer data URL content type over media.contentType for WEBP', () => {
    const runner = createRunner();
    const part: Part = {
      media: {
        // Even if contentType says PNG, data URL says WEBP - should use WEBP
        contentType: 'image/png',
        url: 'data:image/webp;base64,AAA',
      },
    };

    const result = (runner as any).toAnthropicMessageContent(part);

    assert.strictEqual(result.type, 'image');
    assert.strictEqual(result.source.type, 'base64');
    // Key fix: should use data URL type (webp), not contentType (png)
    assert.strictEqual(result.source.media_type, 'image/webp');
    assert.strictEqual(result.source.data, 'AAA');
  });

  it('should throw helpful error for text/plain in toAnthropicMessageContent', () => {
    const runner = createRunner();
    const part: Part = {
      media: {
        contentType: 'text/plain',
        url: 'data:text/plain;base64,AAA',
      },
    };

    assert.throws(
      () => {
        (runner as any).toAnthropicMessageContent(part);
      },
      (error: Error) => {
        return (
          error.message.includes('Text files should be sent as text content') &&
          error.message.includes('text:')
        );
      }
    );
  });

  it('should throw helpful error for text/plain with remote URL', () => {
    const runner = createRunner();
    const part: Part = {
      media: {
        contentType: 'text/plain',
        url: 'https://example.com/file.txt',
      },
    };

    assert.throws(
      () => {
        (runner as any).toAnthropicMessageContent(part);
      },
      (error: Error) => {
        return (
          error.message.includes('Text files should be sent as text content') &&
          error.message.includes('text:')
        );
      }
    );
  });

  it('should throw helpful error for text/plain in tool response', () => {
    const runner = createRunner();
    const part: Part = {
      toolResponse: {
        ref: 'call_123',
        name: 'get_file',
        output: {
          url: 'data:text/plain;base64,AAA',
          contentType: 'text/plain',
        },
      },
    };

    assert.throws(
      () => {
        (runner as any).toAnthropicToolResponseContent(part);
      },
      (error: Error) => {
        return error.message.includes(
          'Text files should be sent as text content'
        );
      }
    );
  });
});
/**
 * Copyright 2025 Google LLC
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

import { Anthropic } from '@anthropic-ai/sdk';
import { mock } from 'node:test';

describe('BetaRunner', () => {
  it('should map all supported Part shapes to beta content blocks', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });

    const exposed = runner as any;

    const textPart = exposed.toAnthropicMessageContent({
      text: 'Hello',
    } as any);
    assert.deepStrictEqual(textPart, { type: 'text', text: 'Hello' });

    const pdfPart = exposed.toAnthropicMessageContent({
      media: {
        url: 'data:application/pdf;base64,JVBERi0xLjQKJ',
        contentType: 'application/pdf',
      },
    } as any);
    assert.strictEqual(pdfPart.type, 'document');

    const imagePart = exposed.toAnthropicMessageContent({
      media: {
        url: 'data:image/png;base64,AAA',
        contentType: 'image/png',
      },
    } as any);
    assert.strictEqual(imagePart.type, 'image');

    const toolUsePart = exposed.toAnthropicMessageContent({
      toolRequest: {
        ref: 'tool1',
        name: 'get_weather',
        input: { city: 'NYC' },
      },
    } as any);
    assert.deepStrictEqual(toolUsePart, {
      type: 'tool_use',
      id: 'tool1',
      name: 'get_weather',
      input: { city: 'NYC' },
    });

    const toolResultPart = exposed.toAnthropicMessageContent({
      toolResponse: {
        ref: 'tool1',
        name: 'get_weather',
        output: 'Sunny',
      },
    } as any);
    assert.strictEqual(toolResultPart.type, 'tool_result');

    assert.throws(() => exposed.toAnthropicMessageContent({} as any));
  });

  it('should convert beta stream events to Genkit Parts', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });

    const exposed = runner as any;
    const textPart = exposed.toGenkitPart({
      type: 'content_block_start',
      index: 0,
      content_block: { type: 'text', text: 'hi' },
    } as any);
    assert.deepStrictEqual(textPart, { text: 'hi' });

    const serverToolEvent = {
      type: 'content_block_start',
      index: 0,
      content_block: {
        type: 'server_tool_use',
        id: 'toolu_test',
        name: 'myTool',
        input: { foo: 'bar' },
        server_name: 'srv',
      },
    } as any;
    const toolPart = exposed.toGenkitPart(serverToolEvent);
    assert.deepStrictEqual(toolPart, {
      text: '[Anthropic server tool srv/myTool] input: {"foo":"bar"}',
      custom: {
        anthropicServerToolUse: {
          id: 'toolu_test',
          name: 'srv/myTool',
          input: { foo: 'bar' },
        },
      },
    });

    const deltaPart = exposed.toGenkitPart({
      type: 'content_block_delta',
      index: 0,
      delta: { type: 'thinking_delta', thinking: 'hmm' },
    } as any);
    assert.deepStrictEqual(deltaPart, { reasoning: 'hmm' });

    const ignored = exposed.toGenkitPart({ type: 'message_stop' } as any);
    assert.strictEqual(ignored, undefined);
  });

  it('should handle mcp_tool_use stream events', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });

    const exposed = runner as any;
    const part = exposed.toGenkitPart({
      type: 'content_block_start',
      index: 0,
      content_block: {
        type: 'mcp_tool_use',
        id: 'mcp_tool_123',
        name: 'search_files',
        server_name: 'filesystem',
        input: { query: 'test' },
      },
    });

    assert.ok(part.text.includes('MCP tool filesystem/search_files'));
    assert.ok(part.custom.anthropicMcpToolUse);
    assert.strictEqual(part.custom.anthropicMcpToolUse.id, 'mcp_tool_123');
    assert.strictEqual(part.custom.anthropicMcpToolUse.serverName, 'filesystem');
    assert.strictEqual(part.custom.anthropicMcpToolUse.toolName, 'search_files');
    assert.deepStrictEqual(part.custom.anthropicMcpToolUse.input, { query: 'test' });
  });

  it('should handle mcp_tool_result stream events', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });

    const exposed = runner as any;
    const part = exposed.toGenkitPart({
      type: 'content_block_start',
      index: 0,
      content_block: {
        type: 'mcp_tool_result',
        tool_use_id: 'mcp_tool_123',
        is_error: false,
        content: [{ type: 'text', text: 'Found 5 files' }],
      },
    });

    assert.ok(part.text.includes('mcp_tool_123'));
    assert.ok(part.custom.anthropicMcpToolResult);
    assert.strictEqual(part.custom.anthropicMcpToolResult.toolUseId, 'mcp_tool_123');
    assert.strictEqual(part.custom.anthropicMcpToolResult.isError, false);
  });

  it('should map beta stop reasons correctly', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });

    const finishReason = runner['fromBetaStopReason'](
      'model_context_window_exceeded'
    );
    assert.strictEqual(finishReason, 'length');

    const pauseReason = runner['fromBetaStopReason']('pause_turn');
    assert.strictEqual(pauseReason, 'stop');
  });

  it('should execute streaming calls and surface errors', async () => {
    const streamError = new Error('stream failed');
    const mockClient = createMockAnthropicClient({
      streamChunks: [
        {
          type: 'content_block_start',
          index: 0,
          content_block: { type: 'text', text: 'hi' },
        } as any,
      ],
      streamErrorAfterChunk: 1,
      streamError,
    });

    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });
    const sendChunk = mock.fn();
    await assert.rejects(async () =>
      runner.run({ messages: [] } as any, {
        streamingRequested: true,
        sendChunk,
        abortSignal: new AbortController().signal,
      })
    );
    assert.strictEqual(sendChunk.mock.calls.length, 1);

    const abortController = new AbortController();
    abortController.abort();
    await assert.rejects(async () =>
      runner.run({ messages: [] } as any, {
        streamingRequested: true,
        sendChunk: () => {},
        abortSignal: abortController.signal,
      })
    );
  });

  it('should throw when tool refs are missing in message content', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });
    const exposed = runner as any;

    assert.throws(() =>
      exposed.toAnthropicMessageContent({
        toolRequest: {
          name: 'get_weather',
          input: {},
        },
      } as any)
    );

    assert.throws(() =>
      exposed.toAnthropicMessageContent({
        toolResponse: {
          name: 'get_weather',
          output: 'ok',
        },
      } as any)
    );

    assert.throws(() =>
      exposed.toAnthropicMessageContent({
        media: {
          url: 'data:image/png;base64,',
          contentType: undefined,
        },
      } as any)
    );
  });

  it('should build request bodies with optional config fields', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-3-5-haiku',
      client: mockClient as Anthropic,
      cacheSystemPrompt: true,
    }) as any;

    const request = {
      messages: [
        {
          role: 'system',
          content: [{ text: 'You are helpful.' }],
        },
        {
          role: 'user',
          content: [{ text: 'Tell me a joke' }],
        },
      ],
      config: {
        maxOutputTokens: 128,
        topK: 4,
        topP: 0.65,
        temperature: 0.55,
        stopSequences: ['DONE'],
        metadata: { user_id: 'beta-user' },
        tool_choice: { type: 'tool', name: 'get_weather' },
        thinking: { enabled: true, budgetTokens: 2048 },
      },
      tools: [
        {
          name: 'get_weather',
          description: 'Returns the weather',
          inputSchema: { type: 'object' },
        },
      ],
    } satisfies any;

    const body = runner.toAnthropicRequestBody(
      'claude-3-5-haiku',
      request,
      true
    );

    assert.strictEqual(body.model, 'claude-3-5-haiku-20241022');
    assert.ok(Array.isArray(body.system));
    assert.strictEqual(body.max_tokens, 128);
    assert.strictEqual(body.top_k, 4);
    assert.strictEqual(body.top_p, 0.65);
    assert.strictEqual(body.temperature, 0.55);
    assert.deepStrictEqual(body.stop_sequences, ['DONE']);
    assert.deepStrictEqual(body.metadata, { user_id: 'beta-user' });
    assert.deepStrictEqual(body.tool_choice, {
      type: 'tool',
      name: 'get_weather',
    });
    assert.strictEqual(body.tools?.length, 1);
    assert.deepStrictEqual(body.thinking, {
      type: 'enabled',
      budget_tokens: 2048,
    });

    const streamingBody = runner.toAnthropicStreamingRequestBody(
      'claude-3-5-haiku',
      request,
      true
    );
    assert.strictEqual(streamingBody.stream, true);
    assert.ok(Array.isArray(streamingBody.system));
    assert.deepStrictEqual(streamingBody.thinking, {
      type: 'enabled',
      budget_tokens: 2048,
    });

    const disabledBody = runner.toAnthropicRequestBody(
      'claude-3-5-haiku',
      {
        messages: [],
        config: {
          thinking: { enabled: false },
        },
      } satisfies any,
      false
    );
    assert.deepStrictEqual(disabledBody.thinking, { type: 'disabled' });
  });

  it('should concatenate multiple text parts in system message', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-3-5-haiku',
      client: mockClient as Anthropic,
    }) as any;

    const request = {
      messages: [
        {
          role: 'system',
          content: [
            { text: 'You are a helpful assistant.' },
            { text: 'Always be concise.' },
            { text: 'Use proper grammar.' },
          ],
        },
        { role: 'user', content: [{ text: 'Hi' }] },
      ],
      output: { format: 'text' },
    } satisfies any;

    const body = runner.toAnthropicRequestBody(
      'claude-3-5-haiku',
      request,
      false
    );

    assert.strictEqual(
      body.system,
      'You are a helpful assistant.\n\nAlways be concise.\n\nUse proper grammar.'
    );
  });

  it('should concatenate multiple text parts in system message with caching', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-3-5-haiku',
      client: mockClient as Anthropic,
    }) as any;

    const request = {
      messages: [
        {
          role: 'system',
          content: [
            { text: 'You are a helpful assistant.' },
            { text: 'Always be concise.' },
          ],
        },
        { role: 'user', content: [{ text: 'Hi' }] },
      ],
      output: { format: 'text' },
    } satisfies any;

    const body = runner.toAnthropicRequestBody(
      'claude-3-5-haiku',
      request,
      true
    );

    assert.ok(Array.isArray(body.system));
    assert.deepStrictEqual(body.system, [
      {
        type: 'text',
        text: 'You are a helpful assistant.\n\nAlways be concise.',
        cache_control: { type: 'ephemeral' },
      },
    ]);
  });

  it('should throw error if system message contains media', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-3-5-haiku',
      client: mockClient as Anthropic,
    }) as any;

    const request = {
      messages: [
        {
          role: 'system',
          content: [
            { text: 'You are a helpful assistant.' },
            {
              media: {
                url: 'data:image/png;base64,iVBORw0KGgoAAAANS',
                contentType: 'image/png',
              },
            },
          ],
        },
        { role: 'user', content: [{ text: 'Hi' }] },
      ],
      output: { format: 'text' },
    } satisfies any;

    assert.throws(
      () => runner.toAnthropicRequestBody('claude-3-5-haiku', request, false),
      /System messages can only contain text content/
    );
  });

  it('should throw error if system message contains tool requests', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-3-5-haiku',
      client: mockClient as Anthropic,
    }) as any;

    const request = {
      messages: [
        {
          role: 'system',
          content: [
            { text: 'You are a helpful assistant.' },
            { toolRequest: { name: 'getTool', input: {}, ref: '123' } },
          ],
        },
        { role: 'user', content: [{ text: 'Hi' }] },
      ],
      output: { format: 'text' },
    } satisfies any;

    assert.throws(
      () => runner.toAnthropicRequestBody('claude-3-5-haiku', request, false),
      /System messages can only contain text content/
    );
  });

  it('should throw error if system message contains tool responses', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-3-5-haiku',
      client: mockClient as Anthropic,
    }) as any;

    const request = {
      messages: [
        {
          role: 'system',
          content: [
            { text: 'You are a helpful assistant.' },
            { toolResponse: { name: 'getTool', output: {}, ref: '123' } },
          ],
        },
        { role: 'user', content: [{ text: 'Hi' }] },
      ],
      output: { format: 'text' },
    } satisfies any;

    assert.throws(
      () => runner.toAnthropicRequestBody('claude-3-5-haiku', request, false),
      /System messages can only contain text content/
    );
  });

  it('should handle mcp_tool_use content blocks', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });
    const exposed = runner as any;

    const part = exposed.fromBetaContentBlock({
      type: 'mcp_tool_use',
      id: 'mcp_tool_456',
      name: 'read_file',
      server_name: 'fs-server',
      input: { path: '/tmp/test.txt' },
    });

    assert.ok(part.text.includes('MCP tool fs-server/read_file'));
    assert.ok(part.custom.anthropicMcpToolUse);
    assert.strictEqual(part.custom.anthropicMcpToolUse.id, 'mcp_tool_456');
    assert.strictEqual(part.custom.anthropicMcpToolUse.name, 'fs-server/read_file');
    assert.strictEqual(part.custom.anthropicMcpToolUse.serverName, 'fs-server');
    assert.strictEqual(part.custom.anthropicMcpToolUse.toolName, 'read_file');
    assert.deepStrictEqual(part.custom.anthropicMcpToolUse.input, { path: '/tmp/test.txt' });
  });

  it('should handle mcp_tool_result content blocks', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });
    const exposed = runner as any;

    const part = exposed.fromBetaContentBlock({
      type: 'mcp_tool_result',
      tool_use_id: 'mcp_tool_456',
      is_error: false,
      content: [{ type: 'text', text: 'file contents here' }],
    });

    assert.ok(part.text.includes('mcp_tool_456'));
    assert.ok(part.custom.anthropicMcpToolResult);
    assert.strictEqual(part.custom.anthropicMcpToolResult.toolUseId, 'mcp_tool_456');
    assert.strictEqual(part.custom.anthropicMcpToolResult.isError, false);
    assert.ok(Array.isArray(part.custom.anthropicMcpToolResult.content));
  });

  it('should handle mcp_tool_result with is_error true', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });
    const exposed = runner as any;

    const part = exposed.fromBetaContentBlock({
      type: 'mcp_tool_result',
      tool_use_id: 'mcp_tool_789',
      is_error: true,
      content: [{ type: 'text', text: 'Permission denied' }],
    });

    assert.strictEqual(part.custom.anthropicMcpToolResult.isError, true);
    // Verify the [ERROR] prefix is added to the text
    assert.ok(part.text.startsWith('[ERROR]'));
  });

  it('should handle mcp_tool_use with missing server_name', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });
    const exposed = runner as any;

    // Suppress warning for this test
    const warnMock = mock.method(console, 'warn', () => {});

    const part = exposed.fromBetaContentBlock({
      type: 'mcp_tool_use',
      id: 'mcp_tool_no_server',
      name: 'some_tool',
      input: { query: 'test' },
    });

    assert.strictEqual(part.custom.anthropicMcpToolUse.serverName, 'unknown_server');
    assert.ok(part.text.includes('unknown_server/some_tool'));
    // Should have logged a warning about missing server_name
    assert.strictEqual(warnMock.mock.calls.length, 1);
    warnMock.mock.restore();
  });

  it('should handle mcp_tool_use with missing name', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });
    const exposed = runner as any;

    // Suppress warning for this test
    const warnMock = mock.method(console, 'warn', () => {});

    const part = exposed.fromBetaContentBlock({
      type: 'mcp_tool_use',
      id: 'mcp_tool_no_name',
      server_name: 'my-server',
      input: { query: 'test' },
    });

    assert.strictEqual(part.custom.anthropicMcpToolUse.toolName, 'unknown_tool');
    assert.ok(part.text.includes('my-server/unknown_tool'));
    // Should have logged a warning about missing name
    assert.strictEqual(warnMock.mock.calls.length, 1);
    warnMock.mock.restore();
  });

  it('should handle mcp_tool_result with missing content', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });
    const exposed = runner as any;

    const part = exposed.fromBetaContentBlock({
      type: 'mcp_tool_result',
      tool_use_id: 'mcp_tool_no_content',
      is_error: false,
    });

    assert.strictEqual(part.custom.anthropicMcpToolResult.content, undefined);
    assert.ok(part.text.includes('mcp_tool_no_content'));
  });

  it('should include mcp_servers and mcp_toolsets in request body', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-3-5-haiku',
      client: mockClient as Anthropic,
    }) as any;

    const request = {
      messages: [{ role: 'user', content: [{ text: 'Hello' }] }],
      config: {
        mcp_servers: [
          {
            type: 'url',
            url: 'https://mcp.example.com/server',
            name: 'my-mcp-server',
            authorization_token: 'secret-token',
          },
        ],
        mcp_toolsets: [
          {
            type: 'mcp_toolset',
            mcp_server_name: 'my-mcp-server',
            default_config: { enabled: true },
          },
        ],
      },
    } satisfies any;

    const body = runner.toAnthropicRequestBody(
      'claude-3-5-haiku',
      request,
      false
    );

    assert.deepStrictEqual(body.mcp_servers, [
      {
        type: 'url',
        url: 'https://mcp.example.com/server',
        name: 'my-mcp-server',
        authorization_token: 'secret-token',
      },
    ]);
    assert.ok(body.tools?.some((t: any) => t.type === 'mcp_toolset'));
  });

  it('should merge mcp_toolsets with regular tools', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-3-5-haiku',
      client: mockClient as Anthropic,
    }) as any;

    const request = {
      messages: [{ role: 'user', content: [{ text: 'Hello' }] }],
      tools: [
        {
          name: 'get_weather',
          description: 'Get weather',
          inputSchema: { type: 'object' },
        },
      ],
      config: {
        mcp_toolsets: [
          {
            type: 'mcp_toolset',
            mcp_server_name: 'my-mcp-server',
          },
        ],
      },
    } satisfies any;

    const body = runner.toAnthropicRequestBody(
      'claude-3-5-haiku',
      request,
      false
    );

    // Should have both regular tool and MCP toolset
    assert.strictEqual(body.tools?.length, 2);
    assert.ok(body.tools?.some((t: any) => t.name === 'get_weather'));
    assert.ok(body.tools?.some((t: any) => t.type === 'mcp_toolset'));
  });

  it('should include mcp_servers and mcp_toolsets in streaming request body', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-3-5-haiku',
      client: mockClient as Anthropic,
    }) as any;

    const request = {
      messages: [{ role: 'user', content: [{ text: 'Hello' }] }],
      config: {
        mcp_servers: [
          {
            type: 'url',
            url: 'https://mcp.example.com/server',
            name: 'stream-mcp-server',
          },
        ],
        mcp_toolsets: [
          {
            type: 'mcp_toolset',
            mcp_server_name: 'stream-mcp-server',
            default_config: { enabled: true },
          },
        ],
      },
    } satisfies any;

    const body = runner.toAnthropicStreamingRequestBody(
      'claude-3-5-haiku',
      request,
      false
    );

    assert.strictEqual(body.stream, true);
    assert.deepStrictEqual(body.mcp_servers, [
      {
        type: 'url',
        url: 'https://mcp.example.com/server',
        name: 'stream-mcp-server',
      },
    ]);
    assert.ok(body.tools?.some((t: any) => t.type === 'mcp_toolset'));
  });

  it('should include mcp_servers without mcp_toolsets', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-3-5-haiku',
      client: mockClient as Anthropic,
    }) as any;

    const request = {
      messages: [{ role: 'user', content: [{ text: 'Hello' }] }],
      config: {
        mcp_servers: [
          {
            type: 'url',
            url: 'https://mcp.example.com/server',
            name: 'server-only',
          },
        ],
        // No mcp_toolsets
      },
    } satisfies any;

    const body = runner.toAnthropicRequestBody(
      'claude-3-5-haiku',
      request,
      false
    );

    assert.deepStrictEqual(body.mcp_servers, [
      {
        type: 'url',
        url: 'https://mcp.example.com/server',
        name: 'server-only',
      },
    ]);
    // tools should be undefined when no tools or toolsets
    assert.strictEqual(body.tools, undefined);
  });

  it('should include mcp_toolsets without regular tools', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-3-5-haiku',
      client: mockClient as Anthropic,
    }) as any;

    const request = {
      messages: [{ role: 'user', content: [{ text: 'Hello' }] }],
      // No tools array
      config: {
        mcp_toolsets: [
          {
            type: 'mcp_toolset',
            mcp_server_name: 'toolset-only-server',
          },
        ],
      },
    } satisfies any;

    const body = runner.toAnthropicRequestBody(
      'claude-3-5-haiku',
      request,
      false
    );

    // Should have only MCP toolset
    assert.strictEqual(body.tools?.length, 1);
    assert.ok(body.tools?.some((t: any) => t.type === 'mcp_toolset'));
  });

  it('should convert additional beta content block types', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });

    const thinkingPart = (runner as any).fromBetaContentBlock({
      type: 'thinking',
      thinking: 'pondering',
      signature: 'sig_456',
    });
    assert.deepStrictEqual(thinkingPart, {
      reasoning: 'pondering',
      custom: { anthropicThinking: { signature: 'sig_456' } },
    });

    const redactedPart = (runner as any).fromBetaContentBlock({
      type: 'redacted_thinking',
      data: '[redacted]',
    });
    assert.deepStrictEqual(redactedPart, {
      custom: { redactedThinking: '[redacted]' },
    });

    const toolPart = (runner as any).fromBetaContentBlock({
      type: 'tool_use',
      id: 'toolu_x',
      name: 'plainTool',
      input: { value: 1 },
    });
    assert.deepStrictEqual(toolPart, {
      toolRequest: {
        ref: 'toolu_x',
        name: 'plainTool',
        input: { value: 1 },
      },
    });

    const serverToolPart = (runner as any).fromBetaContentBlock({
      type: 'server_tool_use',
      id: 'srv_tool_1',
      name: 'serverTool',
      input: { arg: 'value' },
      server_name: 'srv',
    });
    assert.deepStrictEqual(serverToolPart, {
      text: '[Anthropic server tool srv/serverTool] input: {"arg":"value"}',
      custom: {
        anthropicServerToolUse: {
          id: 'srv_tool_1',
          name: 'srv/serverTool',
          input: { arg: 'value' },
        },
      },
    });

    const warnMock = mock.method(console, 'warn', () => {});
    const fallbackPart = (runner as any).fromBetaContentBlock({
      type: 'mystery',
    });
    assert.deepStrictEqual(fallbackPart, { text: '' });
    assert.strictEqual(warnMock.mock.calls.length, 1);
    warnMock.mock.restore();
  });

  it('should map additional stop reasons', () => {
    const mockClient = createMockAnthropicClient();
    const runner = new BetaRunner({
      name: 'claude-test',
      client: mockClient as Anthropic,
    });
    const exposed = runner as any;

    const refusal = exposed.fromBetaStopReason('refusal');
    assert.strictEqual(refusal, 'other');

    const unknown = exposed.fromBetaStopReason('something-new');
    assert.strictEqual(unknown, 'other');

    const nullReason = exposed.fromBetaStopReason(null);
    assert.strictEqual(nullReason, 'unknown');
  });
});
