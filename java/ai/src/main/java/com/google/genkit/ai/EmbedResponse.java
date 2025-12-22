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

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * EmbedResponse contains the embeddings generated from documents.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class EmbedResponse {

  @JsonProperty("embeddings")
  private List<Embedding> embeddings;

  /**
   * Default constructor.
   */
  public EmbedResponse() {
  }

  /**
   * Creates an EmbedResponse with embeddings.
   *
   * @param embeddings
   *            the embeddings
   */
  public EmbedResponse(List<Embedding> embeddings) {
    this.embeddings = embeddings;
  }

  // Getters and setters

  public List<Embedding> getEmbeddings() {
    return embeddings;
  }

  public void setEmbeddings(List<Embedding> embeddings) {
    this.embeddings = embeddings;
  }

  /**
   * Embedding represents a single embedding vector.
   */
  @JsonInclude(JsonInclude.Include.NON_NULL)
  public static class Embedding {

    @JsonProperty("values")
    private float[] values;

    /**
     * Default constructor.
     */
    public Embedding() {
    }

    /**
     * Creates an Embedding with the given values.
     *
     * @param values
     *            the embedding values
     */
    public Embedding(float[] values) {
      this.values = values;
    }

    public float[] getValues() {
      return values;
    }

    public void setValues(float[] values) {
      this.values = values;
    }
  }
}
