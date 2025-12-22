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

package com.google.genkit.ai;

import java.util.Map;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * GenerationConfig contains configuration for model generation.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class GenerationConfig {

  @JsonProperty("temperature")
  private Double temperature;

  @JsonProperty("maxOutputTokens")
  private Integer maxOutputTokens;

  @JsonProperty("topK")
  private Integer topK;

  @JsonProperty("topP")
  private Double topP;

  @JsonProperty("stopSequences")
  private String[] stopSequences;

  @JsonProperty("presencePenalty")
  private Double presencePenalty;

  @JsonProperty("frequencyPenalty")
  private Double frequencyPenalty;

  @JsonProperty("seed")
  private Integer seed;

  @JsonProperty("custom")
  private Map<String, Object> custom;

  /**
   * Default constructor.
   */
  public GenerationConfig() {
  }

  /**
   * Builder pattern for GenerationConfig.
   */
  public static Builder builder() {
    return new Builder();
  }

  // Getters and setters

  public Double getTemperature() {
    return temperature;
  }

  public void setTemperature(Double temperature) {
    this.temperature = temperature;
  }

  public Integer getMaxOutputTokens() {
    return maxOutputTokens;
  }

  public void setMaxOutputTokens(Integer maxOutputTokens) {
    this.maxOutputTokens = maxOutputTokens;
  }

  public Integer getTopK() {
    return topK;
  }

  public void setTopK(Integer topK) {
    this.topK = topK;
  }

  public Double getTopP() {
    return topP;
  }

  public void setTopP(Double topP) {
    this.topP = topP;
  }

  public String[] getStopSequences() {
    return stopSequences;
  }

  public void setStopSequences(String[] stopSequences) {
    this.stopSequences = stopSequences;
  }

  public Double getPresencePenalty() {
    return presencePenalty;
  }

  public void setPresencePenalty(Double presencePenalty) {
    this.presencePenalty = presencePenalty;
  }

  public Double getFrequencyPenalty() {
    return frequencyPenalty;
  }

  public void setFrequencyPenalty(Double frequencyPenalty) {
    this.frequencyPenalty = frequencyPenalty;
  }

  public Integer getSeed() {
    return seed;
  }

  public void setSeed(Integer seed) {
    this.seed = seed;
  }

  public Map<String, Object> getCustom() {
    return custom;
  }

  public void setCustom(Map<String, Object> custom) {
    this.custom = custom;
  }

  /**
   * Builder for GenerationConfig.
   */
  public static class Builder {
    private final GenerationConfig config = new GenerationConfig();

    public Builder temperature(Double temperature) {
      config.temperature = temperature;
      return this;
    }

    public Builder maxOutputTokens(Integer maxOutputTokens) {
      config.maxOutputTokens = maxOutputTokens;
      return this;
    }

    public Builder topK(Integer topK) {
      config.topK = topK;
      return this;
    }

    public Builder topP(Double topP) {
      config.topP = topP;
      return this;
    }

    public Builder stopSequences(String... stopSequences) {
      config.stopSequences = stopSequences;
      return this;
    }

    public Builder presencePenalty(Double presencePenalty) {
      config.presencePenalty = presencePenalty;
      return this;
    }

    public Builder frequencyPenalty(Double frequencyPenalty) {
      config.frequencyPenalty = frequencyPenalty;
      return this;
    }

    public Builder seed(Integer seed) {
      config.seed = seed;
      return this;
    }

    public Builder custom(Map<String, Object> custom) {
      config.custom = custom;
      return this;
    }

    public GenerationConfig build() {
      return config;
    }
  }
}
