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

package com.google.genkit.core;

import java.util.Map;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * ActionDesc is a descriptor of an action containing its metadata and schemas.
 * This is used for reflection and discovery of actions.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ActionDesc {

  @JsonProperty("type")
  private ActionType type;

  @JsonProperty("key")
  private String key;

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
   * Default constructor for Jackson deserialization.
   */
  public ActionDesc() {
  }

  /**
   * Creates a new ActionDesc with the specified parameters.
   *
   * @param type
   *            the action type
   * @param name
   *            the action name
   * @param description
   *            optional description
   * @param inputSchema
   *            optional input JSON schema
   * @param outputSchema
   *            optional output JSON schema
   * @param metadata
   *            optional metadata
   */
  public ActionDesc(ActionType type, String name, String description, Map<String, Object> inputSchema,
      Map<String, Object> outputSchema, Map<String, Object> metadata) {
    this.type = type;
    this.key = type.keyFromName(name);
    this.name = name;
    this.description = description;
    this.inputSchema = inputSchema;
    this.outputSchema = outputSchema;
    this.metadata = metadata;
  }

  /**
   * Creates a builder for ActionDesc.
   *
   * @return a new builder instance
   */
  public static Builder builder() {
    return new Builder();
  }

  // Getters and setters

  public ActionType getType() {
    return type;
  }

  public void setType(ActionType type) {
    this.type = type;
  }

  public String getKey() {
    return key;
  }

  public void setKey(String key) {
    this.key = key;
  }

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

  /**
   * Builder for ActionDesc.
   */
  public static class Builder {
    private ActionType type;
    private String name;
    private String description;
    private Map<String, Object> inputSchema;
    private Map<String, Object> outputSchema;
    private Map<String, Object> metadata;

    public Builder type(ActionType type) {
      this.type = type;
      return this;
    }

    public Builder name(String name) {
      this.name = name;
      return this;
    }

    public Builder description(String description) {
      this.description = description;
      return this;
    }

    public Builder inputSchema(Map<String, Object> inputSchema) {
      this.inputSchema = inputSchema;
      return this;
    }

    public Builder outputSchema(Map<String, Object> outputSchema) {
      this.outputSchema = outputSchema;
      return this;
    }

    public Builder metadata(Map<String, Object> metadata) {
      this.metadata = metadata;
      return this;
    }

    public ActionDesc build() {
      if (type == null) {
        throw new IllegalStateException("type is required");
      }
      if (name == null || name.isEmpty()) {
        throw new IllegalStateException("name is required");
      }
      return new ActionDesc(type, name, description, inputSchema, outputSchema, metadata);
    }
  }
}
