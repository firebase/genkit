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

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransportOptions } from '@modelcontextprotocol/sdk/client/sse.js';
import { StdioServerParameters } from '@modelcontextprotocol/sdk/client/stdio.js';
import { Transport } from '@modelcontextprotocol/sdk/shared/transport.js';
import { Genkit, GenkitError, ToolAction } from 'genkit';
import { logger } from 'genkit/logging';
import { transportFrom } from '../util';
import { fetchDynamicTools } from '../util/tools';
export type { SSEClientTransportOptions, StdioServerParameters, Transport };

interface McpServerRef {
  client: Client;
  transport: Transport;
  disabled?: boolean;
  error?: string;
}

export interface McpServerControls {
  // when true, the server will be stopped and its registered components will not appear in lists/plugins/etc
  disabled?: boolean;
  // Optional server name
  name?: string;
}

export type McpStdioServerConfig = StdioServerParameters & {
  url?: never;
  start?: never;
};

export type McpSSEServerConfig = { url: string } & SSEClientTransportOptions & {
    command?: never;
    start?: never;
  };

export type McpTransportServerConfig = {
  transport: Transport;
  client: Client;
  command?: never;
  url?: never;
};

/**
 * Configuration for an individual MCP server. The interface should be familiar
 * and compatible with existing tool configurations e.g. Cursor or Claude
 * Desktop.
 *
 * In addition to stdio servers, remote servers are supported via URL and
 * custom/arbitary transports are supported as well.
 */
export type McpServerConfig = (
  | McpStdioServerConfig
  | McpSSEServerConfig
  | McpTransportServerConfig
) &
  McpServerControls;

/**
 * Configuration options for an individual `GenkitMcpClient` instance.
 * This defines how the client connects to a single MCP server and how it behaves.
 */
export interface McpClientOptions {
  /**
   * An optional version number for this client. This is primarily for logging
   * and identification purposes. Defaults to '1.0.0'.
   */
  version?: string;
  /**
   * The configuration for the MCP server to which this client will connect.
   * This includes details like the server's command, URL, or a pre-existing transport.
   * See `McpServerConfig` for more details.
   */
  server: McpServerConfig;
  /**
   * If true, tool responses from the MCP server will be returned in their raw
   * MCP format. Otherwise (default), they are processed and potentially
   * simplified for better compatibility with Genkit's typical data structures.
   */
  rawToolResponses?: boolean;
}

/**
 * Represents a client connection to a single MCP (Model Context Protocol) server.
 * It handles the lifecycle of the connection (connect, disconnect, disable, re-enable, reconnect)
 * and provides methods to fetch tools from the connected server.
 *
 * An instance of `GenkitMcpClient` is typically managed by a `GenkitMcpClientManager`
 * when dealing with multiple MCP server connections.
 */
export class GenkitMcpClient {
  name: string;
  version: string;
  private _serverConfig: McpServerConfig;
  private _server?: McpServerRef;
  private _readyListeners: {
    resolve: () => void;
    reject: (err: Error) => void;
  }[] = [];
  private _ready = false;
  rawToolResponses?: boolean;

  constructor(name: string, options: McpClientOptions) {
    this.name = name;
    this.version = options.version || '1.0.0';
    this.rawToolResponses = options.rawToolResponses;
    this._serverConfig = options.server;
    this.initializeConnection();
  }

  /**
   * Sets up a connection based on a provided map of server configurations.
   * - Reconnects existing servers if their configuration appears to have changed (implicitly handled by `connectServer`).
   * Sets the client's ready state once all connection attempts are complete.
   * @param mcpServers A record mapping server names to their configurations.
   */
  initializeConnection() {
    this._ready = false;
    this.connect(this._serverConfig)
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
   * Returns a Promise that resolves when the client has attempted to connect
   * to all configured servers, or rejects if a critical error occurs during
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
  async connect(config: McpServerConfig) {
    if (this._server) await this._server.transport.close();
    logger.info(`[MCP Client] Connecting MCP server in client '${this.name}'.`);

    const { transport, type: transportType } = await transportFrom(config);
    if (!transport) {
      throw new GenkitError({
        status: 'INVALID_ARGUMENT',
        message: `[MCP Client] Could not determine valid transport config from supplied options.`,
      });
    }

    let disabled = config.disabled;
    let error: string | undefined;

    const client = new Client({ name: this.name, version: this.version });
    client.registerCapabilities({ roots: {} });

    if (!config.disabled) {
      try {
        await client.connect(transport);
      } catch (e) {
        logger.warn(
          `[MCP Client] Error connecting server via ${transportType} transport: ${e}`
        );
        disabled = true;
        error = (e as Error).toString();
      }
    }

    this._server = {
      client,
      transport,
      disabled,
      error,
    } as McpServerRef;
  }

  /**
   * Disconnects the MCP server and removes its registration
   * from this client instance.
   */
  async disconnect() {
    if (this._server) {
      logger.info(
        `[MCP Client] Disconnecting MCP server in client '${this.name}'.`
      );
      await this._server.client.close();
      this._server = undefined;
    }
  }

  /**
   * Temporarily disables a server connection. Closes the underlying transport
   * but retains the server's configuration. Does nothing if the server is
   * already disabled.
   */
  async disable() {
    if (this._server?.disabled) return;
    if (this._server) {
      logger.info(`[MCP Client] Disabling MCP server in client '${this.name}'`);
      this._server.disabled = true;
    }
  }

  /**
   * Whether this client-server connection is enabled or not.
   */
  isEnabled() {
    return !this._server?.disabled;
  }

  /**
   * Re-enables a previously disabled server connection. Does nothing if the
   * server is not disabled.
   */
  async reenable() {
    if (this.isEnabled()) return;
    if (this._server) {
      logger.info(
        `[MCP Client] Reenabling MCP server in client '${this.name}'`
      );
      this._server.disabled = false;
    }
  }

  /**
   * Closes and then restarts the transport connection for the specified server.
   * Useful for attempting to recover from connection issues without full
   * reconfiguration.
   */
  async reconnect() {
    if (this._server) {
      logger.info(
        `[MCP Client] Reconnecting MCP server in client '${this.name}'`
      );
      await this.disconnect();
      await this.connect(this._serverConfig);
    }
  }

  async getTools(ai: Genkit): Promise<ToolAction[]> {
    await this.ready();
    let tools: ToolAction[] = [];

    if (this._server) {
      const capabilities = await this._server.client.getServerCapabilities();
      if (capabilities?.tools)
        tools.push(
          ...(await fetchDynamicTools(ai, this._server.client, {
            rawToolResponses: this.rawToolResponses,
            serverName: this.name + '-mcp-server',
            name: this.name,
          }))
        );
      //   if (capabilities?.prompts)
      //     promises.push(
      //       registerAllPrompts(ai, serverRef.client, { name, serverName })
      //     );
      //   if (capabilities?.resources)
      //     promises.push(
      //       registerResourceTools(ai, serverRef.client, { name, serverName })
      //     );
    }

    return tools;
  }
}
