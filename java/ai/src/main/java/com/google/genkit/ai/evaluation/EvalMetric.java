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
 * Represents a single metric score from an evaluator.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class EvalMetric {

  /**
   * Name of the evaluator that produced this metric.
   */
  @JsonProperty("evaluator")
  private String evaluator;

  /**
   * Optional ID for multi-score evaluators.
   */
  @JsonProperty("scoreId")
  private String scoreId;

  /**
   * The score value.
   */
  @JsonProperty("score")
  private Object score;

  /**
   * The evaluation status.
   */
  @JsonProperty("status")
  private EvalStatus status;

  /**
   * Reasoning/explanation for the score.
   */
  @JsonProperty("rationale")
  private String rationale;

  /**
   * Error message if evaluation failed.
   */
  @JsonProperty("error")
  private String error;

  /**
   * Trace ID associated with this evaluation.
   */
  @JsonProperty("traceId")
  private String traceId;

  /**
   * Span ID within the trace.
   */
  @JsonProperty("spanId")
  private String spanId;

  public EvalMetric() {
  }

  private EvalMetric(Builder builder) {
    this.evaluator = builder.evaluator;
    this.scoreId = builder.scoreId;
    this.score = builder.score;
    this.status = builder.status;
    this.rationale = builder.rationale;
    this.error = builder.error;
    this.traceId = builder.traceId;
    this.spanId = builder.spanId;
  }

  public static Builder builder() {
    return new Builder();
  }

  public String getEvaluator() {
    return evaluator;
  }

  public void setEvaluator(String evaluator) {
    this.evaluator = evaluator;
  }

  public String getScoreId() {
    return scoreId;
  }

  public void setScoreId(String scoreId) {
    this.scoreId = scoreId;
  }

  public Object getScore() {
    return score;
  }

  public void setScore(Object score) {
    this.score = score;
  }

  public EvalStatus getStatus() {
    return status;
  }

  public void setStatus(EvalStatus status) {
    this.status = status;
  }

  public String getRationale() {
    return rationale;
  }

  public void setRationale(String rationale) {
    this.rationale = rationale;
  }

  public String getError() {
    return error;
  }

  public void setError(String error) {
    this.error = error;
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

  public static class Builder {
    private String evaluator;
    private String scoreId;
    private Object score;
    private EvalStatus status;
    private String rationale;
    private String error;
    private String traceId;
    private String spanId;

    public Builder evaluator(String evaluator) {
      this.evaluator = evaluator;
      return this;
    }

    public Builder scoreId(String scoreId) {
      this.scoreId = scoreId;
      return this;
    }

    public Builder score(Object score) {
      this.score = score;
      return this;
    }

    public Builder status(EvalStatus status) {
      this.status = status;
      return this;
    }

    public Builder rationale(String rationale) {
      this.rationale = rationale;
      return this;
    }

    public Builder error(String error) {
      this.error = error;
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

    public EvalMetric build() {
      return new EvalMetric(this);
    }
  }
}
