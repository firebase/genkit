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

import java.util.Map;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * RetrieverRequest contains a query for document retrieval.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class RetrieverRequest {

  @JsonProperty("query")
  private Document query;

  @JsonProperty("options")
  private RetrieverOptions options;

  /**
   * Default constructor.
   */
  public RetrieverRequest() {
  }

  /**
   * Creates a RetrieverRequest with a query.
   *
   * @param query
   *            the query document
   */
  public RetrieverRequest(Document query) {
    this.query = query;
  }

  /**
   * Creates a RetrieverRequest with a text query.
   *
   * @param queryText
   *            the query text
   * @return a RetrieverRequest
   */
  public static RetrieverRequest fromText(String queryText) {
    return new RetrieverRequest(Document.fromText(queryText));
  }

  // Getters and setters

  public Document getQuery() {
    return query;
  }

  public void setQuery(Document query) {
    this.query = query;
  }

  public RetrieverOptions getOptions() {
    return options;
  }

  public void setOptions(RetrieverOptions options) {
    this.options = options;
  }

  /**
   * RetrieverOptions contains options for retrieval.
   */
  @JsonInclude(JsonInclude.Include.NON_NULL)
  public static class RetrieverOptions {

    @JsonProperty("k")
    private Integer k;

    @JsonProperty("custom")
    private Map<String, Object> custom;

    public Integer getK() {
      return k;
    }

    public void setK(Integer k) {
      this.k = k;
    }

    public Map<String, Object> getCustom() {
      return custom;
    }

    public void setCustom(Map<String, Object> custom) {
      this.custom = custom;
    }
  }
}
