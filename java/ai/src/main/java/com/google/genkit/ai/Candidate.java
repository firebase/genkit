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

import java.util.Map;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Candidate represents a single model response candidate.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Candidate {

  @JsonProperty("index")
  private int index;

  @JsonProperty("message")
  private Message message;

  @JsonProperty("finishReason")
  private FinishReason finishReason;

  @JsonProperty("finishMessage")
  private String finishMessage;

  @JsonProperty("custom")
  private Map<String, Object> custom;

  /**
   * Default constructor.
   */
  public Candidate() {
  }

  /**
   * Creates a Candidate with a message.
   *
   * @param message
   *            the candidate message
   */
  public Candidate(Message message) {
    this.message = message;
  }

  /**
   * Creates a Candidate with message and finish reason.
   *
   * @param message
   *            the candidate message
   * @param finishReason
   *            the finish reason
   */
  public Candidate(Message message, FinishReason finishReason) {
    this.message = message;
    this.finishReason = finishReason;
  }

  // Getters and setters

  public int getIndex() {
    return index;
  }

  public void setIndex(int index) {
    this.index = index;
  }

  public Message getMessage() {
    return message;
  }

  public void setMessage(Message message) {
    this.message = message;
  }

  public FinishReason getFinishReason() {
    return finishReason;
  }

  public void setFinishReason(FinishReason finishReason) {
    this.finishReason = finishReason;
  }

  public String getFinishMessage() {
    return finishMessage;
  }

  public void setFinishMessage(String finishMessage) {
    this.finishMessage = finishMessage;
  }

  public Map<String, Object> getCustom() {
    return custom;
  }

  public void setCustom(Map<String, Object> custom) {
    this.custom = custom;
  }

  /**
   * Extracts the text content from this candidate.
   *
   * @return the concatenated text content
   */
  public String text() {
    if (message == null || message.getContent() == null) {
      return "";
    }
    StringBuilder sb = new StringBuilder();
    for (Part part : message.getContent()) {
      if (part.getText() != null) {
        sb.append(part.getText());
      }
    }
    return sb.toString();
  }
}
