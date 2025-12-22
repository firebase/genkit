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

/**
 * Represents an MCP resource.
 *
 * <p>
 * Resources in MCP are data sources that can be read by clients. They have a
 * URI, name, optional description, and MIME type.
 */
public class MCPResource {

  private final String uri;
  private final String name;
  private final String description;
  private final String mimeType;

  /**
   * Creates a new MCP resource.
   *
   * @param uri
   *            the resource URI
   * @param name
   *            the resource name
   * @param description
   *            the resource description
   * @param mimeType
   *            the MIME type
   */
  public MCPResource(String uri, String name, String description, String mimeType) {
    this.uri = uri;
    this.name = name;
    this.description = description;
    this.mimeType = mimeType;
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
   * Gets the resource name.
   *
   * @return the name
   */
  public String getName() {
    return name;
  }

  /**
   * Gets the resource description.
   *
   * @return the description
   */
  public String getDescription() {
    return description;
  }

  /**
   * Gets the MIME type.
   *
   * @return the MIME type
   */
  public String getMimeType() {
    return mimeType;
  }

  @Override
  public String toString() {
    return "MCPResource{" + "uri='" + uri + '\'' + ", name='" + name + '\'' + ", description='" + description + '\''
        + ", mimeType='" + mimeType + '\'' + '}';
  }
}
