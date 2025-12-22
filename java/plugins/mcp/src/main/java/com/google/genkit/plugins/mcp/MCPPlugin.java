/*
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
 *
 * SPDX-License-Identifier: Apache-2.0
 */

package com.google.genkit.plugins.mcp;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genkit.ai.Tool;
import com.google.genkit.core.Action;
import com.google.genkit.core.GenkitException;
import com.google.genkit.core.Plugin;
import com.google.genkit.core.Registry;

/**
 * MCP Plugin for Genkit.
 *
 * <p>
 * This plugin enables Genkit to connect to MCP (Model Context Protocol) servers
 * and use their tools. MCP provides a standardized way for AI applications to
 * interact with external tools and data sources.
 *
 * <p>
 * Features:
 * <ul>
 * <li>Connect to multiple MCP servers (STDIO or HTTP transports)</li>
 * <li>Automatic conversion of MCP tools to Genkit tools</li>
 * <li>Access MCP resources programmatically</li>
 * <li>Support for tool caching and lazy loading</li>
 * </ul>
 *
 * <p>
 * Example usage:
 *
 * <pre>{@code
 * // Create the MCP plugin with server configurations
 * MCPPlugin mcpPlugin = MCPPlugin.create(MCPPluginOptions.builder().name("my-mcp-host")
 * 		.addServer("filesystem",
 * 				MCPServerConfig.stdio("npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"))
 * 		.addServer("weather", MCPServerConfig.http("http://localhost:3001/mcp")).build());
 *
 * // Create Genkit with the MCP plugin
 * Genkit genkit = Genkit.builder().plugin(mcpPlugin).build();
 *
 * // Use MCP tools in flows
 * Flow<String, String, Void> myFlow = genkit.defineFlow("myFlow", String.class, String.class, (ctx, input) -> {
 * 	// MCP tools are available as: "serverName/toolName"
 * 	// e.g., "filesystem/readFile", "weather/getForecast"
 * 	ModelResponse response = genkit.generate(
 * 			GenerateOptions.builder().model("openai/gpt-4o").prompt(input).tools(mcpPlugin.getTools()).build());
 * 	return response.getText();
 * });
 * }</pre>
 *
 * @see MCPPluginOptions
 * @see MCPServerConfig
 * @see MCPClient
 */
public class MCPPlugin implements Plugin {

  private static final Logger logger = LoggerFactory.getLogger(MCPPlugin.class);

  private final MCPPluginOptions options;
  private final Map<String, MCPClient> clients = new ConcurrentHashMap<>();
  private final List<Tool<?, ?>> allTools = new ArrayList<>();
  private Registry registry;
  private boolean initialized = false;

  /**
   * Creates a new MCP plugin with the given options.
   *
   * @param options
   *            the plugin options
   */
  public MCPPlugin(MCPPluginOptions options) {
    this.options = options;
  }

  /**
   * Creates an MCP plugin with the given options.
   *
   * @param options
   *            the plugin options
   * @return a new MCPPlugin
   */
  public static MCPPlugin create(MCPPluginOptions options) {
    return new MCPPlugin(options);
  }

  /**
   * Creates an MCP plugin with a single STDIO server.
   *
   * @param serverName
   *            the name for the server
   * @param command
   *            the command to execute
   * @param args
   *            the command arguments
   * @return a new MCPPlugin
   */
  public static MCPPlugin stdio(String serverName, String command, String... args) {
    return create(MCPPluginOptions.builder().addServer(serverName, MCPServerConfig.stdio(command, args)).build());
  }

  /**
   * Creates an MCP plugin with a single HTTP server.
   *
   * @param serverName
   *            the name for the server
   * @param url
   *            the server URL
   * @return a new MCPPlugin
   */
  public static MCPPlugin http(String serverName, String url) {
    return create(MCPPluginOptions.builder().addServer(serverName, MCPServerConfig.http(url)).build());
  }

  @Override
  public String getName() {
    return "mcp";
  }

  @Override
  public List<Action<?, ?, ?>> init() {
    // This method doesn't have access to the registry, so we return empty
    // The actual initialization happens in init(Registry)
    return new ArrayList<>();
  }

