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
 * Response from an evaluator for a single test case.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class EvalResponse {

  /**
   * Index of this sample in the batch (optional).
   */
  @JsonProperty("sampleIndex")
  private Integer sampleIndex;

  /**
   * The test case ID that was evaluated.
   */
  @JsonProperty("testCaseId")
  private String testCaseId;

  /**
   * The trace ID associated with this evaluation.
   */
  @JsonProperty("traceId")
  private String traceId;

  /**
   * The span ID within the trace.
   */
  @JsonProperty("spanId")
  private String spanId;

  /**
   * The evaluation score(s). Can be a single Score or a list of Scores for
   * multi-metric evaluators.
   */
  @JsonProperty("evaluation")
  private Object evaluation;

  public EvalResponse() {
  }

  private EvalResponse(Builder builder) {
    this.sampleIndex = builder.sampleIndex;
    this.testCaseId = builder.testCaseId;
    this.traceId = builder.traceId;
    this.spanId = builder.spanId;
    this.evaluation = builder.evaluation;
  }

  public static Builder builder() {
    return new Builder();
  }

  public Integer getSampleIndex() {
    return sampleIndex;
  }

  public void setSampleIndex(Integer sampleIndex) {
    this.sampleIndex = sampleIndex;
  }

  public String getTestCaseId() {
    return testCaseId;
  }

  public void setTestCaseId(String testCaseId) {
    this.testCaseId = testCaseId;
  }

  public String getTraceId() {
    return traceId;
  }

  public void setTraceId(String traceId) {
    this.traceId = traceId;
  }

  public String getSpanId() {
    return spanId;
  }

  public void setSpanId(String spanId) {
    this.spanId = spanId;
  }

  public Object getEvaluation() {
    return evaluation;
  }

  /**
   * Gets the evaluation as a single Score.
   * 
   * @return the score, or null if the evaluation is a list
   */
  public Score getEvaluationAsScore() {
    if (evaluation instanceof Score) {
      return (Score) evaluation;
    }
    return null;
  }

  /**
   * Gets the evaluation as a list of Scores.
   * 
   * @return the list of scores, or null if the evaluation is a single score
   */
  @SuppressWarnings("unchecked")
  public List<Score> getEvaluationAsScoreList() {
    if (evaluation instanceof List) {
      return (List<Score>) evaluation;
    }
    return null;
  }

  public void setEvaluation(Object evaluation) {
    this.evaluation = evaluation;
  }

  public static class Builder {
    private Integer sampleIndex;
    private String testCaseId;
    private String traceId;
    private String spanId;
    private Object evaluation;

    public Builder sampleIndex(Integer sampleIndex) {
      this.sampleIndex = sampleIndex;
      return this;
    }

    public Builder testCaseId(String testCaseId) {
      this.testCaseId = testCaseId;
      return this;
    }

    public Builder traceId(String traceId) {
      this.traceId = traceId;
      return this;
    }

    public Builder spanId(String spanId) {
      this.spanId = spanId;
      return this;
    }

    public Builder evaluation(Score evaluation) {
      this.evaluation = evaluation;
      return this;
    }

    public Builder evaluation(List<Score> evaluation) {
      this.evaluation = evaluation;
      return this;
    }

    public EvalResponse build() {
      return new EvalResponse(this);
    }
  }
}
