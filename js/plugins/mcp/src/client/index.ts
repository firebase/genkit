import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { SSEClientTransportOptions } from '@modelcontextprotocol/sdk/client/sse.js';
import { StdioServerParameters } from '@modelcontextprotocol/sdk/client/stdio.js';
import { Transport } from '@modelcontextprotocol/sdk/shared/transport.js';
import { GenkitError } from 'genkit';
import { logger } from 'genkit/logging';
import { genkitPlugin, GenkitPlugin } from 'genkit/plugin';
import { registerAllPrompts } from './prompts';
import { registerResourceTools } from './resources';
import { registerAllTools } from './tools';
import { transportFrom } from './util';
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

export interface McpClientOptions {
  /** Provide a name for this client which will be its namespace for all tools and prompts. Defaults to 'mcp'. */
  name?: string;
  /** Provide a version number for this client (defaults to 1.0.0). */
  version?: string;
  /** Provide one or more MCP servers to which this client should connect. */
  mcpServers?: Record<string, McpServerConfig>;
  /** Return tool responses in raw MCP form instead of processing them for Genkit compatibility. */
  rawToolResponses?: boolean;
}

export class GenkitMcpClient {
  name: string;
  version: string;
  private _servers: Record<string, McpServerRef> = {};
  private _readyListeners: {
    resolve: () => void;
    reject: (err: Error) => void;
  }[] = [];
  private _ready = false;
  rawToolResponses?: boolean;

  constructor(options: McpClientOptions) {
    this.name = options.name || 'genkitx-mcp';
    this.version = options.version || '1.0.0';
    this.rawToolResponses = options.rawToolResponses;

    if (options.mcpServers) this.updateServers(options.mcpServers);
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
  async connectServer(serverName: string, config: McpServerConfig) {
    const existingEntry = this._servers[serverName];
    if (existingEntry) await existingEntry.client.close();

    const { transport, type: transportType } = await transportFrom(config);
    if (!transport) {
      throw new GenkitError({
        status: 'INVALID_ARGUMENT',
        message: `[MCP] Server '${serverName}' could not determine valid transport config from supplied options.`,
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
          `[MCP] Error connecting server '${serverName}' via ${transportType} transport: ${e}`
        );
        disabled = true;
        error = (e as Error).toString();
      }
    }

    this._servers[serverName] = {
      client,
      transport,
      disabled,
      error,
    };
  }

  /**
   * Disconnects the specified MCP server and removes its registration
   * from this client instance.
   * @param serverName The name of the server to disconnect.
   */
  async disconnectServer(serverName: string) {
    const entry = this._servers[serverName];
    logger.info(
      `[MCP] Disconnecting MCP server '${serverName}' in client '${this.name}'.`
    );
    await entry.client.close();
    delete this._servers[serverName];
  }

  /**
   * Temporarily disables a server connection. Closes the underlying transport
   * but retains the server's configuration. Does nothing if the server is
   * already disabled.
   * @param serverName The name of the server to disable.
   */
  async disableServer(serverName: string) {
    const entry = this._servers[serverName];
    if (entry.disabled) return;
    logger.info(
      `[MCP] Disabling MCP server '${serverName}' in client '${this.name}'`
    );
    await entry.client.transport?.close();
    this._servers[serverName].disabled = true;
  }

  /**
   * Re-enables a previously disabled server connection. Attempts to reconnect
   * using the stored transport. Does nothing if the server is not disabled.
   * @param serverName The name of the server to re-enable.
   */
  async reenableServer(serverName: string) {
    const entry = this._servers[serverName];
    if (!entry.disabled) return;
    logger.info(
      `[MCP] Reenabling MCP server '${serverName}' in client '${this.name}'`
    );
    await entry.client.connect(entry.transport);
    this._servers[serverName].disabled = false;
  }

  /**
   * Closes and then restarts the transport connection for the specified server.
   * Useful for attempting to recover from connection issues without full
   * reconfiguration.
   * @param serverName The name of the server to reconnect.
   */
  async reconnectServer(serverName: string) {
    const entry = this._servers[serverName];
    logger.info(
      `[MCP] Reconnecting MCP server '${serverName}' in client '${this.name}'`
    );
    await entry.client.transport?.close();
    await entry.client.transport?.start();
  }

  /**
   * Updates the client's connections based on a provided map of server configurations.
   * - Connects any new servers defined in `mcpServers`.
   * - Disconnects any servers currently connected but not present in `mcpServers`.
   * - Reconnects existing servers if their configuration appears to have changed (implicitly handled by `connectServer`).
   * Sets the client's ready state once all connection attempts are complete.
   * @param mcpServers A record mapping server names to their configurations.
   */
  updateServers(mcpServers: Record<string, McpServerConfig>) {
    this._ready = false;
    const newServerNames = new Set(Object.keys(mcpServers));
    const currentServerNames = new Set(Object.keys(this._servers));

    const promises: Promise<void>[] = [];
    for (const serverName in mcpServers) {
      promises.push(this.connectServer(serverName, mcpServers[serverName]));
    }

    // Update existing or add new servers
    for (const serverName of newServerNames) {
      this.connectServer(serverName, mcpServers[serverName]);
    }

    // Disconnect servers that are no longer in the config
    for (const serverName of currentServerNames) {
      if (!newServerNames.has(serverName)) {
        this.disconnectServer(serverName);
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
  plugin(options?: { name?: string }): GenkitPlugin {
    const name = options?.name || this.name;
    return genkitPlugin(name, async (ai) => {
      await this.ready();

      const promises: Promise<any>[] = [];
      for (const serverName in this._servers) {
        const serverRef = this._servers[serverName];
        const capabilities = await serverRef.client.getServerCapabilities();
        if (capabilities?.tools)
          promises.push(
            registerAllTools(ai, serverRef.client, {
              rawToolResponses: this.rawToolResponses,
              serverName,
              name,
            })
          );
        if (capabilities?.prompts)
          promises.push(
            registerAllPrompts(ai, serverRef.client, { name, serverName })
          );
        if (capabilities?.resources)
          promises.push(
            registerResourceTools(ai, serverRef.client, { name, serverName })
          );
      }

      await Promise.all(promises);
    });
  }
}
