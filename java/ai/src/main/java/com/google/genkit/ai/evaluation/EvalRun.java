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
 * Represents a complete evaluation run with results.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class EvalRun {

  /**
   * Key identifying this evaluation run.
   */
  @JsonProperty("key")
  private EvalRunKey key;

  /**
   * Results for all test cases.
   */
  @JsonProperty("results")
  private List<EvalResult> results;

  public EvalRun() {
  }

  private EvalRun(Builder builder) {
    this.key = builder.key;
    this.results = builder.results;
  }

  public static Builder builder() {
    return new Builder();
  }

  public EvalRunKey getKey() {
    return key;
  }

  public void setKey(EvalRunKey key) {
    this.key = key;
  }

  public List<EvalResult> getResults() {
    return results;
  }

  public void setResults(List<EvalResult> results) {
    this.results = results;
  }

  public static class Builder {
    private EvalRunKey key;
    private List<EvalResult> results;

    public Builder key(EvalRunKey key) {
      this.key = key;
      return this;
    }

    public Builder results(List<EvalResult> results) {
      this.results = results;
      return this;
    }

    public EvalRun build() {
      return new EvalRun(this);
    }
  }
}
