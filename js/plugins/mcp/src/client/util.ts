import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import type {
  McpServerConfig,
  McpServerControls,
  SSEClientTransportOptions,
  StdioServerParameters,
  Transport,
} from './index';

export function transportFrom(config: McpServerConfig): {
  transport: Transport | null;
  type: string;
} {
  // Handle pre-configured transport first
  if ('transport' in config && config.transport) {
    return { transport: config.transport, type: 'custom' };
  }
  // Handle SSE config
  if ('url' in config && config.url) {
    const { url, ...sseConfig } = config;
    // Remove McpServerControls properties before passing to transport constructor
    delete (sseConfig as Partial<McpServerControls>).disabled;
    return {
      transport: new SSEClientTransport(
        new URL(url),
        sseConfig as SSEClientTransportOptions
      ),
      type: 'sse',
    };
  }
  // Handle Stdio config
  if ('command' in config && config.command) {
    // Create a copy and remove McpServerControls properties
    const stdioConfig = { ...config };
    delete (stdioConfig as Partial<McpServerControls>).disabled;
    return {
      transport: new StdioClientTransport(stdioConfig as StdioServerParameters),
      type: 'stdio',
    };
  }
  return { transport: null, type: 'unknown' };
}
