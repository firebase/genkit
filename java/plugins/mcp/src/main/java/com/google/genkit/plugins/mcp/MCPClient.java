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

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.genkit.ai.Tool;
import com.google.genkit.core.GenkitException;
import com.google.genkit.core.Registry;

import io.modelcontextprotocol.client.McpClient;
import io.modelcontextprotocol.client.McpSyncClient;
import io.modelcontextprotocol.client.transport.HttpClientSseClientTransport;
import io.modelcontextprotocol.client.transport.HttpClientStreamableHttpTransport;
import io.modelcontextprotocol.client.transport.ServerParameters;
import io.modelcontextprotocol.client.transport.StdioClientTransport;
import io.modelcontextprotocol.json.McpJsonMapper;
import io.modelcontextprotocol.spec.McpClientTransport;
import io.modelcontextprotocol.spec.McpSchema;
import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import io.modelcontextprotocol.spec.McpSchema.ClientCapabilities;
import io.modelcontextprotocol.spec.McpSchema.ListResourcesResult;
import io.modelcontextprotocol.spec.McpSchema.ListToolsResult;
import io.modelcontextprotocol.spec.McpSchema.ReadResourceResult;

/**
 * MCP Client that manages connections to MCP servers and provides access to
 * their tools and resources.
 *
 * <p>
 * This client wraps the MCP Java SDK and converts MCP tools to Genkit tools,
 * allowing them to be used seamlessly in Genkit applications.
 *
 * <p>
 * Example usage:
 *
 * <pre>{@code
 * MCPClient client = new MCPClient("filesystem",
 * 		MCPServerConfig.stdio("npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"),
 * 		Duration.ofSeconds(30), false);
 *
 * client.connect();
 * List<Tool<?, ?>> tools = client.getTools(registry);
 * client.disconnect();
 * }</pre>
 */
public class MCPClient {

  private static final Logger logger = LoggerFactory.getLogger(MCPClient.class);
  private static final ObjectMapper objectMapper = new ObjectMapper();

  private final String serverName;
  private final MCPServerConfig config;
  private final Duration requestTimeout;
  private final boolean rawToolResponses;

  private McpSyncClient client;
  private McpClientTransport transport;
  private boolean connected = false;

  // Cache for tools and resources
  private final Map<String, Tool<?, ?>> toolCache = new ConcurrentHashMap<>();

  /**
   * Creates a new MCP client.
   *
   * @param serverName
   *            the name to identify this server
   * @param config
   *            the server configuration
   * @param requestTimeout
   *            timeout for requests
   * @param rawToolResponses
   *            whether to return raw MCP responses
   */
  public MCPClient(String serverName, MCPServerConfig config, Duration requestTimeout, boolean rawToolResponses) {
    this.serverName = serverName;
    this.config = config;
    this.requestTimeout = requestTimeout;
    this.rawToolResponses = rawToolResponses;
  }

  /**
   * Connects to the MCP server.
   *
   * @throws GenkitException
   *             if connection fails
   */
  public void connect() throws GenkitException {
    if (connected) {
      logger.debug("Already connected to MCP server: {}", serverName);
      return;
    }

    if (config.isDisabled()) {
      logger.info("MCP server {} is disabled, skipping connection", serverName);
      return;
    }

    try {
      logger.info("Connecting to MCP server: {}", serverName);
      transport = createTransport();

      client = McpClient.sync(transport).requestTimeout(requestTimeout)
          .capabilities(ClientCapabilities.builder().roots(true).build()).build();

      client.initialize();
      connected = true;
      logger.info("Successfully connected to MCP server: {}", serverName);
    } catch (Exception e) {
      throw new GenkitException("Failed to connect to MCP server: " + serverName, e);
    }
  }

  /**
   * Disconnects from the MCP server.
   */
  public void disconnect() {
    if (!connected || client == null) {
      return;
    }

    try {
      logger.info("Disconnecting from MCP server: {}", serverName);
      client.closeGracefully();
      connected = false;
      toolCache.clear();
      logger.info("Disconnected from MCP server: {}", serverName);
    } catch (Exception e) {
      logger.warn("Error disconnecting from MCP server {}: {}", serverName, e.getMessage());
    }
  }

