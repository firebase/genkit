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

package com.google.genkit.plugins.localvec;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.google.genkit.ai.Document;

/**
 * Represents a stored document value with its embedding.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class DbValue {

  @JsonProperty("doc")
  private Document doc;

  @JsonProperty("embedding")
  private List<Float> embedding;

  /**
   * Default constructor for Jackson.
   */
  public DbValue() {
  }

  /**
   * Creates a new DbValue.
   *
   * @param doc
   *            the document
   * @param embedding
   *            the embedding vector
   */
  public DbValue(Document doc, List<Float> embedding) {
    this.doc = doc;
    this.embedding = embedding;
  }

  /**
   * Gets the document.
   *
   * @return the document
   */
  public Document getDoc() {
    return doc;
  }

  /**
   * Sets the document.
   *
   * @param doc
   *            the document
   */
  public void setDoc(Document doc) {
    this.doc = doc;
  }

  /**
   * Gets the embedding.
   *
   * @return the embedding vector
   */
  public List<Float> getEmbedding() {
    return embedding;
  }

  /**
   * Sets the embedding.
   *
   * @param embedding
   *            the embedding vector
   */
  public void setEmbedding(List<Float> embedding) {
    this.embedding = embedding;
  }
}
