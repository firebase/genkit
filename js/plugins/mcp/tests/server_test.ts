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

import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import {
  Genkit,
  GenkitError,
  MessageData,
  PromptAction,
  ToolAction,
} from 'genkit';
import type { McpServerOptions } from '../src/index';
import { GenkitMcpServer } from '../src/server';

const mockToJsonSchema = jest.fn();
const mockToToolDefinition = jest.fn();
const mockLoggerInfo = jest.fn();
const mockListActions =
  jest.fn<() => Promise<Record<string, ToolAction | PromptAction>>>();

const mockMcpServerInstance = {
  setRequestHandler: jest.fn(),
  connect: jest.fn<() => Promise<void>>().mockResolvedValue(undefined),
};
const MockMcpServer = jest.fn(() => mockMcpServerInstance);
const mockStdioServerTransportInstance = {};
const MockStdioServerTransport = jest.fn(
  () => mockStdioServerTransportInstance
);

jest.mock('@modelcontextprotocol/sdk/server/index.js', () => ({
  Server: MockMcpServer,
}));

jest.mock('@modelcontextprotocol/sdk/types.js', () => ({
  CallToolRequestSchema: { _id: 'CallToolRequestSchema' },
  GetPromptRequestSchema: { _id: 'GetPromptRequestSchema' },
  ListPromptsRequestSchema: { _id: 'ListPromptsRequestSchema' },
  ListToolsRequestSchema: { _id: 'ListToolsRequestSchema' },
  ListRootsRequestSchema: { _id: 'ListRootsRequestSchema' },
}));

jest.mock('@modelcontextprotocol/sdk/server/stdio.js', () => ({
  StdioServerTransport: MockStdioServerTransport,
}));

jest.mock('@genkit-ai/core/schema', () => ({
  get toJsonSchema() {
    return mockToJsonSchema;
  },
}));

jest.mock('genkit/tool', () => ({
  get toToolDefinition() {
    return mockToToolDefinition;
  },
}));

jest.mock('genkit/logging', () => ({
  logger: {
    get info() {
      return mockLoggerInfo;
    },
  },
}));

interface MockGenkitInstance {
  registry: {
    listActions: typeof mockListActions;
  };
}

const createMockGenkit = (): MockGenkitInstance => ({
  registry: { listActions: mockListActions },
});

const createMockGenkitAction = (
  type: 'tool' | 'prompt',
  name: string,
  inputSchema?: any,
  description?: string,
  metadata?: Record<string, any>
): { [key: string]: ToolAction | PromptAction } => {
  const actionFunction = jest.fn() as unknown as ToolAction | PromptAction;
  (actionFunction as any).__action = {
    name,
    inputSchema,

    inputJsonSchema: inputSchema
      ? { type: 'object', properties: {} }
      : undefined,
    description,
    ...metadata,
  };
  return { [`/${type}/${name}`]: actionFunction };
};

const createDefaultOptions = (
  overrides: Partial<McpServerOptions> = {}
): McpServerOptions => ({
  name: 'test-mcp-server',
  version: '1.0.0-test',
  ...overrides,
});

