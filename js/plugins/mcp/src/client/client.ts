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

import { ExecutablePrompt } from '@genkit-ai/ai';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransportOptions } from '@modelcontextprotocol/sdk/client/sse.js';
import { StdioServerParameters } from '@modelcontextprotocol/sdk/client/stdio.js';
import { Transport } from '@modelcontextprotocol/sdk/shared/transport.js';
import { Genkit, GenkitError, ToolAction } from 'genkit';
import { logger } from 'genkit/logging';
import {
  fetchDynamicResourceTools,
  fetchDynamicTools,
  getExecutablePrompt,
  transportFrom,
} from '../util';
export type { SSEClientTransportOptions, StdioServerParameters, Transport };

interface McpServerRef {
  client: Client;
  transport: Transport;
  error?: string;
}

export interface McpServerControls {
  /** when true, the server will be stopped and its registered components will
   * not appear in lists/plugins/etc */
  disabled?: boolean;
  /**
   * If true, tool responses from the MCP server will be returned in their raw
   * MCP format. Otherwise (default), they are processed and potentially
   * simplified for better compatibility with Genkit's typical data structures.
   */
  rawToolResponses?: boolean;
}

export type McpStdioServerConfig = StdioServerParameters;

export type McpSSEServerConfig = { url: string } & SSEClientTransportOptions;

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
export type McpClientOptions = McpServerConfig & {
  /** Name for this server configuration */
  name: string;
  /**
   * An optional version number for this client. This is primarily for logging
   * and identification purposes. Defaults to '1.0.0'.
   */
  version?: string;
};

/**
 * Represents a client connection to a single MCP (Model Context Protocol) server.
 * It handles the lifecycle of the connection (connect, disconnect, disable, re-enable, reconnect)
 * and provides methods to fetch tools from the connected server.
 *
 * An instance of `GenkitMcpClient` is typically managed by a `GenkitMcpClientManager`
 * when dealing with multiple MCP server connections.
 */
export class GenkitMcpClient {
  _server?: McpServerRef;

  private name: string;
  private version: string;
  private serverConfig: McpServerConfig;
  private rawToolResponses?: boolean;
  private disabled: boolean;

  private _readyListeners: {
    resolve: () => void;
    reject: (err: Error) => void;
  }[] = [];
  private _ready = false;

  constructor(options: McpClientOptions) {
    this.name = options.name;
    this.version = options.version || '1.0.0';
    this.serverConfig = { ...options };
    this.rawToolResponses = !!options.rawToolResponses;
    this.disabled = !!options.disabled;

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
    this.connect(this.serverConfig)
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

    let error: string | undefined;

    const client = new Client({ name: this.name, version: this.version });
    client.registerCapabilities({ roots: {} });

    if (this.isEnabled()) {
      try {
        await client.connect(transport);
      } catch (e) {
        logger.warn(
          `[MCP Client] Error connecting server via ${transportType} transport: ${e}`
        );
        this.disabled = true;
        error = (e as Error).toString();
      }
    }

    this._server = {
      client,
      transport,
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
  disable() {
    if (!this.isEnabled()) return;
    if (this._server) {
      logger.info(`[MCP Client] Disabling MCP server in client '${this.name}'`);
      this.disabled = true;
    }
  }

  /**
   * Whether this client-server connection is enabled or not.
   */
  isEnabled() {
    return !this.disabled;
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
      this.disabled = false;
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
      await this.connect(this.serverConfig);
    }
  }

  /**
   * Fetches all tools available through this client, if the server
   * configuration is not disabled.
   */
  async getActiveTools(ai: Genkit): Promise<ToolAction[]> {
    await this.ready();
    let tools: ToolAction[] = [];

    if (this._server) {
      const capabilities = await this._server.client.getServerCapabilities();
      if (capabilities?.tools)
        tools.push(
          ...(await fetchDynamicTools(ai, this._server.client, {
            rawToolResponses: this.rawToolResponses,
            serverName: this.name,
            name: this.name,
          }))
        );
      if (capabilities?.resources)
        tools.push(
          ...fetchDynamicResourceTools(ai, this._server.client, {
            name: this.name,
            serverName: this.name,
          })
        );
    }

    return tools;
  }

  /**
   * Get the specified prompt as an `ExecutablePrompt` available through this
   * client. If no such prompt is found, return undefined.
   */
  async getPrompt(promptName: string): Promise<ExecutablePrompt | undefined> {
    await this.ready();

    if (this._server) {
      const capabilities = await this._server.client.getServerCapabilities();
      if (capabilities?.prompts) {
        return await getExecutablePrompt(this._server.client, {
          serverName: this.name,
          promptName,
          name: this.name,
        });
      }
      logger.info(`[MCP Client] No prompts are found in this MCP server.`);
    }
    return;
  }
}
