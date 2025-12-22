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
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Document represents a document for use with embedders and retrievers.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Document {

  @JsonProperty("content")
  private List<Part> content;

  @JsonProperty("metadata")
  private Map<String, Object> metadata;

  /**
   * Default constructor.
   */
  public Document() {
    this.content = new ArrayList<>();
    this.metadata = new HashMap<>();
  }

  /**
   * Creates a Document with text content.
   *
   * @param text
   *            the text content
   */
  public Document(String text) {
    this();
    this.content.add(Part.text(text));
  }

  /**
   * Creates a Document with parts.
   *
   * @param content
   *            the content parts
   */
  public Document(List<Part> content) {
    this.content = content != null ? content : new ArrayList<>();
    this.metadata = new HashMap<>();
  }

  /**
   * Creates a text Document.
   *
   * @param text
   *            the text content
   * @return a Document with text content
   */
  public static Document fromText(String text) {
    return new Document(text);
  }

  /**
   * Creates a Document with text and metadata.
   *
   * @param text
   *            the text content
   * @param metadata
   *            the metadata
   * @return a Document with text content and metadata
   */
  public static Document fromText(String text, Map<String, Object> metadata) {
    Document doc = new Document(text);
    doc.metadata = metadata != null ? metadata : new HashMap<>();
    return doc;
  }

  /**
   * Gets the text content of this Document.
   *
   * @return the concatenated text content
   */
  public String text() {
    if (content == null) {
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
   * Adds metadata to this Document.
   *
   * @param key
   *            the metadata key
   * @param value
   *            the metadata value
   * @return this Document for chaining
   */
  public Document withMetadata(String key, Object value) {
    if (this.metadata == null) {
      this.metadata = new HashMap<>();
    }
    this.metadata.put(key, value);
    return this;
  }
}
