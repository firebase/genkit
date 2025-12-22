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

package com.google.genkit.plugins.jetty;

/**
 * Options for configuring the Jetty plugin.
 */
public class JettyPluginOptions {

  private final int port;
  private final String host;
  private final String basePath;

  private JettyPluginOptions(Builder builder) {
    this.port = builder.port;
    this.host = builder.host;
    this.basePath = builder.basePath;
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
   * Gets the HTTP port.
   *
   * @return the port
   */
  public int getPort() {
    return port;
  }

  /**
   * Gets the host to bind to.
   *
   * @return the host
   */
  public String getHost() {
    return host;
  }

  /**
   * Gets the base path for flow endpoints.
   *
   * @return the base path
   */
  public String getBasePath() {
    return basePath;
  }

  /**
   * Builder for JettyPluginOptions.
   */
  public static class Builder {
    private int port = 8080;
    private String host = "0.0.0.0";
    private String basePath = "/api/flows";

    public Builder port(int port) {
      this.port = port;
      return this;
    }

    public Builder host(String host) {
      this.host = host;
      return this;
    }

    public Builder basePath(String basePath) {
      this.basePath = basePath;
      return this;
    }

    public JettyPluginOptions build() {
      return new JettyPluginOptions(this);
    }
  }
}
