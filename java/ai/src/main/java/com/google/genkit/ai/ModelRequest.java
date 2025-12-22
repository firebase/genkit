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

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * ModelRequest represents a request to a generative AI model.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ModelRequest {

  @JsonProperty("messages")
  private List<Message> messages = new ArrayList<>();

  @JsonProperty("config")
  private Map<String, Object> config;

  @JsonProperty("tools")
  private List<ToolDefinition> tools;

  @JsonProperty("output")
  private OutputConfig output;

  @JsonProperty("context")
  private List<Document> context;

  /**
   * Default constructor.
   */
  public ModelRequest() {
  }

  /**
   * Creates a ModelRequest with the given messages.
   *
   * @param messages
   *            the messages
   */
  public ModelRequest(List<Message> messages) {
    this.messages = messages != null ? new ArrayList<>(messages) : new ArrayList<>();
  }

  /**
   * Creates a builder for ModelRequest.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  // Getters and setters

  public List<Message> getMessages() {
    return messages;
  }

  public void setMessages(List<Message> messages) {
    this.messages = messages;
  }

  public Map<String, Object> getConfig() {
    return config;
  }

  public void setConfig(Map<String, Object> config) {
    this.config = config;
  }

  public List<ToolDefinition> getTools() {
    return tools;
  }

  public void setTools(List<ToolDefinition> tools) {
    this.tools = tools;
  }

  public OutputConfig getOutput() {
    return output;
  }

  public void setOutput(OutputConfig output) {
    this.output = output;
  }

  public List<Document> getContext() {
    return context;
  }

  public void setContext(List<Document> context) {
    this.context = context;
  }

  /**
   * Adds a message to the request.
   *
   * @param message
   *            the message to add
   * @return this request for chaining
   */
  public ModelRequest addMessage(Message message) {
    if (this.messages == null) {
      this.messages = new ArrayList<>();
    }
    this.messages.add(message);
    return this;
  }

  /**
   * Builder for ModelRequest.
   */
  public static class Builder {
    private List<Message> messages = new ArrayList<>();
    private Map<String, Object> config;
    private List<ToolDefinition> tools;
    private OutputConfig output;
    private List<Document> context;

    public Builder messages(List<Message> messages) {
      this.messages = new ArrayList<>(messages);
      return this;
    }

    public Builder addMessage(Message message) {
      this.messages.add(message);
      return this;
    }

    public Builder addUserMessage(String text) {
      this.messages.add(Message.user(text));
      return this;
    }

    public Builder addSystemMessage(String text) {
      this.messages.add(Message.system(text));
      return this;
    }

    public Builder config(Map<String, Object> config) {
      this.config = config;
      return this;
    }

    public Builder tools(List<ToolDefinition> tools) {
      this.tools = tools;
      return this;
    }

    public Builder output(OutputConfig output) {
      this.output = output;
      return this;
    }

    public Builder context(List<Document> context) {
      this.context = context;
      return this;
    }

    public ModelRequest build() {
      ModelRequest request = new ModelRequest(messages);
      request.setConfig(config);
      request.setTools(tools);
      request.setOutput(output);
      request.setContext(context);
      return request;
    }
  }
}
