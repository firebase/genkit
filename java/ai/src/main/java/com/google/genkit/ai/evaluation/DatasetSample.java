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
 * Represents a single sample in an inference dataset.
 * 
 * <p>
 * A sample contains the input to run through the AI system and an optional
 * reference output for comparison during evaluation.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class DatasetSample {

  /**
   * Optional identifier for this test case.
   */
  @JsonProperty("testCaseId")
  private String testCaseId;

  /**
   * The input to provide to the AI system.
   */
  @JsonProperty("input")
  private Object input;

  /**
   * The expected/reference output for comparison.
   */
  @JsonProperty("reference")
  private Object reference;

  public DatasetSample() {
  }

  private DatasetSample(Builder builder) {
    this.testCaseId = builder.testCaseId;
    this.input = builder.input;
    this.reference = builder.reference;
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

  public Object getReference() {
    return reference;
  }

  public void setReference(Object reference) {
    this.reference = reference;
  }

  public static class Builder {
    private String testCaseId;
    private Object input;
    private Object reference;

    public Builder testCaseId(String testCaseId) {
      this.testCaseId = testCaseId;
      return this;
    }

    public Builder input(Object input) {
      this.input = input;
      return this;
    }

    public Builder reference(Object reference) {
      this.reference = reference;
      return this;
    }

    public DatasetSample build() {
      return new DatasetSample(this);
    }
  }
}
