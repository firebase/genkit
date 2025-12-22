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
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * A single evaluation result combining input data with metric scores.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class EvalResult {

  /**
   * The test case ID.
   */
  @JsonProperty("testCaseId")
  private String testCaseId;

  /**
   * The input to the evaluated action.
   */
  @JsonProperty("input")
  private Object input;

  /**
   * The output from the evaluated action.
   */
  @JsonProperty("output")
  private Object output;

  /**
   * Error from the evaluated action.
   */
  @JsonProperty("error")
  private String error;

  /**
   * Context used during evaluation.
   */
  @JsonProperty("context")
  private List<Object> context;

  /**
   * Reference output for comparison.
   */
  @JsonProperty("reference")
  private Object reference;

  /**
   * Custom fields.
   */
  @JsonProperty("custom")
  private Map<String, Object> custom;

  /**
   * Trace IDs associated with this result.
   */
  @JsonProperty("traceIds")
  private List<String> traceIds;

  /**
   * Metrics from all evaluators.
   */
  @JsonProperty("metrics")
  private List<EvalMetric> metrics;

  public EvalResult() {
  }

  private EvalResult(Builder builder) {
    this.testCaseId = builder.testCaseId;
    this.input = builder.input;
    this.output = builder.output;
    this.error = builder.error;
    this.context = builder.context;
    this.reference = builder.reference;
    this.custom = builder.custom;
    this.traceIds = builder.traceIds;
    this.metrics = builder.metrics;
  }

  public static Builder builder() {
    return new Builder();
  }

  public String getTestCaseId() {
    return testCaseId;
  }

  public void setTestCaseId(String testCaseId) {
    this.testCaseId = testCaseId;
  }

  public Object getInput() {
    return input;
  }

  public void setInput(Object input) {
    this.input = input;
  }

  public Object getOutput() {
    return output;
  }

  public void setOutput(Object output) {
    this.output = output;
  }

  public String getError() {
    return error;
  }

  public void setError(String error) {
    this.error = error;
  }

  public List<Object> getContext() {
    return context;
  }

  public void setContext(List<Object> context) {
    this.context = context;
  }

  public Object getReference() {
    return reference;
  }

  public void setReference(Object reference) {
    this.reference = reference;
  }

  public Map<String, Object> getCustom() {
    return custom;
  }

  public void setCustom(Map<String, Object> custom) {
    this.custom = custom;
  }

  public List<String> getTraceIds() {
    return traceIds;
  }

  public void setTraceIds(List<String> traceIds) {
    this.traceIds = traceIds;
  }

  public List<EvalMetric> getMetrics() {
    return metrics;
  }

  public void setMetrics(List<EvalMetric> metrics) {
    this.metrics = metrics;
  }

  public static class Builder {
    private String testCaseId;
    private Object input;
    private Object output;
    private String error;
    private List<Object> context;
    private Object reference;
    private Map<String, Object> custom;
    private List<String> traceIds;
    private List<EvalMetric> metrics;

    public Builder testCaseId(String testCaseId) {
      this.testCaseId = testCaseId;
      return this;
    }

    public Builder input(Object input) {
      this.input = input;
      return this;
    }

    public Builder output(Object output) {
      this.output = output;
      return this;
    }

    public Builder error(String error) {
      this.error = error;
      return this;
    }

    public Builder context(List<Object> context) {
      this.context = context;
      return this;
    }

    public Builder reference(Object reference) {
      this.reference = reference;
      return this;
    }

    public Builder custom(Map<String, Object> custom) {
      this.custom = custom;
      return this;
    }

    public Builder traceIds(List<String> traceIds) {
      this.traceIds = traceIds;
      return this;
    }

    public Builder metrics(List<EvalMetric> metrics) {
      this.metrics = metrics;
      return this;
    }

    public EvalResult build() {
      return new EvalResult(this);
    }
  }
}
