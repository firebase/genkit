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

import type { StdioServerParameters } from '@modelcontextprotocol/sdk/client/stdio.js' with { 'resolution-mode': 'import' };
import type { Transport } from '@modelcontextprotocol/sdk/shared/transport.js' with { 'resolution-mode': 'import' };
import { Genkit } from 'genkit';
import { genkitPlugin } from 'genkit/plugin';
import { GenkitMcpClient } from './client';
import { GenkitMcpServer } from './server';

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
  /** Connect to a remote server process using the WebSocket MCP transport. */
  serverWebsocketUrl?: string | URL;
  /** Return tool responses in raw MCP form instead of processing them for Genkit compatibility. */
  rawToolResponses?: boolean;
  /** Specify the MCP roots this client would like the server to work within. */
  roots?: { name: string; uri: string }[];
}

const mcpClients: Record<string, GenkitMcpClient> = {};

export function mcpClient(params: McpClientOptions) {
  return genkitPlugin(params.name, async (ai: Genkit) => {
    mcpClients[params.name] = new GenkitMcpClient(ai, {
      name: params.name,
      version: params.version || '1.0.0',
      roots: params.roots,
    });
  });
}

export function setMcpClientRoots(
  name: string,
  roots: { name: string; uri: string }[]
) {
  if (!mcpClients[name]) {
    throw new Error(`MCP client plugin ${name} doesn't exist.`);
  }
  mcpClients[name].roots = roots;
}

export interface McpServerOptions {
  /** The name you want to give your server for MCP inspection. */
  name: string;
  /** The version you want the server to advertise to clients. Defaults to 1.0.0. */
  version?: string;
  /** The MCP roots this server is associated with or serves. */
  roots?: { name: string; uri: string }[];
}

export function mcpServer(ai: Genkit, options: McpServerOptions) {
  return new GenkitMcpServer(ai, options);
}
