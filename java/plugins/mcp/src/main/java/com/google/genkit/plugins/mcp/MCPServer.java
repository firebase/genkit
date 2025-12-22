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

import java.util.Collections;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genkit.ai.Tool;
import com.google.genkit.core.Action;
import com.google.genkit.core.ActionContext;
import com.google.genkit.core.ActionType;
import com.google.genkit.core.GenkitException;
import com.google.genkit.core.Registry;

import io.modelcontextprotocol.json.McpJsonMapper;
import io.modelcontextprotocol.server.McpServer;
import io.modelcontextprotocol.server.McpServerFeatures;
import io.modelcontextprotocol.server.McpSyncServer;
import io.modelcontextprotocol.server.transport.StdioServerTransportProvider;
import io.modelcontextprotocol.spec.McpSchema;
import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import io.modelcontextprotocol.spec.McpSchema.ServerCapabilities;
import io.modelcontextprotocol.spec.McpServerTransportProvider;

/**
 * MCP Server that exposes Genkit tools, prompts, and flows as MCP endpoints.
 *
 * <p>
 * This server allows external MCP clients (like Claude Desktop, or other AI
 * agents) to discover and invoke Genkit tools.
 *
 * <p>
 * Example usage:
 *
 * <pre>{@code
 * // Create Genkit and define some tools
 * Genkit genkit = Genkit.builder().build();
 *
 * genkit.defineTool("calculator", "Performs basic math",
 *     Map.of("type", "object", ...),
 *     Map.class,
 *     (ctx, input) -> {
 *         // Tool implementation
 *         return result;
 *     });
 *
 * // Create and start MCP server
 * MCPServer mcpServer = new MCPServer(genkit.getRegistry(),
 *     MCPServerOptions.builder()
 *         .name("my-tools-server")
 *         .version("1.0.0")
 *         .build());
 *
 * // Start with STDIO transport (for use with Claude Desktop, etc.)
 * mcpServer.start();
 * }</pre>
 *
 * @see MCPServerOptions
 */
public class MCPServer {

  private static final Logger logger = LoggerFactory.getLogger(MCPServer.class);
  private static final McpJsonMapper jsonMapper = McpJsonMapper.getDefault();

  private final Registry registry;
  private final MCPServerOptions options;
  private McpSyncServer server;
  private boolean running = false;

  /**
   * Creates a new MCP server.
   *
   * @param registry
   *            the Genkit registry containing tools to expose
   * @param options
   *            the server options
   */
  public MCPServer(Registry registry, MCPServerOptions options) {
    this.registry = registry;
    this.options = options;
  }

  /**
   * Creates a new MCP server with default options.
   *
   * @param registry
   *            the Genkit registry containing tools to expose
   */
  public MCPServer(Registry registry) {
    this(registry, MCPServerOptions.builder().build());
  }

  /**
   * Starts the MCP server with STDIO transport.
   *
   * <p>
   * This is the standard transport for use with Claude Desktop and other MCP
   * clients that launch the server as a subprocess.
   *
   * @throws GenkitException
   *             if the server fails to start
   */
  public void start() throws GenkitException {
    start(new StdioServerTransportProvider(jsonMapper));
  }

  /**
   * Starts the MCP server with a custom transport provider.
   *
   * @param transportProvider
   *            the transport provider to use
   * @throws GenkitException
   *             if the server fails to start
   */
  public void start(McpServerTransportProvider transportProvider) throws GenkitException {
    if (running) {
      logger.warn("MCP server is already running");
      return;
    }

    try {
      logger.info("Starting MCP server: {} v{}", options.getName(), options.getVersion());

      // Build the server with capabilities
      server = McpServer.sync(transportProvider).serverInfo(options.getName(), options.getVersion())
          .capabilities(ServerCapabilities.builder().tools(true) // Enable tool support
              .resources(false, false) // Resources not yet supported
              .prompts(false) // Prompts not yet fully supported
              .logging() // Enable logging
              .build())
          .build();

      // Register all tools from the registry
      registerTools();

      running = true;
      logger.info("MCP server started successfully with {} tools", getToolCount());

    } catch (Exception e) {
      throw new GenkitException("Failed to start MCP server", e);
    }
  }