  /**
   * Gets tools from the MCP server as Genkit tools.
   *
   * @param registry
   *            the Genkit registry for tool registration
   * @return list of Genkit tools
   * @throws GenkitException
   *             if listing tools fails
   */
  public List<Tool<?, ?>> getTools(Registry registry) throws GenkitException {
    if (!connected) {
      throw new GenkitException("Not connected to MCP server: " + serverName);
    }

    List<Tool<?, ?>> tools = new ArrayList<>();

    try {
      ListToolsResult result = client.listTools();

      for (McpSchema.Tool mcpTool : result.tools()) {
        Tool<?, ?> tool = createGenkitTool(mcpTool, registry);
        tools.add(tool);
        toolCache.put(mcpTool.name(), tool);
      }

      logger.info("Loaded {} tools from MCP server: {}", tools.size(), serverName);
    } catch (Exception e) {
      throw new GenkitException("Failed to list tools from MCP server: " + serverName, e);
    }

    return tools;
  }

  /**
   * Gets resources from the MCP server.
   *
   * @return list of MCP resources
   * @throws GenkitException
   *             if listing resources fails
   */
  public List<MCPResource> getResources() throws GenkitException {
    if (!connected) {
      throw new GenkitException("Not connected to MCP server: " + serverName);
    }

    List<MCPResource> resources = new ArrayList<>();

    try {
      ListResourcesResult result = client.listResources();

      for (McpSchema.Resource mcpResource : result.resources()) {
        MCPResource resource = new MCPResource(mcpResource.uri(), mcpResource.name(),
            mcpResource.description() != null ? mcpResource.description() : "", mcpResource.mimeType());
        resources.add(resource);
      }

      logger.info("Loaded {} resources from MCP server: {}", resources.size(), serverName);
    } catch (Exception e) {
      throw new GenkitException("Failed to list resources from MCP server: " + serverName, e);
    }

    return resources;
  }

  /**
   * Reads a resource by URI.
   *
   * @param uri
   *            the resource URI
   * @return the resource content
   * @throws GenkitException
   *             if reading fails
   */
  public MCPResourceContent readResource(String uri) throws GenkitException {
    if (!connected) {
      throw new GenkitException("Not connected to MCP server: " + serverName);
    }

    try {
      ReadResourceResult result = client.readResource(new McpSchema.ReadResourceRequest(uri));

      List<MCPResourceContent.ContentPart> parts = new ArrayList<>();
      for (McpSchema.ResourceContents content : result.contents()) {
        if (content instanceof McpSchema.TextResourceContents textContent) {
          parts.add(new MCPResourceContent.ContentPart(textContent.text(), null, content.mimeType()));
        } else if (content instanceof McpSchema.BlobResourceContents blobContent) {
          parts.add(new MCPResourceContent.ContentPart(null, blobContent.blob(), content.mimeType()));
        }
      }

      return new MCPResourceContent(uri, parts);
    } catch (Exception e) {
      throw new GenkitException("Failed to read resource: " + uri, e);
    }
  }

  /**
   * Calls an MCP tool directly.
   *
   * @param toolName
   *            the tool name
   * @param arguments
   *            the tool arguments
   * @return the tool result
   * @throws GenkitException
   *             if the call fails
   */
  @SuppressWarnings("unchecked")
  public Object callTool(String toolName, Map<String, Object> arguments) throws GenkitException {
    if (!connected) {
      throw new GenkitException("Not connected to MCP server: " + serverName);
    }

    try {
      logger.debug("Calling MCP tool {}/{} with arguments: {}", serverName, toolName, arguments);

      CallToolResult result = client.callTool(new McpSchema.CallToolRequest(toolName, arguments));

      if (rawToolResponses) {
        return result;
      }

      return processToolResult(result);
    } catch (Exception e) {
      throw new GenkitException("Failed to call MCP tool: " + toolName, e);
    }
  }

  /**
   * Gets the server name.
   *
   * @return the server name
   */
  public String getServerName() {
    return serverName;
  }

  /**
   * Checks if connected to the MCP server.
   *
   * @return true if connected
   */
  public boolean isConnected() {
    return connected;
  }

  // Private methods

