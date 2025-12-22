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
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Configuration for connecting to an MCP server.
 *
 * <p>
 * Supports two transport types:
 * <ul>
 * <li>STDIO: Launches a local process and communicates via standard I/O</li>
 * <li>HTTP: Connects to a remote MCP server via HTTP/SSE</li>
 * </ul>
 *
 * <p>
 * Example usage:
 *
 * <pre>{@code
 * // STDIO transport - launch a local MCP server
 * MCPServerConfig filesystemServer = MCPServerConfig.stdio("npx", "-y", "@modelcontextprotocol/server-filesystem",
 * 		"/tmp");
 *
 * // HTTP transport - connect to remote server
 * MCPServerConfig remoteServer = MCPServerConfig.http("http://localhost:3001/mcp");
 *
 * // With environment variables
 * MCPServerConfig serverWithEnv = MCPServerConfig.builder().command("npx")
 * 		.args("-y", "@modelcontextprotocol/server-github").env("GITHUB_TOKEN", System.getenv("GITHUB_TOKEN"))
 * 		.build();
 * }</pre>
 */
public class MCPServerConfig {

  /**
   * Transport type for MCP communication.
   */
  public enum TransportType {
    /**
     * Standard I/O transport - launches a local process.
     */
    STDIO,
    /**
     * HTTP transport with SSE for streaming.
     */
    HTTP,
    /**
     * Streamable HTTP transport.
     */
    STREAMABLE_HTTP
  }

  private final TransportType transportType;
  private final String command;
  private final List<String> args;
  private final Map<String, String> env;
  private final String url;
  private final boolean disabled;

  private MCPServerConfig(Builder builder) {
    this.transportType = builder.transportType;
    this.command = builder.command;
    this.args = Collections.unmodifiableList(new ArrayList<>(builder.args));
    this.env = Collections.unmodifiableMap(new HashMap<>(builder.env));
    this.url = builder.url;
    this.disabled = builder.disabled;
  }

  /**
   * Creates a STDIO server configuration.
   *
   * @param command
   *            the command to execute
   * @param args
   *            arguments for the command
   * @return the server configuration
   */
  public static MCPServerConfig stdio(String command, String... args) {
    return builder().command(command).args(args).build();
  }

  /**
   * Creates an HTTP server configuration.
   *
   * @param url
   *            the server URL
   * @return the server configuration
   */
  public static MCPServerConfig http(String url) {
    return builder().url(url).transportType(TransportType.HTTP).build();
  }

  /**
   * Creates a Streamable HTTP server configuration.
   *
   * @param url
   *            the server URL
   * @return the server configuration
   */
  public static MCPServerConfig streamableHttp(String url) {
    return builder().url(url).transportType(TransportType.STREAMABLE_HTTP).build();
  }

  /**
   * Creates a new builder.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  /**
   * Gets the transport type.
   *
   * @return the transport type
   */
  public TransportType getTransportType() {
    return transportType;
  }

  /**
   * Gets the command for STDIO transport.
   *
   * @return the command, or null for HTTP transport
   */
  public String getCommand() {
    return command;
  }

  /**
   * Gets the command arguments.
   *
   * @return the arguments
   */
  public List<String> getArgs() {
    return args;
  }

  /**
   * Gets the environment variables.
   *
   * @return the environment variables
   */
  public Map<String, String> getEnv() {
    return env;
  }

  /**
   * Gets the URL for HTTP transport.
   *
   * @return the URL, or null for STDIO transport
   */
  public String getUrl() {
    return url;
  }

  /**
   * Whether this server is disabled.
   *
   * @return true if disabled
   */
  public boolean isDisabled() {
    return disabled;
  }

  /**
   * Builder for MCPServerConfig.
   */
  public static class Builder {

    private TransportType transportType = TransportType.STDIO;
    private String command;
    private List<String> args = new ArrayList<>();
    private Map<String, String> env = new HashMap<>();
    private String url;
    private boolean disabled = false;

    /**
     * Sets the transport type.
     *
     * @param transportType
     *            the transport type
     * @return this builder
     */
    public Builder transportType(TransportType transportType) {
      this.transportType = transportType;
      return this;
    }

    /**
     * Sets the command for STDIO transport.
     *
     * @param command
     *            the command to execute
     * @return this builder
     */
    public Builder command(String command) {
      this.command = command;
      this.transportType = TransportType.STDIO;
      return this;
    }

    /**
     * Sets the command arguments.
     *
     * @param args
     *            the arguments
     * @return this builder
     */
    public Builder args(String... args) {
      this.args = new ArrayList<>(Arrays.asList(args));
      return this;
    }

    /**
     * Sets the command arguments.
     *
     * @param args
     *            the arguments
     * @return this builder
     */
    public Builder args(List<String> args) {
      this.args = new ArrayList<>(args);
      return this;
    }

    /**
     * Adds an environment variable.
     *
     * @param key
     *            the variable name
     * @param value
     *            the variable value
     * @return this builder
     */
    public Builder env(String key, String value) {
      this.env.put(key, value);
      return this;
    }

    /**
     * Sets all environment variables.
     *
     * @param env
     *            the environment variables
     * @return this builder
     */
    public Builder env(Map<String, String> env) {
      this.env = new HashMap<>(env);
      return this;
    }

    /**
     * Sets the URL for HTTP transport.
     *
     * @param url
     *            the server URL
     * @return this builder
     */
    public Builder url(String url) {
      this.url = url;
      if (this.transportType == TransportType.STDIO) {
        this.transportType = TransportType.HTTP;
      }
      return this;
    }

    /**
     * Sets whether this server is disabled.
     *
     * @param disabled
     *            true to disable
     * @return this builder
     */
    public Builder disabled(boolean disabled) {
      this.disabled = disabled;
      return this;
    }

    /**
     * Builds the MCPServerConfig.
     *
     * @return the built configuration
     */
    public MCPServerConfig build() {
      if (transportType == TransportType.STDIO && command == null) {
        throw new IllegalStateException("Command is required for STDIO transport");
      }
      if ((transportType == TransportType.HTTP || transportType == TransportType.STREAMABLE_HTTP)
          && url == null) {
        throw new IllegalStateException("URL is required for HTTP transport");
      }
      return new MCPServerConfig(this);
    }
  }
}
