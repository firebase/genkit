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

import type { Client } from '@modelcontextprotocol/sdk/client/index.js' with { 'resolution-mode': 'import' };
import type { Transport } from '@modelcontextprotocol/sdk/shared/transport.js' with { 'resolution-mode': 'import' };
import type {
  ListRootsRequest,
  ListRootsResult,
  Root,
  ServerCapabilities,
} from '@modelcontextprotocol/sdk/types.js' with { 'resolution-mode': 'import' };
import { ListRootsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { Genkit, GenkitError } from 'genkit';
import { registerAllPrompts } from './client/prompts';
import { registerResourceTools } from './client/resources';
import { registerAllTools } from './client/tools';
import type { McpClientOptions } from './index.js';

async function transportFrom(options: McpClientOptions): Promise<Transport> {
  if (options.transport) return options.transport;
  if (options.serverUrl) {
    const { SSEClientTransport } = await import(
      '@modelcontextprotocol/sdk/client/sse.js'
    );
    return new SSEClientTransport(new URL(options.serverUrl));
  }
  if (options.serverProcess) {
    const { StdioClientTransport } = await import(
      '@modelcontextprotocol/sdk/client/stdio.js'
    );
    return new StdioClientTransport(options.serverProcess);
  }
  if (options.serverWebsocketUrl) {
    const { WebSocketClientTransport } = await import(
      '@modelcontextprotocol/sdk/client/websocket.js'
    );
    let url = options.serverWebsocketUrl;
    if (typeof url === 'string') url = new URL(url);
    return new WebSocketClientTransport(url);
  }

  throw new GenkitError({
    status: 'INVALID_ARGUMENT',
    message: `Unable to create a server connection with supplied options. Must provide transport, stdio, or sseUrl:\n${JSON.stringify(
      options,
      null,
      2
    )}`,
  });
}

export class GenkitMcpClient {
  ai: Genkit;
  options: McpClientOptions;
  client?: Client;
  serverCapabilities?: ServerCapabilities | undefined = {};
  _isSetup: boolean = false;

  constructor(ai: Genkit, options: McpClientOptions) {
    this.ai = ai;
    this.options = options;
  }

  async setup(): Promise<void> {
    if (this._isSetup) return;
    const { Client } = await import(
      '@modelcontextprotocol/sdk/client/index.js'
    );

    const transport = await transportFrom(this.options);
    this.client = new Client(
      {
        name: this.options.name,
        version: this.options.version || '1.0.0',
        roots: this.options.roots,
      },
      {
        capabilities: {
          // TODO: Allow actually changing the roots dynamically. This requires
          // manipulating which tools, resources, etc. are registered, since
          // they can change based on the roots.
          roots: { listChanged: false },
        },
      }
    );

    this.client.setRequestHandler(
      ListRootsRequestSchema,
      this.listRoots.bind(this)
    );

    await this.client.connect(transport);
    this.serverCapabilities = this.client.getServerCapabilities();

    await this.registerCapabilities();
    this._isSetup = true;
  }

  async registerCapabilities(): Promise<void> {
    if (!this.client || !this.serverCapabilities) {
      return;
    }
    const promises: Promise<any>[] = [];
    if (this.serverCapabilities?.tools) {
      promises.push(registerAllTools(this.ai, this.client, this.options));
    }
    if (this.serverCapabilities?.prompts) {
      promises.push(registerAllPrompts(this.ai, this.client, this.options));
    }
    if (this.serverCapabilities?.resources) {
      promises.push(registerResourceTools(this.ai, this.client, this.options));
    }
    await Promise.all(promises);
  }

  async listRoots(req: ListRootsRequest): Promise<ListRootsResult> {
    if (!this.options.roots) {
      return { roots: [] };
    }
    const mcpRoots: Root[] = this.options.roots.map<Root>((root) => root);
    return { roots: mcpRoots };
  }
}
