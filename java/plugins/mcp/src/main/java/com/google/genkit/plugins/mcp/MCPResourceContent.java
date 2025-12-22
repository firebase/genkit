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

package com.google.genkit.plugins.mcp;

import java.util.List;

/**
 * Represents the content of an MCP resource.
 *
 * <p>
 * Resource content can contain multiple parts, each of which can be text or
 * binary data.
 */
public class MCPResourceContent {

  private final String uri;
  private final List<ContentPart> parts;

  /**
   * Creates a new resource content.
   *
   * @param uri
   *            the resource URI
   * @param parts
   *            the content parts
   */
  public MCPResourceContent(String uri, List<ContentPart> parts) {
    this.uri = uri;
    this.parts = parts;
  }

  /**
   * Gets the resource URI.
   *
   * @return the URI
   */
  public String getUri() {
    return uri;
  }

  /**
   * Gets the content parts.
   *
   * @return the parts
   */
  public List<ContentPart> getParts() {
    return parts;
  }

  /**
   * Gets the text content if this resource has a single text part.
   *
   * @return the text content, or null if not available
   */
  public String getText() {
    if (parts.isEmpty()) {
      return null;
    }
    StringBuilder text = new StringBuilder();
    for (ContentPart part : parts) {
      if (part.getText() != null) {
        text.append(part.getText());
      }
    }
    return text.length() > 0 ? text.toString() : null;
  }

  /**
   * Represents a single part of resource content.
   */
  public static class ContentPart {

    private final String text;
    private final String blob;
    private final String mimeType;

    /**
     * Creates a new content part.
     *
     * @param text
     *            the text content (or null for binary)
     * @param blob
     *            the base64-encoded binary content (or null for text)
     * @param mimeType
     *            the MIME type
     */
    public ContentPart(String text, String blob, String mimeType) {
      this.text = text;
      this.blob = blob;
      this.mimeType = mimeType;
    }

    /**
     * Gets the text content.
     *
     * @return the text, or null if binary
     */
    public String getText() {
      return text;
    }

    /**
     * Gets the base64-encoded binary content.
     *
     * @return the blob, or null if text
     */
    public String getBlob() {
      return blob;
    }

    /**
     * Gets the MIME type.
     *
     * @return the MIME type
     */
    public String getMimeType() {
      return mimeType;
    }

    /**
     * Checks if this part is text.
     *
     * @return true if text
     */
    public boolean isText() {
      return text != null;
    }

    /**
     * Checks if this part is binary.
     *
     * @return true if binary
     */
    public boolean isBinary() {
      return blob != null;
    }
  }
}
