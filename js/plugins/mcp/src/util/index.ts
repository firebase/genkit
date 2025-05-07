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

import { McpServerConfig, McpServerControls } from '../client/client';
import type {
  SSEClientTransportOptions,
  StdioServerParameters,
  Transport,
} from '../client/index';

/**
 * Creates an MCP transport instance based on the provided server configuration.
 * It supports creating SSE, Stdio, or using a pre-configured custom transport.
 *
 * @param config The configuration for the MCP server, determining the type of transport to create.
 * @returns A Promise resolving to an object containing the created `Transport` instance
 *          (or `null` if configuration is invalid) and a string indicating the `type` of transport.
 * @throws May throw an error if essential MCP SDK components cannot be imported.
 */
export async function transportFrom(config: McpServerConfig): Promise<{
  transport: Transport | null;
  type: string;
}> {
  // Handle pre-configured transport first
  if ('transport' in config && config.transport) {
    return { transport: config.transport, type: 'custom' };
  }
  // Handle SSE config
  if ('url' in config && config.url) {
    const { url, ...sseConfig } = config;
    // Remove McpServerControls properties before passing to transport constructor
    delete (sseConfig as Partial<McpServerControls>).disabled;
    const { SSEClientTransport } = await import(
      '@modelcontextprotocol/sdk/client/sse.js'
    );
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
    const { StdioClientTransport } = await import(
      '@modelcontextprotocol/sdk/client/stdio.js'
    );
    return {
      transport: new StdioClientTransport(stdioConfig as StdioServerParameters),
      type: 'stdio',
    };
  }
  return { transport: null, type: 'unknown' };
}
