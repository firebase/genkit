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

package com.google.genkit.samples;

import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genkit.Genkit;
import com.google.genkit.GenkitOptions;
import com.google.genkit.ai.GenerateOptions;
import com.google.genkit.ai.GenerationConfig;
import com.google.genkit.ai.ModelResponse;
import com.google.genkit.ai.Tool;
import com.google.genkit.core.Flow;
import com.google.genkit.plugins.jetty.JettyPlugin;
import com.google.genkit.plugins.jetty.JettyPluginOptions;
import com.google.genkit.plugins.mcp.MCPClient;
import com.google.genkit.plugins.mcp.MCPPlugin;
import com.google.genkit.plugins.mcp.MCPPluginOptions;
import com.google.genkit.plugins.mcp.MCPResource;
import com.google.genkit.plugins.mcp.MCPServerConfig;
import com.google.genkit.plugins.openai.OpenAIPlugin;

/**
 * Sample application demonstrating Genkit with MCP (Model Context Protocol).
 *
 * <p>
 * This example shows how to:
 * <ul>
 * <li>Configure the MCP plugin with different server types</li>
 * <li>Connect to MCP servers via STDIO (local processes) and HTTP</li>
 * <li>Use MCP tools in Genkit flows</li>
 * <li>Access MCP resources</li>
 * <li>Combine MCP tools with AI models for powerful workflows</li>
 * </ul>
 *
 * <p>
 * Prerequisites:
 * <ul>
 * <li>Node.js and npm installed (for MCP server packages)</li>
 * <li>OPENAI_API_KEY environment variable set</li>
 * </ul>
 *
 * <p>
 * To run:
 * <ol>
 * <li>Set the OPENAI_API_KEY environment variable</li>
 * <li>Run: mvn exec:java</li>
 * </ol>
 *
 * <p>
 * Available MCP servers in this sample:
 * <ul>
 * <li>filesystem: Access files
 * using @modelcontextprotocol/server-filesystem</li>
 * <li>everything: Demo server with various tool types</li>
 * </ul>
 */
public class MCPSample {

  private static final Logger logger = LoggerFactory.getLogger(MCPSample.class);

  public static void main(String[] args) throws Exception {
    logger.info("Starting Genkit MCP Sample...");

    // =======================================================
    // Configure MCP Plugin with multiple servers
    // =======================================================

    // Get the allowed directory for the filesystem server
    // Default to /tmp or use MCP_ALLOWED_DIR environment variable
    String tempAllowedDir = System.getenv("MCP_ALLOWED_DIR");
    if (tempAllowedDir == null || tempAllowedDir.isEmpty()) {
      tempAllowedDir = System.getProperty("java.io.tmpdir");
    }
    final String allowedDir = tempAllowedDir;
    logger.info("Filesystem server will have access to: {}", allowedDir);

    MCPPluginOptions mcpOptions = MCPPluginOptions.builder().name("genkit-mcp-sample")
        // Filesystem server - allows file operations in allowed directory
        .addServer("filesystem",
            MCPServerConfig.stdio("npx", "-y", "@modelcontextprotocol/server-filesystem", allowedDir))
        // Everything server - demo server with various tools
        .addServer("everything", MCPServerConfig.stdio("npx", "-y", "@modelcontextprotocol/server-everything"))
        .build();

    MCPPlugin mcpPlugin = MCPPlugin.create(mcpOptions);

    // Create the Jetty server plugin
    JettyPlugin jetty = new JettyPlugin(JettyPluginOptions.builder().port(8080).build());

    // =======================================================
    // Create Genkit with plugins
    // =======================================================

    Genkit genkit = Genkit.builder().options(GenkitOptions.builder().devMode(true).reflectionPort(3100).build())
        .plugin(OpenAIPlugin.create()).plugin(mcpPlugin).plugin(jetty).build();

    // =======================================================
    // Example 1: List available MCP tools
    // =======================================================

    Flow<Void, String, Void> listToolsFlow = genkit.defineFlow("listMcpTools", Void.class, String.class,
        (ctx, input) -> {
          StringBuilder sb = new StringBuilder();
          sb.append("=== Available MCP Tools ===\n\n");

          List<Tool<?, ?>> tools = mcpPlugin.getTools();
          for (Tool<?, ?> tool : tools) {
            sb.append("- ").append(tool.getName()).append("\n");
            sb.append("  Description: ").append(tool.getDescription()).append("\n\n");
          }

          return sb.toString();
        });

    // =======================================================
    // Example 2: Use MCP filesystem tools with AI
    // =======================================================

    Flow<String, String, Void> fileAssistantFlow = genkit.defineFlow("fileAssistant", String.class, String.class,
        (ctx, userRequest) -> {
          logger.info("File assistant processing request: {}", userRequest);

          // Get all MCP tools
          List<Tool<?, ?>> mcpTools = mcpPlugin.getTools();

          ModelResponse response = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o-mini")
              .system("You are a helpful file assistant. You can read, write, and list files "
                  + "using the available filesystem tools. The filesystem tools use the server name "
                  + "'filesystem' as prefix (e.g., 'filesystem/read_file'). "
                  + "Always explain what you're doing and show file contents when relevant.")
              .prompt(userRequest).tools(mcpTools)
              .config(GenerationConfig.builder().temperature(0.7).maxOutputTokens(1000).build()).build());

          return response.getText();
        });

