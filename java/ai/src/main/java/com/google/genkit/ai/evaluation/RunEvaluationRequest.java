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

import java.util.List;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Request to run a new evaluation.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class RunEvaluationRequest {

  /**
   * The data source for evaluation.
   */
  @JsonProperty("dataSource")
  private DataSource dataSource;

  /**
   * The action to evaluate (e.g., "/flow/myFlow").
   */
  @JsonProperty("targetAction")
  private String targetAction;

  /**
   * The evaluators to run.
   */
  @JsonProperty("evaluators")
  private List<String> evaluators;

  /**
   * Options for the evaluation.
   */
  @JsonProperty("options")
  private EvaluationOptions options;

  public RunEvaluationRequest() {
  }

  private RunEvaluationRequest(Builder builder) {
    this.dataSource = builder.dataSource;
    this.targetAction = builder.targetAction;
    this.evaluators = builder.evaluators;
    this.options = builder.options;
  }

  public static Builder builder() {
    return new Builder();
  }

  public DataSource getDataSource() {
    return dataSource;
  }

  public void setDataSource(DataSource dataSource) {
    this.dataSource = dataSource;
  }

  public String getTargetAction() {
    return targetAction;
  }

  public void setTargetAction(String targetAction) {
    this.targetAction = targetAction;
  }

  public List<String> getEvaluators() {
    return evaluators;
  }

  public void setEvaluators(List<String> evaluators) {
    this.evaluators = evaluators;
  }

  public EvaluationOptions getOptions() {
    return options;
  }

  public void setOptions(EvaluationOptions options) {
    this.options = options;
  }

  /**
   * Data source for evaluation - either a dataset ID or inline data.
   */
  @JsonInclude(JsonInclude.Include.NON_NULL)
  public static class DataSource {
    @JsonProperty("datasetId")
    private String datasetId;

    @JsonProperty("data")
    private List<DatasetSample> data;

    public DataSource() {
    }

    public String getDatasetId() {
      return datasetId;
    }

    public void setDatasetId(String datasetId) {
      this.datasetId = datasetId;
    }

    public List<DatasetSample> getData() {
      return data;
    }

    public void setData(List<DatasetSample> data) {
      this.data = data;
    }
  }

  /**
   * Options for evaluation.
   */
  @JsonInclude(JsonInclude.Include.NON_NULL)
  public static class EvaluationOptions {
    @JsonProperty("context")
    private String context;

    @JsonProperty("actionConfig")
    private Object actionConfig;

    @JsonProperty("batchSize")
    private Integer batchSize;

    public EvaluationOptions() {
    }

    public String getContext() {
      return context;
    }

    public void setContext(String context) {
      this.context = context;
    }

    public Object getActionConfig() {
      return actionConfig;
    }

    public void setActionConfig(Object actionConfig) {
      this.actionConfig = actionConfig;
    }

    public Integer getBatchSize() {
      return batchSize;
    }

    public void setBatchSize(Integer batchSize) {
      this.batchSize = batchSize;
    }
  }

  public static class Builder {
    private DataSource dataSource;
    private String targetAction;
    private List<String> evaluators;
    private EvaluationOptions options;

    public Builder dataSource(DataSource dataSource) {
      this.dataSource = dataSource;
      return this;
    }

    public Builder targetAction(String targetAction) {
      this.targetAction = targetAction;
      return this;
    }

    public Builder evaluators(List<String> evaluators) {
      this.evaluators = evaluators;
      return this;
    }

    public Builder options(EvaluationOptions options) {
      this.options = options;
      return this;
    }

    public RunEvaluationRequest build() {
      return new RunEvaluationRequest(this);
    }
  }
}
