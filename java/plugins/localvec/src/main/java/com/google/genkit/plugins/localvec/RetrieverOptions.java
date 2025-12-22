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

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Options for the local vector store retriever.
 */
public class RetrieverOptions {

  @JsonProperty("k")
  private int k = 3;

  /**
   * Default constructor.
   */
  public RetrieverOptions() {
  }

  /**
   * Creates options with specified k value.
   *
   * @param k
   *            the number of documents to retrieve
   */
  public RetrieverOptions(int k) {
    this.k = k;
  }

  /**
   * Gets the number of documents to retrieve.
   *
   * @return the k value
   */
  public int getK() {
    return k;
  }

  /**
   * Sets the number of documents to retrieve.
   *
   * @param k
   *            the k value
   */
  public void setK(int k) {
    this.k = k;
  }
}
