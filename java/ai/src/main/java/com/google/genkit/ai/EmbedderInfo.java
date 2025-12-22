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

import java.util.List;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * EmbedderInfo contains metadata about an embedder's capabilities.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class EmbedderInfo {

  @JsonProperty("label")
  private String label;

  @JsonProperty("dimensions")
  private Integer dimensions;

  @JsonProperty("supports")
  private EmbedderCapabilities supports;

  /**
   * Default constructor.
   */
  public EmbedderInfo() {
  }

  // Getters and setters

  public String getLabel() {
    return label;
  }

  public void setLabel(String label) {
    this.label = label;
  }

  public Integer getDimensions() {
    return dimensions;
  }

  public void setDimensions(Integer dimensions) {
    this.dimensions = dimensions;
  }

  public EmbedderCapabilities getSupports() {
    return supports;
  }

  public void setSupports(EmbedderCapabilities supports) {
    this.supports = supports;
  }

  /**
   * EmbedderCapabilities describes what an embedder can do.
   */
  @JsonInclude(JsonInclude.Include.NON_NULL)
  public static class EmbedderCapabilities {

    @JsonProperty("input")
    private List<String> input;

    public List<String> getInput() {
      return input;
    }

    public void setInput(List<String> input) {
      this.input = input;
    }
  }
}
