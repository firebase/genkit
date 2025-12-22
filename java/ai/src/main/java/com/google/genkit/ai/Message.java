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
import java.util.Collections;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Message represents a message in a conversation with a generative AI model.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Message {

  @JsonProperty("role")
  private Role role;

  @JsonProperty("content")
  private List<Part> content = new ArrayList<>();

  @JsonProperty("metadata")
  private Map<String, Object> metadata;

  /**
   * Default constructor.
   */
  public Message() {
  }

  /**
   * Creates a message with the given role and content.
   *
   * @param role
   *            the message role
   * @param content
   *            the content parts
   */
  public Message(Role role, List<Part> content) {
    this.role = role;
    this.content = content != null ? new ArrayList<>(content) : new ArrayList<>();
  }

  /**
   * Creates a user message with text content.
   *
   * @param text
   *            the text content
   * @return a new user message
   */
  public static Message user(String text) {
    return new Message(Role.USER, Collections.singletonList(Part.text(text)));
  }

  /**
   * Creates a system message with text content.
   *
   * @param text
   *            the text content
   * @return a new system message
   */
  public static Message system(String text) {
    return new Message(Role.SYSTEM, Collections.singletonList(Part.text(text)));
  }

  /**
   * Creates a model message with text content.
   *
   * @param text
   *            the text content
   * @return a new model message
   */
  public static Message model(String text) {
    return new Message(Role.MODEL, Collections.singletonList(Part.text(text)));
  }

  /**
   * Creates a tool message with content.
   *
   * @param content
   *            the content parts
   * @return a new tool message
   */
  public static Message tool(List<Part> content) {
    return new Message(Role.TOOL, content);
  }

  /**
   * Returns the text content from all text parts.
   *
   * @return the concatenated text
   */
  public String getText() {
    if (content == null || content.isEmpty()) {
      return "";
    }
    StringBuilder sb = new StringBuilder();
    for (Part part : content) {
      if (part.getText() != null) {
        sb.append(part.getText());
      }
    }
    return sb.toString();
  }

  // Getters and setters

  public Role getRole() {
    return role;
  }

  public void setRole(Role role) {
    this.role = role;
  }

  public List<Part> getContent() {
    return content;
  }

  public void setContent(List<Part> content) {
    this.content = content;
  }

  public Map<String, Object> getMetadata() {
    return metadata;
  }

  public void setMetadata(Map<String, Object> metadata) {
    this.metadata = metadata;
  }

  /**
   * Adds a part to the message content.
   *
   * @param part
   *            the part to add
   * @return this message for chaining
   */
  public Message addPart(Part part) {
    if (this.content == null) {
      this.content = new ArrayList<>();
    }
    this.content.add(part);
    return this;
  }

  /**
   * Creates a builder for Message.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  /**
   * Builder for Message.
   */
  public static class Builder {
    private Role role;
    private List<Part> content = new ArrayList<>();
    private Map<String, Object> metadata;

    public Builder role(Role role) {
      this.role = role;
      return this;
    }

    public Builder content(List<Part> content) {
      this.content = new ArrayList<>(content);
      return this;
    }

    public Builder addPart(Part part) {
      this.content.add(part);
      return this;
    }

    public Builder addText(String text) {
      this.content.add(Part.text(text));
      return this;
    }

    public Builder metadata(Map<String, Object> metadata) {
      this.metadata = metadata;
      return this;
    }

    public Message build() {
      Message message = new Message(role, content);
      message.setMetadata(metadata);
      return message;
    }
  }
}
