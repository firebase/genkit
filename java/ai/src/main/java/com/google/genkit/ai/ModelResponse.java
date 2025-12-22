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

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * ModelResponse represents a response from a generative AI model.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ModelResponse {

  @JsonProperty("candidates")
  private List<Candidate> candidates = new ArrayList<>();

  @JsonProperty("usage")
  private Usage usage;

  @JsonProperty("request")
  private ModelRequest request;

  @JsonProperty("custom")
  private Map<String, Object> custom;

  @JsonProperty("latencyMs")
  private Long latencyMs;

  @JsonProperty("finishReason")
  private FinishReason finishReason;

  @JsonProperty("finishMessage")
  private String finishMessage;

  @JsonProperty("interrupts")
  private List<Part> interrupts;

  /**
   * Default constructor.
   */
  public ModelResponse() {
  }

  /**
   * Creates a ModelResponse with the given candidates.
   *
   * @param candidates
   *            the candidates
   */
  public ModelResponse(List<Candidate> candidates) {
    this.candidates = candidates != null ? new ArrayList<>(candidates) : new ArrayList<>();
  }

  /**
   * Creates a builder for ModelResponse.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  /**
   * Returns the text content from the first candidate's first text part.
   *
   * @return the text content, or null if no text content is available
   */
  public String getText() {
    if (candidates == null || candidates.isEmpty()) {
      return null;
    }
    Candidate first = candidates.get(0);
    if (first.getMessage() == null || first.getMessage().getContent() == null) {
      return null;
    }
    return first.getMessage().getContent().stream().filter(part -> part.getText() != null).map(Part::getText)
        .collect(Collectors.joining());
  }

  /**
   * Returns the first candidate's message.
   *
   * @return the message, or null if no candidates
   */
  public Message getMessage() {
    if (candidates == null || candidates.isEmpty()) {
      return null;
    }
    return candidates.get(0).getMessage();
  }

  /**
   * Returns all messages including the model's response.
   *
   * <p>
   * This is useful when resuming after an interrupt - pass these messages to the
   * next generate call to maintain context.
   *
   * @return list of all messages (request messages + model response)
   */
  public List<Message> getMessages() {
    List<Message> messages = new ArrayList<>();
    if (request != null && request.getMessages() != null) {
      messages.addAll(request.getMessages());
    }
    Message responseMessage = getMessage();
    if (responseMessage != null) {
      messages.add(responseMessage);
    }
    return messages;
  }

  /**
   * Returns all tool request parts from the first candidate.
   *
   * @return list of tool requests
   */
  public List<Part> getToolRequests() {
    if (candidates == null || candidates.isEmpty()) {
      return new ArrayList<>();
    }
    Candidate first = candidates.get(0);
    if (first.getMessage() == null || first.getMessage().getContent() == null) {
      return new ArrayList<>();
    }
    return first.getMessage().getContent().stream().filter(part -> part.getToolRequest() != null)
        .collect(Collectors.toList());
  }

  // Getters and setters

  public List<Candidate> getCandidates() {
    return candidates;
  }

  public void setCandidates(List<Candidate> candidates) {
    this.candidates = candidates;
  }

  public Usage getUsage() {
    return usage;
  }

  public void setUsage(Usage usage) {
    this.usage = usage;
  }

  public ModelRequest getRequest() {
    return request;
  }

  public void setRequest(ModelRequest request) {
    this.request = request;
  }

  public Map<String, Object> getCustom() {
    return custom;
  }

  public void setCustom(Map<String, Object> custom) {
    this.custom = custom;
  }

  public Long getLatencyMs() {
    return latencyMs;
  }

  public void setLatencyMs(Long latencyMs) {
    this.latencyMs = latencyMs;
  }

  public FinishReason getFinishReason() {
    if (finishReason != null) {
      return finishReason;
    }
    // Fall back to first candidate's finish reason
    if (candidates != null && !candidates.isEmpty()) {
      return candidates.get(0).getFinishReason();
    }
    return null;
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

  /**
   * Returns the list of interrupt tool requests.
   * 
   * <p>
   * When the model requests tools that are interrupts, this list contains the
   * tool request parts with interrupt metadata. Check if this list is non-empty
   * to determine if generation was interrupted.
   *
   * @return list of interrupt tool request parts, or empty list if none
   */
  public List<Part> getInterrupts() {
    return interrupts != null ? interrupts : new ArrayList<>();
  }

  public void setInterrupts(List<Part> interrupts) {
    this.interrupts = interrupts;
  }

  /**
   * Checks if generation was interrupted.
   *
   * @return true if there are pending interrupts
   */
  public boolean isInterrupted() {
    return interrupts != null && !interrupts.isEmpty();
  }

  /**
   * Builder for ModelResponse.
   */
  public static class Builder {
    private List<Candidate> candidates = new ArrayList<>();
    private Usage usage;
    private ModelRequest request;
    private Map<String, Object> custom;
    private Long latencyMs;
    private FinishReason finishReason;
    private String finishMessage;
    private List<Part> interrupts;

    public Builder candidates(List<Candidate> candidates) {
      this.candidates = new ArrayList<>(candidates);
      return this;
    }

    public Builder addCandidate(Candidate candidate) {
      this.candidates.add(candidate);
      return this;
    }

    public Builder usage(Usage usage) {
      this.usage = usage;
      return this;
    }

    public Builder request(ModelRequest request) {
      this.request = request;
      return this;
    }

    public Builder custom(Map<String, Object> custom) {
      this.custom = custom;
      return this;
    }

    public Builder latencyMs(Long latencyMs) {
      this.latencyMs = latencyMs;
      return this;
    }

    public Builder finishReason(FinishReason finishReason) {
      this.finishReason = finishReason;
      return this;
    }

    public Builder finishMessage(String finishMessage) {
      this.finishMessage = finishMessage;
      return this;
    }

    public Builder interrupts(List<Part> interrupts) {
      this.interrupts = interrupts != null ? new ArrayList<>(interrupts) : null;
      return this;
    }

    public ModelResponse build() {
      ModelResponse response = new ModelResponse(candidates);
      response.setUsage(usage);
      response.setRequest(request);
      response.setCustom(custom);
      response.setLatencyMs(latencyMs);
      response.setFinishReason(finishReason);
      response.setFinishMessage(finishMessage);
      response.setInterrupts(interrupts);
      return response;
    }
  }
}