  @Override
  public List<Action<?, ?, ?>> init(Registry registry) {
    this.registry = registry;
    List<Action<?, ?, ?>> actions = new ArrayList<>();

    logger.info("Initializing MCP plugin: {}", options.getName());

    // Connect to all configured servers
    for (Map.Entry<String, MCPServerConfig> entry : options.getServers().entrySet()) {
      String serverName = entry.getKey();
      MCPServerConfig config = entry.getValue();

      if (config.isDisabled()) {
        logger.info("MCP server {} is disabled, skipping", serverName);
        continue;
      }

      try {
        MCPClient client = new MCPClient(serverName, config, options.getRequestTimeout(),
            options.isRawToolResponses());

        client.connect();
        clients.put(serverName, client);

        // Load tools from this server
        List<Tool<?, ?>> tools = client.getTools(registry);
        allTools.addAll(tools);
        actions.addAll(tools);

        logger.info("Connected to MCP server {} with {} tools", serverName, tools.size());
      } catch (Exception e) {
        logger.error("Failed to connect to MCP server {}: {}", serverName, e.getMessage());
        // Continue with other servers
      }
    }

    initialized = true;
    logger.info("MCP plugin initialized with {} servers and {} total tools", clients.size(), allTools.size());

    return actions;
  }

  /**
   * Gets all tools from all connected MCP servers.
   *
   * @return list of tools
   */
  public List<Tool<?, ?>> getTools() {
    return new ArrayList<>(allTools);
  }

  /**
   * Gets tools from a specific MCP server.
   *
   * @param serverName
   *            the server name
   * @return list of tools from that server
   * @throws GenkitException
   *             if the server is not found or not connected
   */
  public List<Tool<?, ?>> getTools(String serverName) throws GenkitException {
    MCPClient client = clients.get(serverName);
    if (client == null) {
      throw new GenkitException("MCP server not found: " + serverName);
    }
    return client.getTools(registry);
  }

  /**
   * Gets resources from a specific MCP server.
   *
   * @param serverName
   *            the server name
   * @return list of resources
   * @throws GenkitException
   *             if the server is not found or not connected
   */
  public List<MCPResource> getResources(String serverName) throws GenkitException {
    MCPClient client = clients.get(serverName);
    if (client == null) {
      throw new GenkitException("MCP server not found: " + serverName);
    }
    return client.getResources();
  }

  /**
   * Reads a resource from an MCP server.
   *
   * @param serverName
   *            the server name
   * @param uri
   *            the resource URI
   * @return the resource content
   * @throws GenkitException
   *             if reading fails
   */
  public MCPResourceContent readResource(String serverName, String uri) throws GenkitException {
    MCPClient client = clients.get(serverName);
    if (client == null) {
      throw new GenkitException("MCP server not found: " + serverName);
    }
    return client.readResource(uri);
  }

  /**
   * Calls an MCP tool directly.
   *
   * @param serverName
   *            the server name
   * @param toolName
   *            the tool name (without server prefix)
   * @param arguments
   *            the tool arguments
   * @return the tool result
   * @throws GenkitException
   *             if the call fails
   */
  public Object callTool(String serverName, String toolName, Map<String, Object> arguments) throws GenkitException {
    MCPClient client = clients.get(serverName);
    if (client == null) {
      throw new GenkitException("MCP server not found: " + serverName);
    }
    return client.callTool(toolName, arguments);
  }

  /**
   * Gets the client for a specific server.
   *
   * @param serverName
   *            the server name
   * @return the client, or null if not found
   */
  public MCPClient getClient(String serverName) {
    return clients.get(serverName);
  }

  /**
   * Gets all connected clients.
   *
   * @return map of server name to client
   */
  public Map<String, MCPClient> getClients() {
    return new HashMap<>(clients);
  }

  /**
   * Disconnects all MCP clients.
   */
  public void disconnect() {
    logger.info("Disconnecting all MCP clients");
    for (MCPClient client : clients.values()) {
      try {
        client.disconnect();
      } catch (Exception e) {
        logger.warn("Error disconnecting MCP client {}: {}", client.getServerName(), e.getMessage());
      }
    }
    clients.clear();
    allTools.clear();
    initialized = false;
  }

  /**
   * Checks if the plugin is initialized.
   *
   * @return true if initialized
   */
  public boolean isInitialized() {
    return initialized;
  }

  /**
   * Gets the plugin options.
   *
   * @return the options
   */
  public MCPPluginOptions getOptions() {
    return options;
  }
}
