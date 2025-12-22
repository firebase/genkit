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
import java.util.Set;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * ModelInfo contains metadata about a model's capabilities.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ModelInfo {

  @JsonProperty("label")
  private String label;

  @JsonProperty("supports")
  private ModelCapabilities supports;

  @JsonProperty("versions")
  private List<String> versions;

  /**
   * Default constructor.
   */
  public ModelInfo() {
  }

  // Getters and setters

  public String getLabel() {
    return label;
  }

  public void setLabel(String label) {
    this.label = label;
  }

  public ModelCapabilities getSupports() {
    return supports;
  }

  public void setSupports(ModelCapabilities supports) {
    this.supports = supports;
  }

  public List<String> getVersions() {
    return versions;
  }

  public void setVersions(List<String> versions) {
    this.versions = versions;
  }

  /**
   * ModelCapabilities describes what a model can do.
   */
  @JsonInclude(JsonInclude.Include.NON_NULL)
  public static class ModelCapabilities {

    @JsonProperty("multiturn")
    private Boolean multiturn;

    @JsonProperty("media")
    private Boolean media;

    @JsonProperty("tools")
    private Boolean tools;

    @JsonProperty("systemRole")
    private Boolean systemRole;

    @JsonProperty("output")
    private Set<String> output;

    @JsonProperty("context")
    private Boolean context;

    @JsonProperty("contextCaching")
    private Boolean contextCaching;

    // Getters and setters

    public Boolean getMultiturn() {
      return multiturn;
    }

    public void setMultiturn(Boolean multiturn) {
      this.multiturn = multiturn;
    }

    public Boolean getMedia() {
      return media;
    }

    public void setMedia(Boolean media) {
      this.media = media;
    }

    public Boolean getTools() {
      return tools;
    }

    public void setTools(Boolean tools) {
      this.tools = tools;
    }

    public Boolean getSystemRole() {
      return systemRole;
    }

    public void setSystemRole(Boolean systemRole) {
      this.systemRole = systemRole;
    }

    public Set<String> getOutput() {
      return output;
    }

    public void setOutput(Set<String> output) {
      this.output = output;
    }

    public Boolean getContext() {
      return context;
    }

    public void setContext(Boolean context) {
      this.context = context;
    }

    public Boolean getContextCaching() {
      return contextCaching;
    }

    public void setContextCaching(Boolean contextCaching) {
      this.contextCaching = contextCaching;
    }
  }
}
