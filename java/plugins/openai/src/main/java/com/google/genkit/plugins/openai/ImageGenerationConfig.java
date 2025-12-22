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

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Configuration options for OpenAI image generation models (DALL-E, gpt-image).
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ImageGenerationConfig {

  /**
   * Size of the generated image. For DALL-E 3: "1024x1024", "1792x1024",
   * "1024x1792" For DALL-E 2: "256x256", "512x512", "1024x1024" For gpt-image-1:
   * "1024x1024", "1536x1024", "1024x1536", "auto"
   */
  @JsonProperty("size")
  private String size;

  /**
   * Image quality: "standard" or "hd" (DALL-E 3 only). For gpt-image-1: "low",
   * "medium", "high"
   */
  @JsonProperty("quality")
  private String quality;

  /**
   * Image style: "vivid" or "natural" (DALL-E 3 only).
   */
  @JsonProperty("style")
  private String style;

  /**
   * Number of images to generate (1-10). Default is 1.
   */
  @JsonProperty("n")
  private Integer n;

  /**
   * Response format: "url" or "b64_json". Default is "b64_json".
   */
  @JsonProperty("responseFormat")
  private String responseFormat;

  /**
   * User identifier for abuse monitoring.
   */
  @JsonProperty("user")
  private String user;

  /**
   * Background setting for gpt-image-1: "transparent", "opaque", "auto".
   */
  @JsonProperty("background")
  private String background;

  /**
   * Output format for gpt-image-1: "png", "jpeg", "webp".
   */
  @JsonProperty("outputFormat")
  private String outputFormat;

  /**
   * Output compression for gpt-image-1 (1-100).
   */
  @JsonProperty("outputCompression")
  private Integer outputCompression;

  /**
   * Moderation level for gpt-image-1: "low", "auto".
   */
  @JsonProperty("moderation")
  private String moderation;

  /**
   * Default constructor.
   */
  public ImageGenerationConfig() {
  }

  /**
   * Creates a builder for ImageGenerationConfig.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  // Getters and setters

  public String getSize() {
    return size;
  }

  public void setSize(String size) {
    this.size = size;
  }

  public String getQuality() {
    return quality;
  }

  public void setQuality(String quality) {
    this.quality = quality;
  }

  public String getStyle() {
    return style;
  }

  public void setStyle(String style) {
    this.style = style;
  }

  public Integer getN() {
    return n;
  }

  public void setN(Integer n) {
    this.n = n;
  }

  public String getResponseFormat() {
    return responseFormat;
  }

  public void setResponseFormat(String responseFormat) {
    this.responseFormat = responseFormat;
  }

  public String getUser() {
    return user;
  }

  public void setUser(String user) {
    this.user = user;
  }

  public String getBackground() {
    return background;
  }

  public void setBackground(String background) {
    this.background = background;
  }

  public String getOutputFormat() {
    return outputFormat;
  }

  public void setOutputFormat(String outputFormat) {
    this.outputFormat = outputFormat;
  }

  public Integer getOutputCompression() {
    return outputCompression;
  }

  public void setOutputCompression(Integer outputCompression) {
    this.outputCompression = outputCompression;
  }

  public String getModeration() {
    return moderation;
  }

  public void setModeration(String moderation) {
    this.moderation = moderation;
  }

  /**
   * Builder for ImageGenerationConfig.
   */
  public static class Builder {
    private final ImageGenerationConfig config = new ImageGenerationConfig();

    public Builder size(String size) {
      config.size = size;
      return this;
    }

    public Builder quality(String quality) {
      config.quality = quality;
      return this;
    }

    public Builder style(String style) {
      config.style = style;
      return this;
    }

    public Builder n(Integer n) {
      config.n = n;
      return this;
    }

    public Builder responseFormat(String responseFormat) {
      config.responseFormat = responseFormat;
      return this;
    }

    public Builder user(String user) {
      config.user = user;
      return this;
    }

    public Builder background(String background) {
      config.background = background;
      return this;
    }

    public Builder outputFormat(String outputFormat) {
      config.outputFormat = outputFormat;
      return this;
    }

    public Builder outputCompression(Integer outputCompression) {
      config.outputCompression = outputCompression;
      return this;
    }

    public Builder moderation(String moderation) {
      config.moderation = moderation;
      return this;
    }

    public ImageGenerationConfig build() {
      return config;
    }
  }
}
