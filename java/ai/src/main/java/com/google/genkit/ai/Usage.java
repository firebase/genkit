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

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Usage represents token usage statistics from a model response.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Usage {

  @JsonProperty("inputTokens")
  private Integer inputTokens;

  @JsonProperty("outputTokens")
  private Integer outputTokens;

  @JsonProperty("totalTokens")
  private Integer totalTokens;

  @JsonProperty("inputCharacters")
  private Integer inputCharacters;

  @JsonProperty("outputCharacters")
  private Integer outputCharacters;

  @JsonProperty("inputImages")
  private Integer inputImages;

  @JsonProperty("outputImages")
  private Integer outputImages;

  @JsonProperty("inputAudioFiles")
  private Integer inputAudioFiles;

  @JsonProperty("outputAudioFiles")
  private Integer outputAudioFiles;

  @JsonProperty("inputVideoFiles")
  private Integer inputVideoFiles;

  @JsonProperty("outputVideoFiles")
  private Integer outputVideoFiles;

  @JsonProperty("thoughtsTokens")
  private Integer thoughtsTokens;

  @JsonProperty("cachedContentTokens")
  private Integer cachedContentTokens;

  /**
   * Default constructor.
   */
  public Usage() {
  }

  /**
   * Creates a Usage with token counts.
   *
   * @param inputTokens
   *            number of input tokens
   * @param outputTokens
   *            number of output tokens
   * @param totalTokens
   *            total number of tokens
   */
  public Usage(Integer inputTokens, Integer outputTokens, Integer totalTokens) {
    this.inputTokens = inputTokens;
    this.outputTokens = outputTokens;
    this.totalTokens = totalTokens;
  }

  // Getters and setters

  public Integer getInputTokens() {
    return inputTokens;
  }

  public void setInputTokens(Integer inputTokens) {
    this.inputTokens = inputTokens;
  }

  public Integer getOutputTokens() {
    return outputTokens;
  }

  public void setOutputTokens(Integer outputTokens) {
    this.outputTokens = outputTokens;
  }

  public Integer getTotalTokens() {
    return totalTokens;
  }

  public void setTotalTokens(Integer totalTokens) {
    this.totalTokens = totalTokens;
  }

  public Integer getInputCharacters() {
    return inputCharacters;
  }

  public void setInputCharacters(Integer inputCharacters) {
    this.inputCharacters = inputCharacters;
  }

  public Integer getOutputCharacters() {
    return outputCharacters;
  }

  public void setOutputCharacters(Integer outputCharacters) {
    this.outputCharacters = outputCharacters;
  }

  public Integer getInputImages() {
    return inputImages;
  }

  public void setInputImages(Integer inputImages) {
    this.inputImages = inputImages;
  }

  public Integer getOutputImages() {
    return outputImages;
  }

  public void setOutputImages(Integer outputImages) {
    this.outputImages = outputImages;
  }

  public Integer getInputAudioFiles() {
    return inputAudioFiles;
  }

  public void setInputAudioFiles(Integer inputAudioFiles) {
    this.inputAudioFiles = inputAudioFiles;
  }

  public Integer getOutputAudioFiles() {
    return outputAudioFiles;
  }

  public void setOutputAudioFiles(Integer outputAudioFiles) {
    this.outputAudioFiles = outputAudioFiles;
  }

  public Integer getInputVideoFiles() {
    return inputVideoFiles;
  }

  public void setInputVideoFiles(Integer inputVideoFiles) {
    this.inputVideoFiles = inputVideoFiles;
  }

  public Integer getOutputVideoFiles() {
    return outputVideoFiles;
  }

  public void setOutputVideoFiles(Integer outputVideoFiles) {
    this.outputVideoFiles = outputVideoFiles;
  }

  public Integer getThoughtsTokens() {
    return thoughtsTokens;
  }

  public void setThoughtsTokens(Integer thoughtsTokens) {
    this.thoughtsTokens = thoughtsTokens;
  }

  public Integer getCachedContentTokens() {
    return cachedContentTokens;
  }

  public void setCachedContentTokens(Integer cachedContentTokens) {
    this.cachedContentTokens = cachedContentTokens;
  }
}
