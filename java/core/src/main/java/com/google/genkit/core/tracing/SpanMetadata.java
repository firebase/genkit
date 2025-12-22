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

package com.google.genkit.core.tracing;

import java.util.HashMap;
import java.util.Map;

/**
 * SpanMetadata contains metadata for a tracing span.
 */
public class SpanMetadata {

  private String name;
  private String type;
  private String subtype;
  private Map<String, Object> attributes;

  /**
   * Creates a new SpanMetadata.
   */
  public SpanMetadata() {
    this.attributes = new HashMap<>();
  }

  /**
   * Creates a new SpanMetadata with the specified values.
   *
   * @param name
   *            the span name
   * @param type
   *            the span type
   * @param subtype
   *            the span subtype
   * @param attributes
   *            additional attributes
   */
  public SpanMetadata(String name, String type, String subtype, Map<String, Object> attributes) {
    this.name = name;
    this.type = type;
    this.subtype = subtype;
    this.attributes = attributes != null ? new HashMap<>(attributes) : new HashMap<>();
  }

  /**
   * Creates a builder for SpanMetadata.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  // Getters and setters

  public String getName() {
    return name;
  }

  public void setName(String name) {
    this.name = name;
  }

  public String getType() {
    return type;
  }

  public void setType(String type) {
    this.type = type;
  }

  public String getSubtype() {
    return subtype;
  }

  public void setSubtype(String subtype) {
    this.subtype = subtype;
  }

  public Map<String, Object> getAttributes() {
    return attributes;
  }

  public void setAttributes(Map<String, Object> attributes) {
    this.attributes = attributes;
  }

  /**
   * Adds an attribute to the span metadata.
   *
   * @param key
   *            the attribute key
   * @param value
   *            the attribute value
   * @return this SpanMetadata for chaining
   */
  public SpanMetadata addAttribute(String key, Object value) {
    this.attributes.put(key, value);
    return this;
  }

  /**
   * Builder for SpanMetadata.
   */
  public static class Builder {
    private String name;
    private String type;
    private String subtype;
    private Map<String, Object> attributes = new HashMap<>();

    public Builder name(String name) {
      this.name = name;
      return this;
    }

    public Builder type(String type) {
      this.type = type;
      return this;
    }

    public Builder subtype(String subtype) {
      this.subtype = subtype;
      return this;
    }

    public Builder attributes(Map<String, Object> attributes) {
      this.attributes = new HashMap<>(attributes);
      return this;
    }

    public Builder addAttribute(String key, Object value) {
      this.attributes.put(key, value);
      return this;
    }

    public SpanMetadata build() {
      return new SpanMetadata(name, type, subtype, attributes);
    }
  }
}
