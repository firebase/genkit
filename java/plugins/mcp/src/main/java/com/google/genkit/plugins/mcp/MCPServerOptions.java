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

/**
 * Configuration options for an MCP server.
 *
 * <p>
 * Example usage:
 *
 * <pre>{@code
 * MCPServerOptions options = MCPServerOptions.builder().name("my-genkit-server").version("1.0.0").build();
 * }</pre>
 */
public class MCPServerOptions {

  private final String name;
  private final String version;

  private MCPServerOptions(Builder builder) {
    this.name = builder.name;
    this.version = builder.version;
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
   * Gets the server name.
   *
   * @return the server name
   */
  public String getName() {
    return name;
  }

  /**
   * Gets the server version.
   *
   * @return the server version
   */
  public String getVersion() {
    return version;
  }

  /**
   * Builder for MCPServerOptions.
   */
  public static class Builder {

    private String name = "genkit-mcp-server";
    private String version = "1.0.0";

    /**
     * Sets the server name.
     *
     * @param name
     *            the server name
     * @return this builder
     */
    public Builder name(String name) {
      this.name = name;
      return this;
    }

    /**
     * Sets the server version.
     *
     * @param version
     *            the server version
     * @return this builder
     */
    public Builder version(String version) {
      this.version = version;
      return this;
    }

    /**
     * Builds the MCPServerOptions.
     *
     * @return the built options
     */
    public MCPServerOptions build() {
      return new MCPServerOptions(this);
    }
  }
}