    // =======================================================
    // Example 3: Direct MCP tool usage (without AI)
    // =======================================================

    Flow<String, String, Void> readFileFlow = genkit.defineFlow("readFile", String.class, String.class,
        (ctx, filePath) -> {
          logger.info("Reading file via MCP: {}", filePath);

          try {
            Object result = mcpPlugin.callTool("filesystem", "read_file", Map.of("path", filePath));
            return result != null ? result.toString() : "File is empty";
          } catch (Exception e) {
            return "Error reading file: " + e.getMessage();
          }
        });

    // =======================================================
    // Example 4: List MCP resources
    // =======================================================

    Flow<String, String, Void> listResourcesFlow = genkit.defineFlow("listResources", String.class, String.class,
        (ctx, serverName) -> {
          StringBuilder sb = new StringBuilder();
          sb.append("=== Resources from ").append(serverName).append(" ===\n\n");

          try {
            List<MCPResource> resources = mcpPlugin.getResources(serverName);
            if (resources.isEmpty()) {
              sb.append("No resources available.\n");
            } else {
              for (MCPResource resource : resources) {
                sb.append("- URI: ").append(resource.getUri()).append("\n");
                sb.append("  Name: ").append(resource.getName()).append("\n");
                if (resource.getDescription() != null && !resource.getDescription().isEmpty()) {
                  sb.append("  Description: ").append(resource.getDescription()).append("\n");
                }
                sb.append("\n");
              }
            }
          } catch (Exception e) {
            sb.append("Error listing resources: ").append(e.getMessage()).append("\n");
          }

          return sb.toString();
        });

    // =======================================================
    // Example 5: AI-powered tool exploration with 'everything' server
    // =======================================================