  private McpClientTransport createTransport() {
    McpJsonMapper jsonMapper = McpJsonMapper.getDefault();

    switch (config.getTransportType()) {
      case STDIO :
        ServerParameters.Builder paramsBuilder = ServerParameters.builder(config.getCommand());
        if (!config.getArgs().isEmpty()) {
          paramsBuilder.args(config.getArgs().toArray(new String[0]));
        }
        if (!config.getEnv().isEmpty()) {
          paramsBuilder.env(config.getEnv());
        }
        return new StdioClientTransport(paramsBuilder.build(), jsonMapper);

      case HTTP :
        return HttpClientSseClientTransport.builder(config.getUrl()).build();

      case STREAMABLE_HTTP :
        return HttpClientStreamableHttpTransport.builder(config.getUrl()).build();

      default :
        throw new IllegalArgumentException("Unsupported transport type: " + config.getTransportType());
    }
  }

  @SuppressWarnings("unchecked")
  private Tool<Map<String, Object>, Object> createGenkitTool(McpSchema.Tool mcpTool, Registry registry) {
    String toolName = serverName + "/" + mcpTool.name();

    // Convert MCP input schema to Map
    Map<String, Object> inputSchema = convertJsonSchema(mcpTool.inputSchema());

    Tool<Map<String, Object>, Object> tool = Tool.<Map<String, Object>, Object>builder().name(toolName)
        .description(mcpTool.description() != null ? mcpTool.description() : "")
        .inputSchema(inputSchema != null ? inputSchema : new HashMap<>())
        .inputClass((Class<Map<String, Object>>) (Class<?>) Map.class).handler((ctx, input) -> {
          return callTool(mcpTool.name(), input);
        }).build();

    // Register the tool
    tool.register(registry);

    logger.debug("Created Genkit tool: {} from MCP server: {}", toolName, serverName);
    return tool;
  }

  @SuppressWarnings("unchecked")
  private Map<String, Object> convertJsonSchema(Object schema) {
    if (schema == null) {
      return new HashMap<>();
    }
    if (schema instanceof Map) {
      return (Map<String, Object>) schema;
    }
    try {
      JsonNode node = objectMapper.valueToTree(schema);
      return objectMapper.convertValue(node, Map.class);
    } catch (Exception e) {
      logger.warn("Failed to convert schema: {}", e.getMessage());
      return new HashMap<>();
    }
  }

  private Object processToolResult(CallToolResult result) {
    if (result.isError() != null && result.isError()) {
      StringBuilder errorText = new StringBuilder();
      for (McpSchema.Content content : result.content()) {
        if (content instanceof McpSchema.TextContent textContent) {
          errorText.append(textContent.text());
        }
      }
      return Map.of("error", errorText.toString());
    }

    // Check if all content is text
    boolean allText = result.content().stream().allMatch(c -> c instanceof McpSchema.TextContent);

    if (allText) {
      StringBuilder text = new StringBuilder();
      for (McpSchema.Content content : result.content()) {
        if (content instanceof McpSchema.TextContent textContent) {
          text.append(textContent.text());
        }
      }
      String textResult = text.toString();

      // Try to parse as JSON
      if (textResult.trim().startsWith("{") || textResult.trim().startsWith("[")) {
        try {
          return objectMapper.readValue(textResult, Object.class);
        } catch (Exception e) {
          // Return as plain text
        }
      }
      return textResult;
    }

    // Return first content item or the whole result
    if (result.content().size() == 1) {
      McpSchema.Content content = result.content().get(0);
      if (content instanceof McpSchema.TextContent textContent) {
        return textContent.text();
      } else if (content instanceof McpSchema.ImageContent imageContent) {
        return Map.of("type", "image", "data", imageContent.data(), "mimeType", imageContent.mimeType());
      }
    }

    // Return raw content list
    List<Map<String, Object>> contentList = new ArrayList<>();
    for (McpSchema.Content content : result.content()) {
      if (content instanceof McpSchema.TextContent textContent) {
        contentList.add(Map.of("type", "text", "text", textContent.text()));
      } else if (content instanceof McpSchema.ImageContent imageContent) {
        contentList
            .add(Map.of("type", "image", "data", imageContent.data(), "mimeType", imageContent.mimeType()));
      }
    }
    return contentList;
  }
}
