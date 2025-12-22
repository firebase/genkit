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

import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * EmbedRequest contains documents to embed.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class EmbedRequest {

  @JsonProperty("input")
  private List<Document> documents;

  @JsonProperty("options")
  private Map<String, Object> options;

  /**
   * Default constructor.
   */
  public EmbedRequest() {
  }

  /**
   * Creates an EmbedRequest with documents.
   *
   * @param documents
   *            the documents to embed
   */
  public EmbedRequest(List<Document> documents) {
    this.documents = documents;
  }

  // Getters and setters

  public List<Document> getDocuments() {
    return documents;
  }

  public void setDocuments(List<Document> documents) {
    this.documents = documents;
  }

  public Map<String, Object> getOptions() {
    return options;
  }

  public void setOptions(Map<String, Object> options) {
    this.options = options;
  }
}
