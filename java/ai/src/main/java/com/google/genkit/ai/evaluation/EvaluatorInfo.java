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

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Information about an evaluator including display metadata and metrics.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class EvaluatorInfo {

  /**
   * Display name for the evaluator.
   */
  @JsonProperty("displayName")
  private String displayName;

  /**
   * Description of what the evaluator measures.
   */
  @JsonProperty("definition")
  private String definition;

  /**
   * Whether using this evaluator incurs costs (e.g., LLM API calls).
   */
  @JsonProperty("isBilled")
  private Boolean isBilled;

  public EvaluatorInfo() {
  }

  private EvaluatorInfo(Builder builder) {
    this.displayName = builder.displayName;
    this.definition = builder.definition;
    this.isBilled = builder.isBilled;
  }

  public static Builder builder() {
    return new Builder();
  }

  public String getDisplayName() {
    return displayName;
  }

  public void setDisplayName(String displayName) {
    this.displayName = displayName;
  }

  public String getDefinition() {
    return definition;
  }

  public void setDefinition(String definition) {
    this.definition = definition;
  }

  public Boolean getIsBilled() {
    return isBilled;
  }

  public void setIsBilled(Boolean isBilled) {
    this.isBilled = isBilled;
  }

  public static class Builder {
    private String displayName;
    private String definition;
    private Boolean isBilled;

    public Builder displayName(String displayName) {
      this.displayName = displayName;
      return this;
    }

    public Builder definition(String definition) {
      this.definition = definition;
      return this;
    }

    public Builder isBilled(Boolean isBilled) {
      this.isBilled = isBilled;
      return this;
    }

    public EvaluatorInfo build() {
      return new EvaluatorInfo(this);
    }
  }
}
