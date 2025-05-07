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

import { SSEClientTransportOptions } from '@modelcontextprotocol/sdk/client/sse.js';
import { StdioServerParameters } from '@modelcontextprotocol/sdk/client/stdio.js';
import { Transport } from '@modelcontextprotocol/sdk/shared/transport.js';
import { Genkit, ToolAction } from 'genkit';
import { logger } from 'genkit/logging';
import { GenkitMcpClient, McpClientOptions } from './client';
export type { SSEClientTransportOptions, StdioServerParameters, Transport };

export interface McpClientManagerOptions {
  /** Provide a name for this client manager Defaults to 'mcp-manager'. */
  name?: string;
  /** Provide one or more MCP clients to manage connections. */
  mcpClients?: Record<string, McpClientOptions>;
}

export class GenkitMcpClientManager {
  name: string;
  private _clients: Record<string, GenkitMcpClient> = {};
  private _readyListeners: {
    resolve: () => void;
    reject: (err: Error) => void;
  }[] = [];
  private _ready = false;

  constructor(options: McpClientManagerOptions) {
    this.name = options.name || 'genkitx-mcp';

    if (options.mcpClients) this.updateClients(options.mcpClients);
  }

  /**
   * Returns a Promise that resolves when the manager has attempted to connect
   * to all configured clients, or rejects if a critical error occurs during
   * the initial connection phase.
   */
  async ready() {
    if (this._ready) return;
    return new Promise<void>((resolve, reject) => {
      this._readyListeners.push({ resolve, reject });
    });
  }

  /**
   * Connects to a single MCP server defined by the provided configuration.
   * If a server with the same name already exists, it will be disconnected first.
   * Stores the client and transport references internally. Handles connection errors
   * by marking the server as disabled.
   * @param serverName The name to assign to this server connection.
   * @param config The configuration object for the server.
   */
  async connectClient(serverName: string, config: McpClientOptions) {
    const existingEntry = this._clients[serverName];
    if (existingEntry) {
      await existingEntry.disconnect();
    }

    const client = new GenkitMcpClient(config);
    this._clients[serverName] = client;
  }

  /**
   * Disconnects the specified MCP server and removes its registration
   * from this client instance.
   * @param serverName The name of the server to disconnect.
   */
  async disconnectClient(serverName: string) {
    const client = this._clients[serverName];
    logger.info(
      `[MCP Manager] Disconnecting MCP server '${serverName}' in client '${this.name}'.`
    );
    await client.disconnect();
    delete this._clients[serverName];
  }

  /**
   * Temporarily disables a server connection. Closes the underlying transport
   * but retains the server's configuration. Does nothing if the server is
   * already disabled.
   * @param serverName The name of the server to disable.
   */
  async disableClient(serverName: string) {
    const client = this._clients[serverName];
    if (!client.isDisabled()) {
      logger.info(
        `[MCP Manager] Disabling MCP server '${serverName}' in client '${this.name}'`
      );
      await client.disable();
    }
  }

  /**
   * Re-enables a previously disabled server connection. Attempts to reconnect
   * using the stored transport. Does nothing if the server is not disabled.
   * @param serverName The name of the server to re-enable.
   */
  async reenableServer(serverName: string) {
    const client = this._clients[serverName];
    if (client) {
      logger.info(
        `[MCP Manager] Reenabling MCP server '${serverName}' in client '${this.name}'`
      );
      await client.reenable();
    }
  }

  /**
   * Closes and then restarts the transport connection for the specified server.
   * Useful for attempting to recover from connection issues without full
   * reconfiguration.
   * @param serverName The name of the server to reconnect.
   */
  async reconnectServer(serverName: string) {
    const client = this._clients[serverName];
    if (client) {
      logger.info(
        `[MCP Manager] Reconnecting MCP server '${serverName}' in client '${this.name}'`
      );
      await client.reconnect();
    }
  }

  /**
   * Updates the connections based on a provided map of server configurations.
   * - Connects any new servers defined in `mcpServers`.
   * - Disconnects any servers currently connected but not present in `mcpServers`.
   * - Reconnects existing servers if their configuration appears to have changed (implicitly handled by `connectServer`).
   * Sets the client's ready state once all connection attempts are complete.
   * @param mcpServers A record mapping server names to their configurations.
   */
  updateClients(mcpClients: Record<string, McpClientOptions>) {
    this._ready = false;
    const newServerNames = new Set(Object.keys(mcpClients));
    const currentServerNames = new Set(Object.keys(this._clients));

    const promises: Promise<void>[] = [];
    for (const serverName in mcpClients) {
      promises.push(this.connectClient(serverName, mcpClients[serverName]));
    }

    // Disconnect servers that are no longer in the config
    for (const serverName of currentServerNames) {
      if (!newServerNames.has(serverName)) {
        this.disconnectClient(serverName);
      }
    }

    Promise.all(promises)
      .then(() => {
        this._ready = true;
        while (this._readyListeners.length) {
          this._readyListeners.pop()?.resolve();
        }
      })
      .catch((err) => {
        while (this._readyListeners.length) {
          this._readyListeners.pop()?.reject(err);
        }
      });
  }

  /**
   * Creates a Genkit plugin that registers tools, prompts, and resources
   * from all connected and enabled MCP servers associated with this client.
   *
   * The plugin dynamically fetches capabilities from each server upon initialization.
   *
   * ```ts
   * export default configureGenkit({
   *   plugins: [
   *     myMcpClient.plugin()
   *   ],
   *   // ... other configurations
   * });
   * ```
   *
   * **Note:** The plugin is initialized once. Servers added or enabled *after*
   * Genkit initialization will not be reflected in the plugin's registered components
   * unless the Genkit configuration is reloaded.
   *
   * @param options Optional configuration for the plugin, such as its name.
   * @returns A GenkitPlugin instance.
   */
  async getAllTools(ai: Genkit): Promise<ToolAction[]> {
    await this.ready();
    let allTools: ToolAction[] = [];

    for (const serverName in this._clients) {
      const client = this._clients[serverName];
      if (!client.isDisabled()) {
        const tools = await client.getTools(ai);
        allTools.push(...tools);
      }

      //   if (capabilities?.prompts)
      //     promises.push(
      //       registerAllPrompts(ai, serverRef.client, { name, serverName })
      //     );
      //   if (capabilities?.resources)
      //     promises.push(
      //       registerResourceTools(ai, serverRef.client, { name, serverName })
      //     );
    }

    return allTools;
  }
}
