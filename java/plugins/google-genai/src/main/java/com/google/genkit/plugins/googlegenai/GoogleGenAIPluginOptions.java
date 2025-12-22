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

package com.google.genkit.plugins.googlegenai;

import com.google.genai.types.HttpOptions;

/**
 * Options for configuring the Google GenAI plugin.
 *
 * <p>
 * The plugin can be configured to use either:
 * <ul>
 * <li>Gemini Developer API (default): Set the API key</li>
 * <li>Vertex AI API: Set project, location, and enable vertexAI</li>
 * </ul>
 */
public class GoogleGenAIPluginOptions {

  private final String apiKey;
  private final String project;
  private final String location;
  private final boolean vertexAI;
  private final String apiVersion;
  private final String baseUrl;
  private final int timeout;

  private GoogleGenAIPluginOptions(Builder builder) {
    this.apiKey = builder.apiKey;
    this.project = builder.project;
    this.location = builder.location;
    this.vertexAI = builder.vertexAI;
    this.apiVersion = builder.apiVersion;
    this.baseUrl = builder.baseUrl;
    this.timeout = builder.timeout;
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
   * Gets the API key.
   *
   * @return the API key
   */
  public String getApiKey() {
    return apiKey;
  }

  /**
   * Gets the Google Cloud project ID (for Vertex AI).
   *
   * @return the project ID
   */
  public String getProject() {
    return project;
  }

  /**
   * Gets the Google Cloud location (for Vertex AI).
   *
   * @return the location
   */
  public String getLocation() {
    return location;
  }

  /**
   * Returns whether to use Vertex AI backend.
   *
   * @return true if using Vertex AI, false for Gemini Developer API
   */
  public boolean isVertexAI() {
    return vertexAI;
  }

  /**
   * Gets the API version.
   *
   * @return the API version
   */
  public String getApiVersion() {
    return apiVersion;
  }

  /**
   * Gets the base URL override.
   *
   * @return the base URL
   */
  public String getBaseUrl() {
    return baseUrl;
  }

  /**
   * Gets the request timeout in milliseconds.
   *
   * @return the timeout in milliseconds
   */
  public int getTimeout() {
    return timeout;
  }

  /**
   * Converts these options to HttpOptions for the Google GenAI SDK.
   *
   * @return HttpOptions
   */
  public HttpOptions toHttpOptions() {
    HttpOptions.Builder builder = HttpOptions.builder();
    if (apiVersion != null) {
      builder.apiVersion(apiVersion);
    }
    if (baseUrl != null) {
      builder.baseUrl(baseUrl);
    }
    if (timeout > 0) {
      builder.timeout(timeout);
    }
    return builder.build();
  }

  /**
   * Builder for GoogleGenAIPluginOptions.
   */
  public static class Builder {
    private String apiKey = getApiKeyFromEnv();
    private String project = getProjectFromEnv();
    private String location = getLocationFromEnv();
    private boolean vertexAI = getVertexAIFromEnv();
    private String apiVersion;
    private String baseUrl;
    private int timeout = 600000; // 10 minutes default (in milliseconds)

    private static String getApiKeyFromEnv() {
      // GOOGLE_API_KEY takes precedence over GEMINI_API_KEY (legacy)
      String apiKey = System.getenv("GOOGLE_API_KEY");
      if (apiKey == null || apiKey.isEmpty()) {
        apiKey = System.getenv("GEMINI_API_KEY");
      }
      return apiKey;
    }

    private static String getProjectFromEnv() {
      return System.getenv("GOOGLE_CLOUD_PROJECT");
    }

    private static String getLocationFromEnv() {
      String location = System.getenv("GOOGLE_CLOUD_LOCATION");
      return location != null ? location : "us-central1";
    }

    private static boolean getVertexAIFromEnv() {
      String useVertexAI = System.getenv("GOOGLE_GENAI_USE_VERTEXAI");
      return "true".equalsIgnoreCase(useVertexAI);
    }

    /**
     * Sets the API key for Gemini Developer API.
     *
     * @param apiKey
     *            the API key
     * @return this builder
     */
    public Builder apiKey(String apiKey) {
      this.apiKey = apiKey;
      return this;
    }

    /**
     * Sets the Google Cloud project ID for Vertex AI.
     *
     * @param project
     *            the project ID
     * @return this builder
     */
    public Builder project(String project) {
      this.project = project;
      return this;
    }

    /**
     * Sets the Google Cloud location for Vertex AI.
     *
     * @param location
     *            the location
     * @return this builder
     */
    public Builder location(String location) {
      this.location = location;
      return this;
    }

    /**
     * Sets whether to use Vertex AI backend.
     *
     * @param vertexAI
     *            true to use Vertex AI, false for Gemini Developer API
     * @return this builder
     */
    public Builder vertexAI(boolean vertexAI) {
      this.vertexAI = vertexAI;
      return this;
    }

    /**
     * Sets the API version.
     *
     * @param apiVersion
     *            the API version (e.g., "v1", "v1beta")
     * @return this builder
     */
    public Builder apiVersion(String apiVersion) {
      this.apiVersion = apiVersion;
      return this;
    }

    /**
     * Sets the base URL override.
     *
     * @param baseUrl
     *            the base URL
     * @return this builder
     */
    public Builder baseUrl(String baseUrl) {
      this.baseUrl = baseUrl;
      return this;
    }

    /**
     * Sets the request timeout in milliseconds.
     *
     * @param timeout
     *            the timeout in milliseconds
     * @return this builder
     */
    public Builder timeout(int timeout) {
      this.timeout = timeout;
      return this;
    }

    /**
     * Builds the GoogleGenAIPluginOptions.
     *
     * @return the built options
     */
    public GoogleGenAIPluginOptions build() {
      // Validate configuration
      if (!vertexAI && (apiKey == null || apiKey.isEmpty())) {
        throw new IllegalStateException("Google API key is required for Gemini Developer API. "
            + "Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable, "
            + "or provide it in options, or enable vertexAI mode.");
      }
      if (vertexAI && (project == null || project.isEmpty()) && (apiKey == null || apiKey.isEmpty())) {
        throw new IllegalStateException(
            "For Vertex AI, either set GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION "
                + "environment variables, or provide an API key for express mode.");
      }
      return new GoogleGenAIPluginOptions(this);
    }
  }
}
