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
 * Part represents a part of a message content, which can be text, media, tool
 * request, or tool response.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Part {

  @JsonProperty("text")
  private String text;

  @JsonProperty("media")
  private Media media;

  @JsonProperty("toolRequest")
  private ToolRequest toolRequest;

  @JsonProperty("toolResponse")
  private ToolResponse toolResponse;

  @JsonProperty("data")
  private Object data;

  @JsonProperty("metadata")
  private Map<String, Object> metadata;

  /**
   * Default constructor.
   */
  public Part() {
  }

  /**
   * Creates a text part.
   *
   * @param text
   *            the text content
   * @return a new text part
   */
  public static Part text(String text) {
    Part part = new Part();
    part.text = text;
    return part;
  }

  /**
   * Creates a media part.
   *
   * @param contentType
   *            the media content type
   * @param url
   *            the media URL
   * @return a new media part
   */
  public static Part media(String contentType, String url) {
    Part part = new Part();
    part.media = new Media(contentType, url);
    return part;
  }

  /**
   * Creates a tool request part.
   *
   * @param toolRequest
   *            the tool request
   * @return a new tool request part
   */
  public static Part toolRequest(ToolRequest toolRequest) {
    Part part = new Part();
    part.toolRequest = toolRequest;
    return part;
  }

  /**
   * Creates a tool response part.
   *
   * @param toolResponse
   *            the tool response
   * @return a new tool response part
   */
  public static Part toolResponse(ToolResponse toolResponse) {
    Part part = new Part();
    part.toolResponse = toolResponse;
    return part;
  }

  /**
   * Creates a data part.
   *
   * @param data
   *            the structured data
   * @return a new data part
   */
  public static Part data(Object data) {
    Part part = new Part();
    part.data = data;
    return part;
  }

  // Getters and setters

  public String getText() {
    return text;
  }

  public void setText(String text) {
    this.text = text;
  }

  public Media getMedia() {
    return media;
  }

  public void setMedia(Media media) {
    this.media = media;
  }

  public ToolRequest getToolRequest() {
    return toolRequest;
  }

  public void setToolRequest(ToolRequest toolRequest) {
    this.toolRequest = toolRequest;
  }

  public ToolResponse getToolResponse() {
    return toolResponse;
  }

  public void setToolResponse(ToolResponse toolResponse) {
    this.toolResponse = toolResponse;
  }

  public Object getData() {
    return data;
  }

  public void setData(Object data) {
    this.data = data;
  }

  public Map<String, Object> getMetadata() {
    return metadata;
  }

  public void setMetadata(Map<String, Object> metadata) {
    this.metadata = metadata;
  }

  /**
   * Returns true if this is a text part.
   *
   * @return true if text
   */
  public boolean isText() {
    return text != null;
  }

  /**
   * Returns true if this is a media part.
   *
   * @return true if media
   */
  public boolean isMedia() {
    return media != null;
  }

  /**
   * Returns true if this is a tool request part.
   *
   * @return true if tool request
   */
  public boolean isToolRequest() {
    return toolRequest != null;
  }

  /**
   * Returns true if this is a tool response part.
   *
   * @return true if tool response
   */
  public boolean isToolResponse() {
    return toolResponse != null;
  }

  /**
   * Returns true if this is a data part.
   *
   * @return true if data
   */
  public boolean isData() {
    return data != null;
  }
}
