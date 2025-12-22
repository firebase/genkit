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
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Configuration options for the MCP plugin.
 *
 * <p>
 * This class allows configuration of MCP server connections, including:
 * <ul>
 * <li>Multiple MCP servers with different transports (STDIO, HTTP)</li>
 * <li>Connection timeouts and retry settings</li>
 * <li>Raw tool response handling</li>
 * </ul>
 *
 * <p>
 * Example usage:
 *
 * <pre>{@code
 * MCPPluginOptions options = MCPPluginOptions.builder().name("my-mcp-host")
 * 		.addServer("filesystem",
 * 				MCPServerConfig.stdio("npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"))
 * 		.addServer("weather", MCPServerConfig.http("http://localhost:3001/mcp"))
 * 		.requestTimeout(Duration.ofSeconds(30)).build();
 * }</pre>
 */
public class MCPPluginOptions {

  private final String name;
  private final Map<String, MCPServerConfig> servers;
  private final Duration requestTimeout;
  private final boolean rawToolResponses;

  private MCPPluginOptions(Builder builder) {
    this.name = builder.name;
    this.servers = Collections.unmodifiableMap(new HashMap<>(builder.servers));
    this.requestTimeout = builder.requestTimeout;
    this.rawToolResponses = builder.rawToolResponses;
  }

  /**
   * Creates a new builder for MCPPluginOptions.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  /**
   * Gets the name of the MCP host.
   *
   * @return the host name
   */
  public String getName() {
    return name;
  }

  /**
   * Gets the configured MCP servers.
   *
   * @return map of server name to configuration
   */
  public Map<String, MCPServerConfig> getServers() {
    return servers;
  }

  /**
   * Gets the request timeout.
   *
   * @return the request timeout
   */
  public Duration getRequestTimeout() {
    return requestTimeout;
  }

  /**
   * Whether to return raw MCP tool responses.
   *
   * @return true if raw responses should be returned
   */
  public boolean isRawToolResponses() {
    return rawToolResponses;
  }

  /**
   * Builder for MCPPluginOptions.
   */
  public static class Builder {

    private String name = "genkit-mcp";
    private Map<String, MCPServerConfig> servers = new HashMap<>();
    private Duration requestTimeout = Duration.ofSeconds(30);
    private boolean rawToolResponses = false;

    /**
     * Sets the name of the MCP host.
     *
     * @param name
     *            the host name
     * @return this builder
     */
    public Builder name(String name) {
      this.name = name;
      return this;
    }

    /**
     * Adds an MCP server configuration.
     *
     * @param serverName
     *            the name to identify this server
     * @param config
     *            the server configuration
     * @return this builder
     */
    public Builder addServer(String serverName, MCPServerConfig config) {
      this.servers.put(serverName, config);
      return this;
    }

    /**
     * Sets all MCP server configurations at once.
     *
     * @param servers
     *            map of server name to configuration
     * @return this builder
     */
    public Builder servers(Map<String, MCPServerConfig> servers) {
      this.servers = new HashMap<>(servers);
      return this;
    }

    /**
     * Sets the request timeout for MCP operations.
     *
     * @param timeout
     *            the timeout duration
     * @return this builder
     */
    public Builder requestTimeout(Duration timeout) {
      this.requestTimeout = timeout;
      return this;
    }

    /**
     * Sets whether to return raw MCP tool responses.
     *
     * <p>
     * When true, tool responses are returned in their raw MCP format. When false
     * (default), responses are processed for better Genkit compatibility.
     *
     * @param rawToolResponses
     *            true to return raw responses
     * @return this builder
     */
    public Builder rawToolResponses(boolean rawToolResponses) {
      this.rawToolResponses = rawToolResponses;
      return this;
    }

    /**
     * Builds the MCPPluginOptions.
     *
     * @return the built options
     */
    public MCPPluginOptions build() {
      return new MCPPluginOptions(this);
    }
  }
}
