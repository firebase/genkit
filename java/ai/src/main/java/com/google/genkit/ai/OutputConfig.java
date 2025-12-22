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
 * OutputConfig contains configuration for model output generation.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class OutputConfig {

  @JsonProperty("format")
  private OutputFormat format;

  @JsonProperty("schema")
  private Map<String, Object> schema;

  @JsonProperty("constrained")
  private Boolean constrained;

  @JsonProperty("contentType")
  private String contentType;

  @JsonProperty("instructions")
  private String instructions;

  /**
   * Default constructor.
   */
  public OutputConfig() {
  }

  /**
   * Creates an OutputConfig with the given format.
   *
   * @param format
   *            the output format
   */
  public OutputConfig(OutputFormat format) {
    this.format = format;
  }

  /**
   * Creates an OutputConfig for JSON output with schema.
   *
   * @param schema
   *            the JSON schema
   * @return an OutputConfig configured for JSON
   */
  public static OutputConfig json(Map<String, Object> schema) {
    OutputConfig config = new OutputConfig();
    config.format = OutputFormat.JSON;
    config.schema = schema;
    return config;
  }

  /**
   * Creates an OutputConfig for text output.
   *
   * @return an OutputConfig configured for text
   */
  public static OutputConfig text() {
    OutputConfig config = new OutputConfig();
    config.format = OutputFormat.TEXT;
    return config;
  }

  // Getters and setters

  public OutputFormat getFormat() {
    return format;
  }

  public void setFormat(OutputFormat format) {
    this.format = format;
  }

  public Map<String, Object> getSchema() {
    return schema;
  }

  public void setSchema(Map<String, Object> schema) {
    this.schema = schema;
  }

  public Boolean getConstrained() {
    return constrained;
  }

  public void setConstrained(Boolean constrained) {
    this.constrained = constrained;
  }

  public String getContentType() {
    return contentType;
  }

  public void setContentType(String contentType) {
    this.contentType = contentType;
  }

  public String getInstructions() {
    return instructions;
  }

  public void setInstructions(String instructions) {
    this.instructions = instructions;
  }
}
