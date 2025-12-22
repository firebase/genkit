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
 * ToolDefinition describes a tool that can be used by a model.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ToolDefinition {

  @JsonProperty("name")
  private String name;

  @JsonProperty("description")
  private String description;

  @JsonProperty("inputSchema")
  private Map<String, Object> inputSchema;

  @JsonProperty("outputSchema")
  private Map<String, Object> outputSchema;

  @JsonProperty("metadata")
  private Map<String, Object> metadata;

  /**
   * Default constructor.
   */
  public ToolDefinition() {
  }

  /**
   * Creates a ToolDefinition with the given name and description.
   *
   * @param name
   *            the tool name
   * @param description
   *            the tool description
   */
  public ToolDefinition(String name, String description) {
    this.name = name;
    this.description = description;
  }

  /**
   * Creates a ToolDefinition with full parameters.
   *
   * @param name
   *            the tool name
   * @param description
   *            the tool description
   * @param inputSchema
   *            the input JSON schema
   * @param outputSchema
   *            the output JSON schema
   */
  public ToolDefinition(String name, String description, Map<String, Object> inputSchema,
      Map<String, Object> outputSchema) {
    this.name = name;
    this.description = description;
    this.inputSchema = inputSchema;
    this.outputSchema = outputSchema;
  }

  // Getters and setters

  public String getName() {
    return name;
  }

  public void setName(String name) {
    this.name = name;
  }

  public String getDescription() {
    return description;
  }

  public void setDescription(String description) {
    this.description = description;
  }

  public Map<String, Object> getInputSchema() {
    return inputSchema;
  }

  public void setInputSchema(Map<String, Object> inputSchema) {
    this.inputSchema = inputSchema;
  }

  public Map<String, Object> getOutputSchema() {
    return outputSchema;
  }

  public void setOutputSchema(Map<String, Object> outputSchema) {
    this.outputSchema = outputSchema;
  }

  public Map<String, Object> getMetadata() {
    return metadata;
  }

  public void setMetadata(Map<String, Object> metadata) {
    this.metadata = metadata;
  }
}
