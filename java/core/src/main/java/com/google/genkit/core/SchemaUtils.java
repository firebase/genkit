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

import java.util.Map;

import com.fasterxml.jackson.databind.JsonNode;
import com.github.victools.jsonschema.generator.*;

/**
 * SchemaUtils provides utilities for JSON Schema generation and validation.
 */
public final class SchemaUtils {

  private static final SchemaGenerator schemaGenerator;

  static {
    SchemaGeneratorConfigBuilder configBuilder = new SchemaGeneratorConfigBuilder(SchemaVersion.DRAFT_7,
        OptionPreset.PLAIN_JSON);

    configBuilder.with(Option.EXTRA_OPEN_API_FORMAT_VALUES);
    configBuilder.with(Option.FLATTENED_ENUMS);
    // Note: Removed NULLABLE_FIELDS_BY_DEFAULT as it generates "type": ["string",
    // "null"]
    // for all fields, which causes issues with the Genkit UI input form generation.
    // Fields should be explicitly marked as nullable using @Nullable annotation if
    // needed.

    SchemaGeneratorConfig config = configBuilder.build();
    schemaGenerator = new SchemaGenerator(config);
  }

  private SchemaUtils() {
    // Utility class
  }

  /**
   * Generates a JSON Schema for the given class.
   *
   * @param clazz
   *            the class to generate schema for
   * @return the JSON schema as a map
   */
  @SuppressWarnings("unchecked")
  public static Map<String, Object> inferSchema(Class<?> clazz) {
    if (clazz == null || clazz == Void.class || clazz == void.class) {
      return null;
    }

    try {
      JsonNode schemaNode = schemaGenerator.generateSchema(clazz);
      return JsonUtils.getObjectMapper().convertValue(schemaNode, Map.class);
    } catch (Exception e) {
      // If schema generation fails, return a simple object schema
      return Map.of("type", "object");
    }
  }

  /**
   * Generates a JSON Schema for a primitive type.
   *
   * @param typeName
   *            the type name (string, number, integer, boolean, array, object)
   * @return the JSON schema as a map
   */
  public static Map<String, Object> simpleSchema(String typeName) {
    return Map.of("type", typeName);
  }

  /**
   * Creates a schema for a string type.
   *
   * @return the string schema
   */
  public static Map<String, Object> stringSchema() {
    return simpleSchema("string");
  }

  /**
   * Creates a schema for an integer type.
   *
   * @return the integer schema
   */
  public static Map<String, Object> integerSchema() {
    return simpleSchema("integer");
  }

  /**
   * Creates a schema for a number type.
   *
   * @return the number schema
   */
  public static Map<String, Object> numberSchema() {
    return simpleSchema("number");
  }

  /**
   * Creates a schema for a boolean type.
   *
   * @return the boolean schema
   */
  public static Map<String, Object> booleanSchema() {
    return simpleSchema("boolean");
  }

  /**
   * Creates a schema for an array type with the given items schema.
   *
   * @param itemsSchema
   *            the schema for array items
   * @return the array schema
   */
  public static Map<String, Object> arraySchema(Map<String, Object> itemsSchema) {
    return Map.of("type", "array", "items", itemsSchema);
  }

  /**
   * Creates a schema for an object type with the given properties.
   *
   * @param properties
   *            the property schemas
   * @return the object schema
   */
  public static Map<String, Object> objectSchema(Map<String, Object> properties) {
    return Map.of("type", "object", "properties", properties);
  }
}
