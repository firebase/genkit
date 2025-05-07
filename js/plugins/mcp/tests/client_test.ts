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
import type { StdioServerParameters } from '@modelcontextprotocol/sdk/client/stdio.js';
import type { Transport } from '@modelcontextprotocol/sdk/shared/transport.js';
import type { Genkit } from 'genkit';
import { McpClientOptions, mcpClient } from '../src/index';

type MockedFunction<T extends (...args: any) => any> = jest.MockedFunction<T>;
type MockedGenkitPluginSignature = (
  name: string,
  onInit: (ai: Genkit) => Promise<void>
) => { name: string };

const mockSSEClientTransport = jest.fn();
const mockStdioClientTransport = jest.fn();
const mockWebSocketClientTransport = jest.fn();

type McpServerCapabilities = {
  tools?: boolean;
  prompts?: boolean;
  resources?: boolean;
  roots?: { listChanged: boolean };
};

const mockMcpClientInstance = {
  connect: jest
    .fn<(transport: Transport) => Promise<void>>()
    .mockResolvedValue(undefined),
  getServerCapabilities: jest
    .fn<() => McpServerCapabilities | undefined>()
    .mockReturnValue({
      tools: true,
      prompts: true,
      resources: true,
    }),
};
const MockMcpClient = jest.fn(() => mockMcpClientInstance);

type RegistrationFunction = (
  ai: Genkit,
  client: typeof mockMcpClientInstance,
  params: McpClientOptions
) => Promise<void>;

const mockGenkitInstance = {
  options: {},
} as Genkit;

jest.mock('@modelcontextprotocol/sdk/client/sse.js', () => ({
  SSEClientTransport: mockSSEClientTransport,
}));
jest.mock('@modelcontextprotocol/sdk/client/stdio.js', () => ({
  StdioClientTransport: mockStdioClientTransport,
}));
jest.mock('@modelcontextprotocol/sdk/client/websocket.js', () => ({
  WebSocketClientTransport: mockWebSocketClientTransport,
}));
jest.mock('@modelcontextprotocol/sdk/client/index.js', () => ({
  Client: MockMcpClient,
}));

jest.mock('genkit/plugin', () => {
  return {
    genkitPlugin: jest.fn<MockedGenkitPluginSignature>(),
  };
});

jest.mock('genkit', () => {
  class MockGenkitError extends Error {
    constructor(public details: { status?: string; message: string }) {
      super(details.message);
      this.name = 'GenkitError';
      if (details.status) {
        (this as any).status = details.status;
      }
    }
  }

  const originalGenkitModule =
    jest.requireActual<typeof import('genkit')>('genkit');
  return {
    __esModule: true,
    ...originalGenkitModule,
    GenkitError: MockGenkitError,
  };
});

jest.mock('../src/client/tools.ts', () => ({
  registerAllTools: jest.fn<RegistrationFunction>(),
}));
jest.mock('../src/client/prompts.ts', () => ({
  registerAllPrompts: jest.fn<RegistrationFunction>(),
}));
jest.mock('../src/client/resources.ts', () => ({
  registerResourceTools: jest.fn<RegistrationFunction>(),
}));

const getMockedGenkitErrorConstructor = () => {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const genkitModule = require('genkit');
  return genkitModule.GenkitError as unknown as new (details: {
    status?: string;
    message: string;
  }) => Error & { details: { status?: string; message: string } };
};

