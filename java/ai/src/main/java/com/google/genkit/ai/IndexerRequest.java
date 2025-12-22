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
 * Request to index documents into a vector store.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class IndexerRequest {

  @JsonProperty("documents")
  private List<Document> documents;

  @JsonProperty("options")
  private Object options;

  /**
   * Default constructor.
   */
  public IndexerRequest() {
    this.documents = new ArrayList<>();
  }

  /**
   * Creates a request with documents.
   *
   * @param documents
   *            the documents to index
   */
  public IndexerRequest(List<Document> documents) {
    this.documents = documents != null ? documents : new ArrayList<>();
  }

  /**
   * Creates a request with documents and options.
   *
   * @param documents
   *            the documents to index
   * @param options
   *            the indexing options
   */
  public IndexerRequest(List<Document> documents, Object options) {
    this.documents = documents != null ? documents : new ArrayList<>();
    this.options = options;
  }

  /**
   * Gets the documents to index.
   *
   * @return the documents
   */
  public List<Document> getDocuments() {
    return documents;
  }

  /**
   * Sets the documents to index.
   *
   * @param documents
   *            the documents
   */
  public void setDocuments(List<Document> documents) {
    this.documents = documents;
  }

  /**
   * Gets the indexing options.
   *
   * @return the options
   */
  public Object getOptions() {
    return options;
  }

  /**
   * Sets the indexing options.
   *
   * @param options
   *            the options
   */
  public void setOptions(Object options) {
    this.options = options;
  }
}
