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

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * ModelResponseChunk represents a streaming chunk from a generative AI model.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ModelResponseChunk {

  @JsonProperty("content")
  private List<Part> content = new ArrayList<>();

  @JsonProperty("index")
  private Integer index;

  /**
   * Default constructor.
   */
  public ModelResponseChunk() {
  }

  /**
   * Creates a ModelResponseChunk with the given content.
   *
   * @param content
   *            the content parts
   */
  public ModelResponseChunk(List<Part> content) {
    this.content = content != null ? new ArrayList<>(content) : new ArrayList<>();
  }

  /**
   * Creates a ModelResponseChunk with text content.
   *
   * @param text
   *            the text content
   * @return a new chunk
   */
  public static ModelResponseChunk text(String text) {
    ModelResponseChunk chunk = new ModelResponseChunk();
    chunk.content.add(Part.text(text));
    return chunk;
  }

  /**
   * Returns the text content from all text parts.
   *
   * @return the concatenated text, or null if no text content
   */
  public String getText() {
    if (content == null || content.isEmpty()) {
      return null;
    }
    StringBuilder sb = new StringBuilder();
    for (Part part : content) {
      if (part.getText() != null) {
        sb.append(part.getText());
      }
    }
    return sb.length() > 0 ? sb.toString() : null;
  }

  // Getters and setters

  public List<Part> getContent() {
    return content;
  }

  public void setContent(List<Part> content) {
    this.content = content;
  }

  public Integer getIndex() {
    return index;
  }

  public void setIndex(Integer index) {
    this.index = index;
  }
}
