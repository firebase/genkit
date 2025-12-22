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
 * Score represents the result of an evaluation.
 * 
 * <p>
 * A score can contain a numeric value, a string value, or a boolean value,
 * along with an optional status and detailed information about the evaluation.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Score {

  /**
   * Optional identifier to differentiate scores in multi-score evaluations.
   */
  @JsonProperty("id")
  private String id;

  /**
   * The numeric score value. Can be null if using string or boolean score.
   */
  @JsonProperty("score")
  private Object score;

  /**
   * The status of the evaluation (PASS, FAIL, UNKNOWN).
   */
  @JsonProperty("status")
  private EvalStatus status;

  /**
   * Error message if the evaluation failed.
   */
  @JsonProperty("error")
  private String error;

  /**
   * Additional details about the evaluation including reasoning.
   */
  @JsonProperty("details")
  private ScoreDetails details;

  public Score() {
  }

  private Score(Builder builder) {
    this.id = builder.id;
    this.score = builder.score;
    this.status = builder.status;
    this.error = builder.error;
    this.details = builder.details;
  }

  public static Builder builder() {
    return new Builder();
  }

  public String getId() {
    return id;
  }

  public void setId(String id) {
    this.id = id;
  }

  public Object getScore() {
    return score;
  }

  public void setScore(Object score) {
    this.score = score;
  }

  public Double getScoreAsDouble() {
    if (score instanceof Number) {
      return ((Number) score).doubleValue();
    }
    return null;
  }

  public String getScoreAsString() {
    if (score instanceof String) {
      return (String) score;
    }
    return score != null ? score.toString() : null;
  }

  public Boolean getScoreAsBoolean() {
    if (score instanceof Boolean) {
      return (Boolean) score;
    }
    return null;
  }

  public EvalStatus getStatus() {
    return status;
  }

  public void setStatus(EvalStatus status) {
    this.status = status;
  }

  public String getError() {
    return error;
  }

  public void setError(String error) {
    this.error = error;
  }

  public ScoreDetails getDetails() {
    return details;
  }

  public void setDetails(ScoreDetails details) {
    this.details = details;
  }

  public static class Builder {
    private String id;
    private Object score;
    private EvalStatus status;
    private String error;
    private ScoreDetails details;

    public Builder id(String id) {
      this.id = id;
      return this;
    }

    public Builder score(double score) {
      this.score = score;
      return this;
    }

    public Builder score(String score) {
      this.score = score;
      return this;
    }

    public Builder score(boolean score) {
      this.score = score;
      return this;
    }

    public Builder status(EvalStatus status) {
      this.status = status;
      return this;
    }

    public Builder error(String error) {
      this.error = error;
      return this;
    }

    public Builder details(ScoreDetails details) {
      this.details = details;
      return this;
    }

    public Builder reasoning(String reasoning) {
      this.details = ScoreDetails.builder().reasoning(reasoning).build();
      return this;
    }

    public Score build() {
      return new Score(this);
    }
  }
}
