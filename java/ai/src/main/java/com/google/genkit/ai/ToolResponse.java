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
 * ToolResponse represents a response from a tool invocation.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ToolResponse {

  @JsonProperty("ref")
  private String ref;

  @JsonProperty("name")
  private String name;

  @JsonProperty("output")
  private Object output;

  @JsonProperty("metadata")
  private Map<String, Object> metadata;

  /**
   * Default constructor.
   */
  public ToolResponse() {
  }

  /**
   * Creates a ToolResponse with the given name and output.
   *
   * @param name
   *            the tool name
   * @param output
   *            the tool output
   */
  public ToolResponse(String name, Object output) {
    this.name = name;
    this.output = output;
  }

  /**
   * Creates a ToolResponse with the given ref, name and output.
   *
   * @param ref
   *            the reference ID
   * @param name
   *            the tool name
   * @param output
   *            the tool output
   */
  public ToolResponse(String ref, String name, Object output) {
    this.ref = ref;
    this.name = name;
    this.output = output;
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

  public Object getOutput() {
    return output;
  }

  public void setOutput(Object output) {
    this.output = output;
  }

  public Map<String, Object> getMetadata() {
    return metadata;
  }

  public void setMetadata(Map<String, Object> metadata) {
    this.metadata = metadata;
  }
}
