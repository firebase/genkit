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

import type { Genkit } from 'genkit';
import { GenkitMcpClientManager, McpClientManagerOptions } from './client';
import { McpClientOptions, McpServerConfig } from './client/client';
import { GenkitMcpServer } from './server';

export { mcpClient, type LegacyMcpClientOptions } from './client/legacy';
export {
  GenkitMcpClientManager as GenkitMcpClient,
  type McpClientOptions,
  type McpServerConfig,
};

export interface McpServerOptions {
  /** The name you want to give your server for MCP inspection. */
  name: string;
  /** The version you want the server to advertise to clients. Defaults to 1.0.0. */
  version?: string;
}

/**
 * Creates an MCP client that connects to one or more MCP servers as specified in
 * the `mcpServers` option. By default, all servers in the config will be automatically
 * started unless a `{disabled: true}` option is supplied.
 *
 * ```ts
 * const client = createMcpClient({
 *   name: "my-mcp-client",
 *   version: "0.1.0",
 *   mcpServers: {
 *     git: {command: "uvx", args: ["mcp-server-git"]},
 *   }
 * })
 * ```
 *
 * @param options
 * @returns
 */
export function createMcpClient(
  options: McpClientManagerOptions & {
    mcpClients: Record<string, McpServerConfig>;
  }
) {
  return new GenkitMcpClientManager(options);
}

/**
 * Creates an MCP server based on the supplied Genkit instance. All tools and prompts
 * will be automatically converted to MCP compatibility.
 *
 * ```ts
 * const mcpServer = createMcpServer(ai, {name: 'my-mcp-server', version: '0.1.0'});
 *
 * await mcpServer.start(); // starts a stdio transport, OR
 * await mcpServer.start(customMcpTransport); // starts server using supplied transport
 * ```
 *
 * @param ai Your Genkit instance with registered tools and prompts.
 * @param options Configuration metadata for the server.
 * @returns GenkitMcpServer instance.
 */
export function createMcpServer(
  ai: Genkit,
  options: McpServerOptions
): GenkitMcpServer {
  return new GenkitMcpServer(ai, options);
}

/**
 * @deprecated use `createMcpServer` instead.
 */
export function mcpServer(ai: Genkit, options: McpServerOptions) {
  return createMcpServer(ai, options);
}
