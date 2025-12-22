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

package com.google.genkit;

/**
 * GenkitOptions contains configuration options for Genkit.
 */
public class GenkitOptions {

  private final boolean devMode;
  private final int reflectionPort;
  private final String projectRoot;
  private final String promptDir;

  private GenkitOptions(Builder builder) {
    this.devMode = builder.devMode;
    this.reflectionPort = builder.reflectionPort;
    this.projectRoot = builder.projectRoot;
    this.promptDir = builder.promptDir;
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
   * Returns whether dev mode is enabled.
   *
   * @return true if dev mode is enabled
   */
  public boolean isDevMode() {
    return devMode;
  }

  /**
   * Returns the reflection server port.
   *
   * @return the port number
   */
  public int getReflectionPort() {
    return reflectionPort;
  }

  /**
   * Returns the project root directory.
   *
   * @return the project root path
   */
  public String getProjectRoot() {
    return projectRoot;
  }

  /**
   * Returns the prompt directory path (relative to resources or absolute).
   * Defaults to "/prompts" for loading from classpath resources.
   *
   * @return the prompt directory path
   */
  public String getPromptDir() {
    return promptDir;
  }

  /**
   * Builder for GenkitOptions.
   */
  public static class Builder {
    private boolean devMode = isDevModeFromEnv();
    private int reflectionPort = getReflectionPortFromEnv();
    private String projectRoot = System.getProperty("user.dir");
    private String promptDir = "/prompts";

    private static boolean isDevModeFromEnv() {
      String env = System.getenv("GENKIT_ENV");
      return "dev".equals(env) || env == null;
    }

    private static int getReflectionPortFromEnv() {
      String port = System.getenv("GENKIT_REFLECTION_PORT");
      if (port != null) {
        try {
          return Integer.parseInt(port);
        } catch (NumberFormatException e) {
          // fall through to default
        }
      }
      return 3100;
    }

    public Builder devMode(boolean devMode) {
      this.devMode = devMode;
      return this;
    }

    public Builder reflectionPort(int reflectionPort) {
      this.reflectionPort = reflectionPort;
      return this;
    }

    public Builder projectRoot(String projectRoot) {
      this.projectRoot = projectRoot;
      return this;
    }

    public Builder promptDir(String promptDir) {
      this.promptDir = promptDir;
      return this;
    }

    public GenkitOptions build() {
      return new GenkitOptions(this);
    }
  }
}