describe('mcpClient', () => {
  let pluginSetupFunction: (ai: Genkit) => Promise<void>;

  let localMockRegisterAllTools: MockedFunction<RegistrationFunction>;
  let localMockRegisterAllPrompts: MockedFunction<RegistrationFunction>;
  let localMockRegisterResourceTools: MockedFunction<RegistrationFunction>;

  let localMockGenkitPlugin: MockedFunction<MockedGenkitPluginSignature>;

  beforeEach(() => {
    jest.clearAllMocks();

    const mockedPluginModule = jest.requireMock('genkit/plugin') as {
      genkitPlugin: MockedFunction<MockedGenkitPluginSignature>;
    };
    localMockGenkitPlugin = mockedPluginModule.genkitPlugin;

    const mockedToolsModule = jest.requireMock('../src/client/tools.ts') as {
      registerAllTools: MockedFunction<RegistrationFunction>;
    };
    localMockRegisterAllTools = mockedToolsModule.registerAllTools;

    const mockedPromptsModule = jest.requireMock(
      '../src/client/prompts.ts'
    ) as {
      registerAllPrompts: MockedFunction<RegistrationFunction>;
    };
    localMockRegisterAllPrompts = mockedPromptsModule.registerAllPrompts;

    const mockedResourcesModule = jest.requireMock(
      '../src/client/resources.ts'
    ) as {
      registerResourceTools: MockedFunction<RegistrationFunction>;
    };
    localMockRegisterResourceTools =
      mockedResourcesModule.registerResourceTools;

    localMockGenkitPlugin.mockImplementation((name, func) => {
      pluginSetupFunction = func;
      return { name: `plugin-${name}` };
    });

    mockMcpClientInstance.connect.mockResolvedValue(undefined);
    MockMcpClient.mockClear().mockReturnValue(mockMcpClientInstance);
    mockSSEClientTransport.mockClear();
    mockStdioClientTransport.mockClear();
    mockWebSocketClientTransport.mockClear();

    mockMcpClientInstance.getServerCapabilities.mockReturnValue({
      tools: true,
      prompts: true,
      resources: true,
      roots: { listChanged: false },
    });

    localMockRegisterAllTools.mockClear().mockResolvedValue(undefined);
    localMockRegisterAllPrompts.mockClear().mockResolvedValue(undefined);
    localMockRegisterResourceTools.mockClear().mockResolvedValue(undefined);
  });

  it('should initialize with SSE transport and register all capabilities by default', async () => {
    const options: McpClientOptions = {
      name: 'test-sse-client',
      serverUrl: 'http://localhost:1234/sse',
    };
    mcpClient(options);
    const capabilitiesToReturn = {
      tools: true,
      prompts: true,
      resources: true,
      roots: { listChanged: false },
    };
    mockMcpClientInstance.getServerCapabilities.mockReturnValue(
      capabilitiesToReturn
    );

    await pluginSetupFunction(mockGenkitInstance);

    expect(MockMcpClient).toHaveBeenCalledTimes(1);
    expect(MockMcpClient).toHaveBeenCalledWith(expect.any(Object), {
      capabilities: {
        roots: { listChanged: false },
      },
    });
    expect(mockMcpClientInstance.connect).toHaveBeenCalled();
    expect(mockMcpClientInstance.getServerCapabilities).toHaveBeenCalled();
    expect(localMockRegisterAllTools).toHaveBeenCalledWith(
      mockGenkitInstance,
      mockMcpClientInstance,
      options
    );
    expect(localMockRegisterAllPrompts).toHaveBeenCalledWith(
      mockGenkitInstance,
      mockMcpClientInstance,
      options
    );
    expect(localMockRegisterResourceTools).toHaveBeenCalledWith(
      mockGenkitInstance,
      mockMcpClientInstance,
      options
    );
  });

  it('should initialize with Stdio transport', async () => {
    const serverProcessParams: StdioServerParameters = {
      command: 'my-server-cmd',
    };
    const options: McpClientOptions = {
      name: 'test-stdio-client',
      serverProcess: serverProcessParams,
    };

    mcpClient(options);
    await pluginSetupFunction(mockGenkitInstance);

    expect(mockStdioClientTransport).toHaveBeenCalledWith(serverProcessParams);
    expect(mockMcpClientInstance.connect).toHaveBeenCalledWith(
      expect.any(mockStdioClientTransport)
    );
  });

  it('should initialize with WebSocket transport (string URL)', async () => {
    const options: McpClientOptions = {
      name: 'test-ws-client-string',
      serverWebsocketUrl: 'ws://localhost:5678',
    };

    mcpClient(options);
    await pluginSetupFunction(mockGenkitInstance);

    expect(mockWebSocketClientTransport).toHaveBeenCalledWith(
      new URL(options.serverWebsocketUrl as string)
    );
    expect(mockMcpClientInstance.connect).toHaveBeenCalledWith(
      expect.any(mockWebSocketClientTransport)
    );
  });

  it('should initialize with WebSocket transport (URL object)', async () => {
    const url = new URL('wss://secure.example.com:8080');
    const options: McpClientOptions = {
      name: 'test-ws-client-url',
      serverWebsocketUrl: url,
    };

    mcpClient(options);
    await pluginSetupFunction(mockGenkitInstance);

    expect(mockWebSocketClientTransport).toHaveBeenCalledWith(url);
    expect(mockMcpClientInstance.connect).toHaveBeenCalledWith(
      expect.any(mockWebSocketClientTransport)
    );
  });

  it('should initialize with an existing transport', async () => {
    const mockTransportInstance = {} as Transport;
    const options: McpClientOptions = {
      name: 'test-existing-transport-client',
      transport: mockTransportInstance,
    };

    mcpClient(options);
    await pluginSetupFunction(mockGenkitInstance);

    expect(mockMcpClientInstance.connect).toHaveBeenCalledWith(
      mockTransportInstance
    );
    expect(mockSSEClientTransport).not.toHaveBeenCalled();
    expect(mockStdioClientTransport).not.toHaveBeenCalled();
    expect(mockWebSocketClientTransport).not.toHaveBeenCalled();
  });

  it('should throw GenkitError if no valid transport options are provided', async () => {
    const options: McpClientOptions = {
      name: 'test-error-client',
    };

    mcpClient(options);
    const MockedError = getMockedGenkitErrorConstructor();

    await expect(pluginSetupFunction(mockGenkitInstance)).rejects.toThrow(
      MockedError
    );
    try {
      await pluginSetupFunction(mockGenkitInstance);
    } catch (e: any) {
      expect(e.details.status).toBe('INVALID_ARGUMENT');
      expect(e.message).toBe(
        'Unable to create a server connection with supplied options. Must provide transport, stdio, or sseUrl.'
      );
    }

    expect(mockSSEClientTransport).not.toHaveBeenCalled();
    expect(mockStdioClientTransport).not.toHaveBeenCalled();
    expect(mockWebSocketClientTransport).not.toHaveBeenCalled();
  });

  it('should use provided version, roots, and pass options to registration functions', async () => {
    const options: McpClientOptions = {
      name: 'test-options-client',
      serverUrl: 'http://localhost:1234/sse',
      version: '2.0.0-beta',
      roots: [{ name: 'root1', uri: 'file:///project1' }],
      rawToolResponses: true,
    };

    mcpClient(options);
    await pluginSetupFunction(mockGenkitInstance);

    expect(MockMcpClient).toHaveBeenCalledWith(
      {
        name: options.name,
        version: options.version,
        roots: options.roots,
      },
      { capabilities: { roots: { listChanged: false } } }
    );
    expect(localMockRegisterAllTools).toHaveBeenCalledWith(
      mockGenkitInstance,
      mockMcpClientInstance,
      options
    );
    expect(localMockRegisterAllPrompts).toHaveBeenCalledWith(
      mockGenkitInstance,
      mockMcpClientInstance,
      options
    );
    expect(localMockRegisterResourceTools).toHaveBeenCalledWith(
      mockGenkitInstance,
      mockMcpClientInstance,
      options
    );
  });

  describe('capability-based registration', () => {
    const baseOptions: McpClientOptions = {
      name: 'test-caps-client',
      serverUrl: 'http://localhost:9000/sse',
    };

    it('should only register tools if only tools capability is present', async () => {
      mockMcpClientInstance.getServerCapabilities.mockReturnValue({
        tools: true,
        prompts: false,
        resources: false,
      });
      mcpClient(baseOptions);
      await pluginSetupFunction(mockGenkitInstance);

      expect(localMockRegisterAllTools).toHaveBeenCalledWith(
        mockGenkitInstance,
        mockMcpClientInstance,
        baseOptions
      );
      expect(localMockRegisterAllPrompts).not.toHaveBeenCalled();
      expect(localMockRegisterResourceTools).not.toHaveBeenCalled();
    });

    it('should only register prompts if only prompts capability is present', async () => {
      mockMcpClientInstance.getServerCapabilities.mockReturnValue({
        tools: false,
        prompts: true,
        resources: false,
      });
      mcpClient(baseOptions);
      await pluginSetupFunction(mockGenkitInstance);

      expect(localMockRegisterAllTools).not.toHaveBeenCalled();
      expect(localMockRegisterAllPrompts).toHaveBeenCalledWith(
        mockGenkitInstance,
        mockMcpClientInstance,
        baseOptions
      );
      expect(localMockRegisterResourceTools).not.toHaveBeenCalled();
    });

    it('should only register resource tools if only resources capability is present', async () => {
      mockMcpClientInstance.getServerCapabilities.mockReturnValue({
        tools: false,
        prompts: false,
        resources: true,
      });
      mcpClient(baseOptions);
      await pluginSetupFunction(mockGenkitInstance);

      expect(localMockRegisterAllTools).not.toHaveBeenCalled();
      expect(localMockRegisterAllPrompts).not.toHaveBeenCalled();
      expect(localMockRegisterResourceTools).toHaveBeenCalledWith(
        mockGenkitInstance,
        mockMcpClientInstance,
        baseOptions
      );
    });

    it('should register nothing if no capabilities are present (all false)', async () => {
      mockMcpClientInstance.getServerCapabilities.mockReturnValue({
        tools: false,
        prompts: false,
        resources: false,
      });
      mcpClient(baseOptions);
      await pluginSetupFunction(mockGenkitInstance);

      expect(localMockRegisterAllTools).not.toHaveBeenCalled();
      expect(localMockRegisterAllPrompts).not.toHaveBeenCalled();
      expect(localMockRegisterResourceTools).not.toHaveBeenCalled();
    });

    it('should register nothing if capabilities object is undefined', async () => {
      (
        mockMcpClientInstance.getServerCapabilities as MockedFunction<any>
      ).mockResolvedValue(undefined);
      mcpClient(baseOptions);
      await pluginSetupFunction(mockGenkitInstance);

      expect(localMockRegisterAllTools).not.toHaveBeenCalled();
      expect(localMockRegisterAllPrompts).not.toHaveBeenCalled();
      expect(localMockRegisterResourceTools).not.toHaveBeenCalled();
    });

    it('should register tools and prompts if those capabilities are present', async () => {
      mockMcpClientInstance.getServerCapabilities.mockReturnValue({
        tools: true,
        prompts: true,
        resources: false,
      });
      mcpClient(baseOptions);
      await pluginSetupFunction(mockGenkitInstance);

      expect(localMockRegisterAllTools).toHaveBeenCalledWith(
        mockGenkitInstance,
        mockMcpClientInstance,
        baseOptions
      );
      expect(localMockRegisterAllPrompts).toHaveBeenCalledWith(
        mockGenkitInstance,
        mockMcpClientInstance,
        baseOptions
      );
      expect(localMockRegisterResourceTools).not.toHaveBeenCalled();
    });
  });
});
