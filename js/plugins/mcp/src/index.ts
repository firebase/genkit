import type { StdioServerParameters } from '@modelcontextprotocol/sdk/client/stdio.js' with { 'resolution-mode': 'import' };
import type { Transport } from '@modelcontextprotocol/sdk/shared/transport.js' with { 'resolution-mode': 'import' };
import { Genkit, GenkitError } from 'genkit';
import { genkitPlugin } from 'genkit/plugin';
import { registerAllPrompts } from './client/prompts.js';
import { registerResourceTools } from './client/resources.js';
import { registerAllTools } from './client/tools.js';
import { GenkitMcpServer } from './server.js';

export interface McpClientOptions {
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
  /** Return tool responses in raw MCP form instead of processing them for Genkit compatibility. */
  rawToolResponses?: boolean;
}

async function transportFrom(params: McpClientOptions): Promise<Transport> {
  if (params.transport) return params.transport;
  if (params.serverUrl) {
    const { SSEClientTransport } = await import(
      '@modelcontextprotocol/sdk/client/sse.js'
    );
    return new SSEClientTransport(URL.parse(params.serverUrl)!);
  }
  if (params.serverProcess) {
    const { StdioClientTransport } = await import(
      '@modelcontextprotocol/sdk/client/stdio.js'
    );
    return new StdioClientTransport(params.serverProcess);
  }
  throw new GenkitError({
    status: 'INVALID_ARGUMENT',
    message:
      'Unable to create a server connection with supplied options. Must provide transport, stdio, or sseUrl.',
  });
}

export function mcpClient(params: McpClientOptions) {
  return genkitPlugin(params.name, async (ai: Genkit) => {
    const { Client } = await import(
      '@modelcontextprotocol/sdk/client/index.js'
    );

    const transport = await transportFrom(params);
    ai.options.model;
    const client = new Client(
      { name: params.name, version: params.version || '1.0.0' },
      { capabilities: {} }
    );
    await client.connect(transport);
    await Promise.all([
      registerAllTools(ai, client, params),
      registerAllPrompts(ai, client, params),
      registerResourceTools(ai, client, params),
    ]);
  });
}

export interface McpServerOptions {
  /** The name you want to give your server for MCP inspection. */
  name: string;
  /** The version you want the server to advertise to clients. Defaults to 1.0.0. */
  version?: string;
}

export function mcpServer(ai: Genkit, options: McpServerOptions) {
  return new GenkitMcpServer(ai, options);
}
