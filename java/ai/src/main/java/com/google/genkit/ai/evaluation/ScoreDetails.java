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

package com.google.genkit.ai.evaluation;

import java.util.HashMap;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Details about an evaluation score, including reasoning.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ScoreDetails {

  @JsonProperty("reasoning")
  private String reasoning;

  /**
   * Additional properties that may be included in the details.
   */
  private Map<String, Object> additionalProperties = new HashMap<>();

  public ScoreDetails() {
  }

  private ScoreDetails(Builder builder) {
    this.reasoning = builder.reasoning;
    this.additionalProperties = builder.additionalProperties;
  }

  public static Builder builder() {
    return new Builder();
  }

  public String getReasoning() {
    return reasoning;
  }

  public void setReasoning(String reasoning) {
    this.reasoning = reasoning;
  }

  @JsonAnyGetter
  public Map<String, Object> getAdditionalProperties() {
    return additionalProperties;
  }

  @JsonAnySetter
  public void setAdditionalProperty(String name, Object value) {
    this.additionalProperties.put(name, value);
  }

  public static class Builder {
    private String reasoning;
    private Map<String, Object> additionalProperties = new HashMap<>();

    public Builder reasoning(String reasoning) {
      this.reasoning = reasoning;
      return this;
    }

    public Builder additionalProperty(String name, Object value) {
      this.additionalProperties.put(name, value);
      return this;
    }

    public ScoreDetails build() {
      return new ScoreDetails(this);
    }
  }
}
