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

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Media represents media content in a message part.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Media {

  @JsonProperty("contentType")
  private String contentType;

  @JsonProperty("url")
  private String url;

  /**
   * Default constructor.
   */
  public Media() {
  }

  /**
   * Creates a Media with the given content type and URL.
   *
   * @param contentType
   *            the MIME type
   * @param url
   *            the media URL or data URI
   */
  public Media(String contentType, String url) {
    this.contentType = contentType;
    this.url = url;
  }

  // Getters and setters

  public String getContentType() {
    return contentType;
  }

  public void setContentType(String contentType) {
    this.contentType = contentType;
  }

  public String getUrl() {
    return url;
  }

  public void setUrl(String url) {
    this.url = url;
  }
}