describe('GenkitMcpServer', () => {
  let mockGenkit: MockGenkitInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    mockGenkit = createMockGenkit();
    mockToToolDefinition.mockReturnValue({
      name: 'defaultMockedTool',
      inputSchema: { type: 'object' },
      description: 'Default mock',
    });
  });

  describe('constructor and setup', () => {
    it('should initialize MCP Server with options and capabilities', async () => {
      const options = createDefaultOptions({
        name: 'my-server',
        version: '2.0',
        roots: [{ name: 'root1', uri: 'genkit:/tool/t1' }],
      });
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        options
      );
      await server.setup();
      expect(MockMcpServer).toHaveBeenCalledWith(
        {
          name: 'my-server',
          version: '2.0',
          roots: [{ name: 'root1', uri: 'genkit:/tool/t1' }],
        },
        {
          capabilities: {
            prompts: {},
            tools: {},
            roots: { listChanged: false },
          },
        }
      );
    });

    it('should register request handlers for MCP SDK schemas', async () => {
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );
      await server.setup();

      expect(mockMcpServerInstance.setRequestHandler).toHaveBeenCalledTimes(5);
      const {
        ListToolsRequestSchema,
        CallToolRequestSchema,
        ListPromptsRequestSchema,
        GetPromptRequestSchema,
        ListRootsRequestSchema,
      } = await import('@modelcontextprotocol/sdk/types.js');

      expect(mockMcpServerInstance.setRequestHandler).toHaveBeenCalledWith(
        ListToolsRequestSchema,
        expect.any(Function)
      );
      expect(mockMcpServerInstance.setRequestHandler).toHaveBeenCalledWith(
        CallToolRequestSchema,
        expect.any(Function)
      );
      expect(mockMcpServerInstance.setRequestHandler).toHaveBeenCalledWith(
        ListPromptsRequestSchema,
        expect.any(Function)
      );
      expect(mockMcpServerInstance.setRequestHandler).toHaveBeenCalledWith(
        GetPromptRequestSchema,
        expect.any(Function)
      );
      expect(mockMcpServerInstance.setRequestHandler).toHaveBeenCalledWith(
        ListRootsRequestSchema,
        expect.any(Function)
      );
    });

    it('should fetch and categorize actions from Genkit registry', async () => {
      const toolAction1 = createMockGenkitAction('tool', 'tool1');
      const promptAction1 = createMockGenkitAction('prompt', 'prompt1');
      const otherAction = {
        '/other/action': jest.fn() as unknown as ToolAction,
      };
      mockListActions.mockResolvedValue({
        ...toolAction1,
        ...promptAction1,
        ...otherAction,
      });

      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );
      await server.setup();

      expect(mockListActions).toHaveBeenCalled();
      expect(server.toolActions).toEqual(
        expect.arrayContaining([Object.values(toolAction1)[0]])
      );
      expect(server.promptActions).toEqual(
        expect.arrayContaining([Object.values(promptAction1)[0]])
      );
    });

    it('should call setup only once even if methods are called multiple times', async () => {
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );
      await server.listTools({} as any);
      await server.listPrompts({} as any);
      expect(mockListActions).toHaveBeenCalledTimes(1);
      expect(MockMcpServer).toHaveBeenCalledTimes(1);
    });
  });

  describe('listTools', () => {
    it('should return tools based on registered tool actions', async () => {
      const toolAction = createMockGenkitAction(
        'tool',
        'toolA',
        { type: 'string' },
        'Tool A desc'
      );
      mockListActions.mockResolvedValue(toolAction);
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );
      const mockToolFn = Object.values(toolAction)[0];

      mockToToolDefinition.mockReturnValue({
        name: 'toolA',
        inputSchema: { type: 'string' },
        description: 'Tool A desc',
      });

      const result = await server.listTools({} as any);
      expect(mockToToolDefinition).toHaveBeenCalledWith(mockToolFn);
      expect(result.tools).toEqual([
        {
          name: 'toolA',
          inputSchema: { type: 'string' },
          description: 'Tool A desc',
        },
      ]);
    });

    it('should use default inputSchema if not defined', async () => {
      const toolAction = createMockGenkitAction(
        'tool',
        'toolB',
        undefined, // inputSchema
        'Tool B desc'
      );
      mockListActions.mockResolvedValue(toolAction);
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );

      mockToToolDefinition.mockReturnValue({
        name: 'toolB',
        // inputSchema is undefined here
        description: 'Tool B desc',
      });

      const result = await server.listTools({} as any);
      expect(result.tools[0].inputSchema).toEqual({ type: 'object' });
    });
  });

  describe('listRoots', () => {
    it('should return roots from options', async () => {
      const roots = [{ name: 'root1', uri: 'genkit:/tool/t1' }];
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions({ roots } as McpServerOptions)
      );
      await server.setup();
      const result = await server.listRoots({} as any);
      expect(result.roots).toEqual(roots);
    });

    it('should return empty array if no roots in options', async () => {
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions({ roots: undefined } as McpServerOptions)
      );
      await server.setup();

      const result = await server.listRoots({} as any);
      expect(result.roots).toEqual([]);
    });
  });

  describe('callTool', () => {
    it('should find and call the specified tool action', async () => {
      const toolAction = createMockGenkitAction('tool', 'myTool');
      const toolFn = Object.values(toolAction)[0] as jest.MockedFunction<any>;
      toolFn.mockResolvedValue('tool_result_data' as any);
      mockListActions.mockResolvedValue(toolAction);
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );

      const result = await server.callTool({
        params: { name: 'myTool', arguments: { arg1: 'val1' } },
      } as any);

      expect(toolFn).toHaveBeenCalledWith({ arg1: 'val1' });
      expect(result.content).toEqual([
        { type: 'text', text: JSON.stringify('tool_result_data') },
      ]);
    });

    it('should throw GenkitError if tool is not found', async () => {
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );
      mockListActions.mockResolvedValue({});
      await expect(
        server.callTool({ params: { name: 'nonExistentTool' } } as any)
      ).rejects.toThrow(
        new GenkitError({
          status: 'NOT_FOUND',
          message:
            "Tried to call tool 'nonExistentTool' but it could not be found.",
        })
      );
    });
  });

  describe('listPrompts', () => {
    it('should return prompts with arguments derived from inputSchema', async () => {
      const promptInputSchema = {
        properties: { query: { type: 'string', description: 'User query' } },
        required: ['query'],
      };
      const promptAction = createMockGenkitAction(
        'prompt',
        'myPrompt',
        promptInputSchema,
        'A prompt'
      );
      mockListActions.mockResolvedValue(promptAction);
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );
      const promptFn = Object.values(promptAction)[0];
      mockToJsonSchema.mockReturnValue({
        properties: { query: { type: 'string', description: 'User query' } },
        required: ['query'],
      });

      const result = await server.listPrompts({} as any);
      expect(mockToJsonSchema).toHaveBeenCalledWith({
        schema: (promptFn as any).__action.inputSchema,
        jsonSchema: (promptFn as any).__action.inputJsonSchema,
      });
      expect(result.prompts).toEqual([
        {
          name: 'myPrompt',
          description: 'A prompt',
          arguments: [
            { name: 'query', description: 'User query', required: true },
          ],
        },
      ]);
    });

    it('should throw if prompt inputSchema is not an object (no properties)', async () => {
      const promptAction = createMockGenkitAction('prompt', 'badPrompt', {
        type: 'string',
      });
      mockListActions.mockResolvedValue(promptAction);
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );

      mockToJsonSchema.mockReturnValue({ type: 'string' });
      await expect(server.listPrompts({} as any)).rejects.toThrow(
        new GenkitError({
          status: 'FAILED_PRECONDITION',
          message:
            '[@genkit-ai/mcp] MCP prompts must take objects as input schema.',
        })
      );
    });

    it('should throw if prompt argument is not a string', async () => {
      const promptAction = createMockGenkitAction(
        'prompt',
        'promptWithNonString',
        { properties: { numArg: { type: 'number' } } }
      );
      mockListActions.mockResolvedValue(promptAction);
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );

      mockToJsonSchema.mockReturnValue({
        properties: { numArg: { type: 'number', description: 'A number' } },
      });

      await expect(server.listPrompts({} as any)).rejects.toThrow(
        new GenkitError({
          status: 'FAILED_PRECONDITION',
          message: `[@genkit-ai/mcp] MCP prompts may only take string arguments, but promptWithNonString has property 'numArg' of type 'number'.`,
        })
      );
    });

    it('should handle undefined inputSchema for a prompt gracefully', async () => {
      const promptAction = createMockGenkitAction(
        'prompt',
        'noSchemaPrompt',
        undefined,
        'Prompt without schema'
      );
      mockListActions.mockResolvedValue(promptAction);
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );
      mockToJsonSchema.mockReturnValue(undefined); // Simulate no schema or unparsable

      const result = await server.listPrompts({} as any);
      expect(result.prompts[0].arguments).toBeUndefined();
    });
  });

  describe('getPrompt', () => {
    const createMessageData = (
      role: 'user' | 'model' | 'system' | 'tool',
      text?: string,
      mediaUrl?: string,
      mediaContentType?: string
    ): MessageData => ({
      role,
      content: [
        ...(text ? [{ text, custom: {} }] : []),
        ...(mediaUrl
          ? [
              {
                media: { url: mediaUrl, contentType: mediaContentType },
                custom: {},
              },
            ]
          : []),
      ].filter(Boolean) as MessageData['content'], // Filter out undefined if neither text nor media
    });

    it('should find, call prompt, and format messages (text only)', async () => {
      const promptAction = createMockGenkitAction(
        'prompt',
        'chatPrompt',
        undefined,
        'Chatty prompt'
      );
      const promptFn = Object.values(
        promptAction
      )[0] as jest.MockedFunction<any>;
      promptFn.mockResolvedValue(
        Promise.resolve({
          messages: [
            createMessageData('user', 'Hello'),
            createMessageData('model', 'Hi there'),
          ],
        } as any)
      );
      mockListActions.mockResolvedValue(promptAction);
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );

      const result = await server.getPrompt({
        params: { name: 'chatPrompt', arguments: { query: 'Hi' } },
      } as any);

      expect(promptFn).toHaveBeenCalledWith({ query: 'Hi' });
      expect(result.description).toBe('Chatty prompt');
      expect(result.messages).toEqual([
        { role: 'user', content: { type: 'text', text: 'Hello' } },
        { role: 'assistant', content: { type: 'text', text: 'Hi there' } },
      ]);
    });

    it('should format media messages (data URL)', async () => {
      const promptAction = createMockGenkitAction('prompt', 'imagePrompt');
      const promptFn = Object.values(
        promptAction
      )[0] as jest.MockedFunction<any>;
      promptFn.mockResolvedValue(
        Promise.resolve({
          messages: [
            createMessageData(
              'user',
              undefined,
              'data:image/png;base64,abc',
              'image/png'
            ),
          ],
        } as any)
      );
      mockListActions.mockResolvedValue(promptAction);
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );

      const result = await server.getPrompt({
        params: { name: 'imagePrompt' },
      } as any);
      expect(result.messages).toEqual([
        {
          role: 'user',
          content: { type: 'image', mimeType: 'image/png', data: 'abc' },
        },
      ]);
    });

    it('should throw GenkitError if prompt is not found', async () => {
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );
      mockListActions.mockResolvedValue({});
      await expect(
        server.getPrompt({ params: { name: 'ghostPrompt' } } as any)
      ).rejects.toThrow(
        new GenkitError({
          status: 'NOT_FOUND',
          message:
            "[@genkit-ai/mcp] Tried to call prompt 'ghostPrompt' but it could not be found.",
        })
      );
    });

    it('should throw if message role is unsupported', async () => {
      const promptAction = createMockGenkitAction('prompt', 'systemRolePrompt');
      const promptFn = Object.values(
        promptAction
      )[0] as jest.MockedFunction<any>;
      promptFn.mockResolvedValue(
        Promise.resolve({
          messages: [createMessageData('system', 'System message')],
        } as any)
      );

      mockListActions.mockResolvedValue(promptAction);
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );

      await expect(
        server.getPrompt({ params: { name: 'systemRolePrompt' } } as any)
      ).rejects.toThrow(
        new GenkitError({
          status: 'UNIMPLEMENTED',
          message:
            "[@genkit-ai/mcp] MCP prompt messages do not support role 'system'. Only 'user' and 'model' messages are supported.",
        })
      );
    });

    it('should throw if media URL is not a data URL', async () => {
      const promptAction = createMockGenkitAction('prompt', 'httpImagePrompt');
      const promptFn = Object.values(
        promptAction
      )[0] as jest.MockedFunction<any>;
      promptFn.mockResolvedValue(
        Promise.resolve({
          messages: [
            createMessageData(
              'user',
              undefined,
              'http://example.com/image.png'
            ),
          ],
        } as any)
      );

      mockListActions.mockResolvedValue(promptAction);
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );
      await expect(
        server.getPrompt({ params: { name: 'httpImagePrompt' } } as any)
      ).rejects.toThrow(
        new GenkitError({
          status: 'UNIMPLEMENTED',
          message:
            '[@genkit-ai/mcp] MCP prompt messages only support base64 data images.',
        })
      );
    });
  });

  describe('start', () => {
    it('should use StdioServerTransport by default if no transport is provided', async () => {
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );
      await server.start();

      expect(MockStdioServerTransport).toHaveBeenCalled();
      expect(mockMcpServerInstance.connect).toHaveBeenCalledWith(
        mockStdioServerTransportInstance
      );
      expect(mockLoggerInfo).toHaveBeenCalledWith(
        "[@genkit-ai/mcp] MCP server 'test-mcp-server' started successfully."
      );
    });

    it('should use provided transport', async () => {
      const customTransport = { custom: 'transport' };
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );
      await server.start(customTransport as any);

      expect(MockStdioServerTransport).not.toHaveBeenCalled();
      expect(mockMcpServerInstance.connect).toHaveBeenCalledWith(
        customTransport
      );
      expect(mockLoggerInfo).toHaveBeenCalledWith(
        "[@genkit-ai/mcp] MCP server 'test-mcp-server' started successfully."
      );
    });

    it('should call setup before connecting', async () => {
      const server = new GenkitMcpServer(
        mockGenkit as unknown as Genkit,
        createDefaultOptions()
      );
      // Spy on setup to ensure it's called by start
      const setupSpy = jest.spyOn(server, 'setup');
      await server.start();
      expect(setupSpy).toHaveBeenCalled();
    });
  });
});