    Flow<String, String, Void> toolExplorerFlow = genkit.defineFlow("toolExplorer", String.class, String.class,
        (ctx, query) -> {
          logger.info("Tool explorer processing: {}", query);

          List<Tool<?, ?>> mcpTools = mcpPlugin.getTools();

          ModelResponse response = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o-mini")
              .system("You are a helpful assistant that can use various tools. "
                  + "You have access to tools from multiple MCP servers including 'filesystem' and 'everything'. "
                  + "Use the appropriate tools to help the user with their request. "
                  + "Explain what tools you're using and why.")
              .prompt(query).tools(mcpTools)
              .config(GenerationConfig.builder().temperature(0.7).maxOutputTokens(1000).build()).build());

          return response.getText();
        });

    // =======================================================
    // Example 6: Get MCP server status
    // =======================================================

    Flow<Void, String, Void> serverStatusFlow = genkit.defineFlow("mcpStatus", Void.class, String.class,
        (ctx, input) -> {
          StringBuilder sb = new StringBuilder();
          sb.append("=== MCP Server Status ===\n\n");

          Map<String, MCPClient> clients = mcpPlugin.getClients();
          for (Map.Entry<String, MCPClient> entry : clients.entrySet()) {
            String serverName = entry.getKey();
            MCPClient client = entry.getValue();

            sb.append("Server: ").append(serverName).append("\n");
            sb.append("  Connected: ").append(client.isConnected()).append("\n");

            if (client.isConnected()) {
              try {
                List<Tool<?, ?>> tools = mcpPlugin.getTools(serverName);
                sb.append("  Tools: ").append(tools.size()).append("\n");
              } catch (Exception e) {
                sb.append("  Tools: Error - ").append(e.getMessage()).append("\n");
              }

              try {
                List<MCPResource> resources = mcpPlugin.getResources(serverName);
                sb.append("  Resources: ").append(resources.size()).append("\n");
              } catch (Exception e) {
                sb.append("  Resources: Error - ").append(e.getMessage()).append("\n");
              }
            }
            sb.append("\n");
          }

          return sb.toString();
        });

    // =======================================================
    // Example 7: Write and read file demo
    // =======================================================

    Flow<String, String, Void> writeReadDemoFlow = genkit.defineFlow("writeReadDemo", String.class, String.class,
        (ctx, content) -> {
          String testFile = allowedDir + "/genkit-mcp-test.txt";
          StringBuilder sb = new StringBuilder();

          try {
            // Write content
            sb.append("Writing to file: ").append(testFile).append("\n");
            mcpPlugin.callTool("filesystem", "write_file", Map.of("path", testFile, "content", content));
            sb.append("Write successful!\n\n");

            // Read it back
            sb.append("Reading file back:\n");
            Object readResult = mcpPlugin.callTool("filesystem", "read_file", Map.of("path", testFile));
            sb.append(readResult != null ? readResult.toString() : "(empty)");

          } catch (Exception e) {
            sb.append("Error: ").append(e.getMessage());
          }

          return sb.toString();
        });

    // =======================================================
    // Print usage information
    // =======================================================

    logger.info("\n========================================");
    logger.info("Genkit MCP Sample Started!");
    logger.info("========================================\n");

    logger.info("Available flows:");
    logger.info("  - listMcpTools: List all available MCP tools");
    logger.info("  - fileAssistant: AI-powered file operations assistant");
    logger.info("  - readFile: Read a file using MCP filesystem tool");
    logger.info("  - listResources: List resources from an MCP server");
    logger.info("  - toolExplorer: AI assistant with all MCP tools");
    logger.info("  - mcpStatus: Get status of all MCP servers");
    logger.info("  - writeReadDemo: Demo writing and reading a file\n");

    logger.info("Server running on http://localhost:8080");
    logger.info("Reflection server running on http://localhost:3100");
    logger.info("\nExample requests:");
    logger.info("  curl -X POST http://localhost:8080/listMcpTools -H 'Content-Type: application/json' -d 'null'");
    logger.info(
        "  curl -X POST http://localhost:8080/fileAssistant -H 'Content-Type: application/json' -d '\"List files in the temp directory\"'");
    logger.info(
        "  curl -X POST http://localhost:8080/readFile -H 'Content-Type: application/json' -d '\"/tmp/test.txt\"'");
    logger.info(
        "  curl -X POST http://localhost:8080/listResources -H 'Content-Type: application/json' -d '\"filesystem\"'");
    logger.info(
        "  curl -X POST http://localhost:8080/toolExplorer -H 'Content-Type: application/json' -d '\"Generate a random number\"'");
    logger.info("  curl -X POST http://localhost:8080/mcpStatus -H 'Content-Type: application/json' -d 'null'");
    logger.info(
        "  curl -X POST http://localhost:8080/writeReadDemo -H 'Content-Type: application/json' -d '\"Hello from Genkit MCP!\"'");

    // Add shutdown hook to cleanup MCP connections
    Runtime.getRuntime().addShutdownHook(new Thread(() -> {
      logger.info("Shutting down...");
      mcpPlugin.disconnect();
    }));
  }
}
