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

package com.google.genkit.plugins.openai;

/**
 * Options for configuring the OpenAI plugin.
 */
public class OpenAIPluginOptions {

  private final String apiKey;
  private final String baseUrl;
  private final String organization;
  private final int timeout;

  private OpenAIPluginOptions(Builder builder) {
    this.apiKey = builder.apiKey;
    this.baseUrl = builder.baseUrl;
    this.organization = builder.organization;
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
   * Gets the base URL for API requests.
   *
   * @return the base URL
   */
  public String getBaseUrl() {
    return baseUrl;
  }

  /**
   * Gets the organization ID.
   *
   * @return the organization ID
   */
  public String getOrganization() {
    return organization;
  }

  /**
   * Gets the request timeout in seconds.
   *
   * @return the timeout
   */
  public int getTimeout() {
    return timeout;
  }

  /**
   * Builder for OpenAIPluginOptions.
   */
  public static class Builder {
    private String apiKey = getApiKeyFromEnv();
    private String baseUrl = "https://api.openai.com/v1";
    private String organization;
    private int timeout = 60;

    private static String getApiKeyFromEnv() {
      return System.getenv("OPENAI_API_KEY");
    }

    public Builder apiKey(String apiKey) {
      this.apiKey = apiKey;
      return this;
    }

    public Builder baseUrl(String baseUrl) {
      this.baseUrl = baseUrl;
      return this;
    }

    public Builder organization(String organization) {
      this.organization = organization;
      return this;
    }

    public Builder timeout(int timeout) {
      this.timeout = timeout;
      return this;
    }

    public OpenAIPluginOptions build() {
      if (apiKey == null || apiKey.isEmpty()) {
        throw new IllegalStateException(
            "OpenAI API key is required. Set OPENAI_API_KEY environment variable or provide it in options.");
      }
      return new OpenAIPluginOptions(this);
    }
  }
}