  /**
   * Stops the MCP server.
   */
  public void stop() {
    if (!running || server == null) {
      return;
    }

    try {
      logger.info("Stopping MCP server: {}", options.getName());
      server.close();
      running = false;
      logger.info("MCP server stopped");
    } catch (Exception e) {
      logger.error("Error stopping MCP server: {}", e.getMessage());
    }
  }

  /**
   * Checks if the server is running.
   *
   * @return true if running
   */
  public boolean isRunning() {
    return running;
  }

  /**
   * Gets the server options.
   *
   * @return the options
   */
  public MCPServerOptions getOptions() {
    return options;
  }

  // Private methods

  @SuppressWarnings("unchecked")
  private void registerTools() {
    // Get all tool actions from the registry
    List<Action<?, ?, ?>> actions = registry.listActions();

    for (Action<?, ?, ?> action : actions) {
      // Only register tool actions
      if (action.getType() == ActionType.TOOL) {
        try {
          registerTool((Tool<Object, Object>) action);
        } catch (Exception e) {
          logger.error("Failed to register tool {}: {}", action.getName(), e.getMessage());
        }
      }
    }
  }

  private void registerTool(Tool<Object, Object> tool) {
    String name = tool.getName();
    String description = tool.getDescription() != null ? tool.getDescription() : "";

    // Convert input schema to JsonSchema
    McpSchema.JsonSchema inputSchema;
    try {
      Map<String, Object> schema = tool.getInputSchema();
      if (schema == null || schema.isEmpty()) {
        inputSchema = new McpSchema.JsonSchema("object", Collections.emptyMap(), null, null, null, null);
      } else {
        String schemaJson = jsonMapper.writeValueAsString(schema);
        inputSchema = jsonMapper.readValue(schemaJson, McpSchema.JsonSchema.class);
      }
    } catch (Exception e) {
      logger.warn("Failed to serialize input schema for tool {}, using empty schema", name);
      inputSchema = new McpSchema.JsonSchema("object", Collections.emptyMap(), null, null, null, null);
    }

    // Create MCP tool using the builder
    McpSchema.Tool mcpTool = McpSchema.Tool.builder().name(name).description(description).inputSchema(inputSchema)
        .build();

    // Create MCP tool specification
    McpServerFeatures.SyncToolSpecification toolSpec = new McpServerFeatures.SyncToolSpecification(mcpTool,
        (exchange, arguments) -> {
          try {
            logger.debug("Executing tool: {} with arguments: {}", name, arguments);

            // Create action context with registry
            ActionContext ctx = new ActionContext(registry);

            // Execute the tool
            Object result = tool.run(ctx, arguments);

            // Convert result to text content
            String resultText;
            if (result instanceof String) {
              resultText = (String) result;
            } else {
              resultText = jsonMapper.writeValueAsString(result);
            }

            logger.debug("Tool {} completed successfully", name);

            return CallToolResult.builder().addTextContent(resultText).isError(false).build();

          } catch (Exception e) {
            logger.error("Tool {} failed: {}", name, e.getMessage());
            return CallToolResult.builder().addTextContent("Error: " + e.getMessage()).isError(true)
                .build();
          }
        });

    server.addTool(toolSpec);
    logger.debug("Registered MCP tool: {}", name);
  }

  private int getToolCount() {
    int count = 0;
    List<Action<?, ?, ?>> actions = registry.listActions();
    for (Action<?, ?, ?> action : actions) {
      if (action.getType() == ActionType.TOOL) {
        count++;
      }
    }
    return count;
  }
}
