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
 * Key that uniquely identifies an evaluation run.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class EvalRunKey {

  /**
   * The action that was evaluated.
   */
  @JsonProperty("actionRef")
  private String actionRef;

  /**
   * The dataset used for evaluation.
   */
  @JsonProperty("datasetId")
  private String datasetId;

  /**
   * The version of the dataset used.
   */
  @JsonProperty("datasetVersion")
  private Integer datasetVersion;

  /**
   * Unique identifier for this evaluation run.
   */
  @JsonProperty("evalRunId")
  private String evalRunId;

  /**
   * When the evaluation was created.
   */
  @JsonProperty("createdAt")
  private String createdAt;

  /**
   * Configuration used for the action.
   */
  @JsonProperty("actionConfig")
  private Object actionConfig;

  public EvalRunKey() {
  }

  private EvalRunKey(Builder builder) {
    this.actionRef = builder.actionRef;
    this.datasetId = builder.datasetId;
    this.datasetVersion = builder.datasetVersion;
    this.evalRunId = builder.evalRunId;
    this.createdAt = builder.createdAt;
    this.actionConfig = builder.actionConfig;
  }

  public static Builder builder() {
    return new Builder();
  }

  public String getActionRef() {
    return actionRef;
  }

  public void setActionRef(String actionRef) {
    this.actionRef = actionRef;
  }

  public String getDatasetId() {
    return datasetId;
  }

  public void setDatasetId(String datasetId) {
    this.datasetId = datasetId;
  }

  public Integer getDatasetVersion() {
    return datasetVersion;
  }

  public void setDatasetVersion(Integer datasetVersion) {
    this.datasetVersion = datasetVersion;
  }

  public String getEvalRunId() {
    return evalRunId;
  }

  public void setEvalRunId(String evalRunId) {
    this.evalRunId = evalRunId;
  }

  public String getCreatedAt() {
    return createdAt;
  }

  public void setCreatedAt(String createdAt) {
    this.createdAt = createdAt;
  }

  public Object getActionConfig() {
    return actionConfig;
  }

  public void setActionConfig(Object actionConfig) {
    this.actionConfig = actionConfig;
  }

  public static class Builder {
    private String actionRef;
    private String datasetId;
    private Integer datasetVersion;
    private String evalRunId;
    private String createdAt;
    private Object actionConfig;

    public Builder actionRef(String actionRef) {
      this.actionRef = actionRef;
      return this;
    }

    public Builder datasetId(String datasetId) {
      this.datasetId = datasetId;
      return this;
    }

    public Builder datasetVersion(Integer datasetVersion) {
      this.datasetVersion = datasetVersion;
      return this;
    }

    public Builder evalRunId(String evalRunId) {
      this.evalRunId = evalRunId;
      return this;
    }

    public Builder createdAt(String createdAt) {
      this.createdAt = createdAt;
      return this;
    }

    public Builder actionConfig(Object actionConfig) {
      this.actionConfig = actionConfig;
      return this;
    }

    public EvalRunKey build() {
      return new EvalRunKey(this);
    }
  }
}
