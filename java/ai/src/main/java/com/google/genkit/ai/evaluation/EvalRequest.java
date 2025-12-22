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
 * Request to run an evaluator on a dataset.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class EvalRequest {

  /**
   * The dataset to evaluate.
   */
  @JsonProperty("dataset")
  private List<EvalDataPoint> dataset;

  /**
   * Unique identifier for this evaluation run.
   */
  @JsonProperty("evalRunId")
  private String evalRunId;

  /**
   * Options for the evaluator.
   */
  @JsonProperty("options")
  private Object options;

  /**
   * Number of data points to process in each batch.
   */
  @JsonProperty("batchSize")
  private Integer batchSize;

  public EvalRequest() {
  }

  private EvalRequest(Builder builder) {
    this.dataset = builder.dataset;
    this.evalRunId = builder.evalRunId;
    this.options = builder.options;
    this.batchSize = builder.batchSize;
  }

  public static Builder builder() {
    return new Builder();
  }

  public List<EvalDataPoint> getDataset() {
    return dataset;
  }

  public void setDataset(List<EvalDataPoint> dataset) {
    this.dataset = dataset;
  }

  public String getEvalRunId() {
    return evalRunId;
  }

  public void setEvalRunId(String evalRunId) {
    this.evalRunId = evalRunId;
  }

  public Object getOptions() {
    return options;
  }

  public void setOptions(Object options) {
    this.options = options;
  }

  public Integer getBatchSize() {
    return batchSize;
  }

  public void setBatchSize(Integer batchSize) {
    this.batchSize = batchSize;
  }

  public static class Builder {
    private List<EvalDataPoint> dataset;
    private String evalRunId;
    private Object options;
    private Integer batchSize;

    public Builder dataset(List<EvalDataPoint> dataset) {
      this.dataset = dataset;
      return this;
    }

    public Builder evalRunId(String evalRunId) {
      this.evalRunId = evalRunId;
      return this;
    }

    public Builder options(Object options) {
      this.options = options;
      return this;
    }

    public Builder batchSize(Integer batchSize) {
      this.batchSize = batchSize;
      return this;
    }

    public EvalRequest build() {
      return new EvalRequest(this);
    }
  }
}
