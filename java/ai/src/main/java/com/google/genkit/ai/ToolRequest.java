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
 * ToolRequest represents a request from the model to invoke a tool.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ToolRequest {

  @JsonProperty("ref")
  private String ref;

  @JsonProperty("name")
  private String name;

  @JsonProperty("input")
  private Object input;

  @JsonProperty("metadata")
  private Map<String, Object> metadata;

  /**
   * Default constructor.
   */
  public ToolRequest() {
  }

  /**
   * Creates a ToolRequest with the given name and input.
   *
   * @param name
   *            the tool name
   * @param input
   *            the tool input
   */
  public ToolRequest(String name, Object input) {
    this.name = name;
    this.input = input;
  }

  // Getters and setters

  public String getRef() {
    return ref;
  }

  public void setRef(String ref) {
    this.ref = ref;
  }

  public String getName() {
    return name;
  }

  public void setName(String name) {
    this.name = name;
  }

  public Object getInput() {
    return input;
  }

  public void setInput(Object input) {
    this.input = input;
  }

  public Map<String, Object> getMetadata() {
    return metadata;
  }

  public void setMetadata(Map<String, Object> metadata) {
    this.metadata = metadata;
  }
}
