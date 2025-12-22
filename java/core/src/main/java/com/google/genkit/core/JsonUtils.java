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

package com.google.genkit.core;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

/**
 * JsonUtils provides JSON serialization and deserialization utilities for
 * Genkit.
 */
public final class JsonUtils {

  private static final ObjectMapper objectMapper;

  static {
    objectMapper = new ObjectMapper();
    objectMapper.registerModule(new JavaTimeModule());
    objectMapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
    objectMapper.configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false);
    objectMapper.configure(SerializationFeature.FAIL_ON_EMPTY_BEANS, false);
  }

  private JsonUtils() {
    // Utility class
  }

  /**
   * Returns the shared ObjectMapper instance.
   *
   * @return the ObjectMapper
   */
  public static ObjectMapper getObjectMapper() {
    return objectMapper;
  }

  /**
   * Converts an object to JSON string.
   *
   * @param value
   *            the object to convert
   * @return the JSON string
   * @throws GenkitException
   *             if serialization fails
   */
  public static String toJson(Object value) throws GenkitException {
    try {
      return objectMapper.writeValueAsString(value);
    } catch (JsonProcessingException e) {
      throw new GenkitException("Failed to serialize to JSON: " + e.getMessage(), e);
    }
  }

  /**
   * Converts an object to a JsonNode.
   *
   * @param value
   *            the object to convert
   * @return the JsonNode
   */
  public static JsonNode toJsonNode(Object value) {
    return objectMapper.valueToTree(value);
  }

  /**
   * Parses a JSON string to the specified type.
   *
   * @param json
   *            the JSON string
   * @param clazz
   *            the target class
   * @param <T>
   *            the target type
   * @return the parsed object
   * @throws GenkitException
   *             if parsing fails
   */
  public static <T> T fromJson(String json, Class<T> clazz) throws GenkitException {
    try {
      return objectMapper.readValue(json, clazz);
    } catch (JsonProcessingException e) {
      throw new GenkitException("Failed to parse JSON: " + e.getMessage(), e);
    }
  }

  /**
   * Converts a JsonNode to the specified type.
   *
   * @param node
   *            the JsonNode
   * @param clazz
   *            the target class
   * @param <T>
   *            the target type
   * @return the converted object
   * @throws GenkitException
   *             if conversion fails
   */
  public static <T> T fromJsonNode(JsonNode node, Class<T> clazz) throws GenkitException {
    try {
      return objectMapper.treeToValue(node, clazz);
    } catch (JsonProcessingException e) {
      throw new GenkitException("Failed to convert JsonNode: " + e.getMessage(), e);
    }
  }

  /**
   * Parses a JSON string to a JsonNode.
   *
   * @param json
   *            the JSON string
   * @return the JsonNode
   * @throws GenkitException
   *             if parsing fails
   */
  public static JsonNode parseJson(String json) throws GenkitException {
    try {
      return objectMapper.readTree(json);
    } catch (JsonProcessingException e) {
      throw new GenkitException("Failed to parse JSON: " + e.getMessage(), e);
    }
  }

  /**
   * Converts an object to the specified type.
   * 
   * <p>
   * This is useful for converting Maps (from JSON parsing) to typed objects.
   *
   * @param value
   *            the object to convert (typically a Map from JSON parsing)
   * @param clazz
   *            the target class
   * @param <T>
   *            the target type
   * @return the converted object
   * @throws GenkitException
   *             if conversion fails
   */
  public static <T> T convert(Object value, Class<T> clazz) throws GenkitException {
    try {
      return objectMapper.convertValue(value, clazz);
    } catch (IllegalArgumentException e) {
      throw new GenkitException("Failed to convert object to " + clazz.getName() + ": " + e.getMessage(), e);
    }
  }

  /**
   * Pretty prints a JSON object.
   *
   * @param value
   *            the object to print
   * @return the pretty-printed JSON string
   * @throws GenkitException
   *             if serialization fails
   */
  public static String toPrettyJson(Object value) throws GenkitException {
    try {
      return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(value);
    } catch (JsonProcessingException e) {
      throw new GenkitException("Failed to serialize to JSON: " + e.getMessage(), e);
    }
  }
}
