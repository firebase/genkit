import { StdioServerParameters } from '@modelcontextprotocol/sdk/client/stdio.js';
import { Transport } from '@modelcontextprotocol/sdk/shared/transport.js';
import { Genkit, GenkitError } from 'genkit';
import { genkitPlugin } from 'genkit/plugin';
import { registerAllPrompts } from './prompts.js';
import { registerResourceTools } from './resources.js';
import { registerAllTools } from './tools.js';

export interface LegacyMcpClientOptions {
  /** Provide a name for this client which will be its namespace for all tools and prompts. */
  name: string;
  /** Provide a version number for this client (defaults to 1.0.0). */
  version?: string;
  /** If you already have an MCP transport you'd like to use, pass it here to connect to the server. */
  transport?: Transport;
  /** Start a local server process using the stdio MCP transport. */
  serverProcess?: StdioServerParameters;
  /** Connect to a remote server process using the SSE MCP transport. */
  serverUrl?: string;
  /** Connect to a remote server process using the WebSocket MCP transport. */
  serverWebsocketUrl?: string | URL;
  /** Return tool responses in raw MCP form instead of processing them for Genkit compatibility. */
  rawToolResponses?: boolean;
}

async function transportFrom(
  params: LegacyMcpClientOptions
): Promise<Transport> {
  if (params.transport) return params.transport;
  if (params.serverUrl) {
    const { SSEClientTransport } = await import(
      '@modelcontextprotocol/sdk/client/sse.js'
    );
    return new SSEClientTransport(new URL(params.serverUrl));
  }
  if (params.serverProcess) {
    const { StdioClientTransport } = await import(
      '@modelcontextprotocol/sdk/client/stdio.js'
    );
    return new StdioClientTransport(params.serverProcess);
  }
  if (params.serverWebsocketUrl) {
    const { WebSocketClientTransport } = await import(
      '@modelcontextprotocol/sdk/client/websocket.js'
    );
    let url = params.serverWebsocketUrl;
    if (typeof url === 'string') url = new URL(url);
    return new WebSocketClientTransport(url);
  }

  throw new GenkitError({
    status: 'INVALID_ARGUMENT',
    message:
      'Unable to create a server connection with supplied options. Must provide transport, stdio, or sseUrl.',
  });
}

/**
 * @deprecated use `createMcpClient({mcpServers: {...}})` instead.
 */
export function mcpClient(params: LegacyMcpClientOptions) {
  return genkitPlugin(params.name, async (ai: Genkit) => {
    const transport = await transportFrom(params);
    ai.options.model;
    const { Client } = await import(
      '@modelcontextprotocol/sdk/client/index.js'
    );
    const client = new Client({
      name: params.name,
      version: params.version || '1.0.0',
    });
    // Register empty capabilities, similar to the newer client/index.ts
    client.registerCapabilities({ roots: {} });
    await client.connect(transport);
    const capabilties = await client.getServerCapabilities();
    const promises: Promise<any>[] = [];
    if (capabilties?.tools)
      promises.push(
        registerAllTools(ai, client, {
          name: params.name,
          serverName: params.name,
          rawToolResponses: params.rawToolResponses,
        })
      );
    if (capabilties?.prompts)
      promises.push(
        registerAllPrompts(ai, client, {
          name: params.name,
          serverName: params.name,
        })
      );
    if (capabilties?.resources)
      promises.push(
        registerResourceTools(ai, client, {
          name: params.name,
          serverName: params.name,
        })
      );
    await Promise.all(promises);
  });
}
