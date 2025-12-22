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

import static org.junit.jupiter.api.Assertions.*;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Unit tests for JsonUtils.
 */
class JsonUtilsTest {

  @Test
  void testGetObjectMapper() {
    ObjectMapper mapper = JsonUtils.getObjectMapper();
    assertNotNull(mapper);
    // Same instance should be returned
    assertSame(mapper, JsonUtils.getObjectMapper());
  }

  @Test
  void testToJson() {
    TestObject obj = new TestObject("test", 42);

    String json = JsonUtils.toJson(obj);

    assertNotNull(json);
    assertTrue(json.contains("\"name\":\"test\""));
    assertTrue(json.contains("\"value\":42"));
  }

  @Test
  void testToJsonWithNull() {
    String json = JsonUtils.toJson(null);
    assertEquals("null", json);
  }

  @Test
  void testToJsonNode() {
    TestObject obj = new TestObject("test", 42);

    JsonNode node = JsonUtils.toJsonNode(obj);

    assertNotNull(node);
    assertEquals("test", node.get("name").asText());
    assertEquals(42, node.get("value").asInt());
  }

  @Test
  void testFromJson() {
    String json = "{\"name\":\"test\",\"value\":42}";

    TestObject obj = JsonUtils.fromJson(json, TestObject.class);

    assertNotNull(obj);
    assertEquals("test", obj.getName());
    assertEquals(42, obj.getValue());
  }

  @Test
  void testFromJsonIgnoresUnknownProperties() {
    String json = "{\"name\":\"test\",\"value\":42,\"unknown\":\"field\"}";

    TestObject obj = JsonUtils.fromJson(json, TestObject.class);

    assertNotNull(obj);
    assertEquals("test", obj.getName());
    assertEquals(42, obj.getValue());
  }

  @Test
  void testFromJsonInvalidJson() {
    String invalidJson = "{invalid}";

    assertThrows(GenkitException.class, () -> JsonUtils.fromJson(invalidJson, TestObject.class));
  }

  @Test
  void testFromJsonNode() {
    JsonNode node = JsonUtils.getObjectMapper().createObjectNode().put("name", "test").put("value", 42);

    TestObject obj = JsonUtils.fromJsonNode(node, TestObject.class);

    assertNotNull(obj);
    assertEquals("test", obj.getName());
    assertEquals(42, obj.getValue());
  }

  @Test
  void testParseJson() {
    String json = "{\"name\":\"test\",\"value\":42}";

    JsonNode node = JsonUtils.parseJson(json);

    assertNotNull(node);
    assertEquals("test", node.get("name").asText());
    assertEquals(42, node.get("value").asInt());
  }

  @Test
  void testParseJsonInvalidJson() {
    String invalidJson = "{invalid}";

    assertThrows(GenkitException.class, () -> JsonUtils.parseJson(invalidJson));
  }

  @Test
  void testToPrettyJson() {
    TestObject obj = new TestObject("test", 42);

    String prettyJson = JsonUtils.toPrettyJson(obj);

    assertNotNull(prettyJson);
    assertTrue(prettyJson.contains("\n")); // Should have newlines for pretty printing
    assertTrue(prettyJson.contains("\"name\""));
    assertTrue(prettyJson.contains("\"value\""));
  }

  @Test
  void testToJsonMap() {
    Map<String, Object> map = new HashMap<>();
    map.put("key1", "value1");
    map.put("key2", 123);

    String json = JsonUtils.toJson(map);

    assertNotNull(json);
    assertTrue(json.contains("\"key1\":\"value1\""));
    assertTrue(json.contains("\"key2\":123"));
  }

  @Test
  void testDateSerialization() {
    Instant now = Instant.parse("2025-01-01T12:00:00Z");
    Map<String, Object> map = new HashMap<>();
    map.put("timestamp", now);

    String json = JsonUtils.toJson(map);

    assertNotNull(json);
    // Should serialize as ISO-8601 string, not timestamps
    assertTrue(json.contains("2025-01-01"));
  }

  @Test
  void testEmptyObjectSerialization() {
    Object emptyObj = new Object() {
    };

    // Should not fail on empty beans
    assertDoesNotThrow(() -> JsonUtils.toJson(emptyObj));
  }

  /**
   * Test helper class.
   */
  static class TestObject {
    @JsonProperty("name")
    private String name;

    @JsonProperty("value")
    private int value;

    public TestObject() {
    }

    public TestObject(String name, int value) {
      this.name = name;
      this.value = value;
    }

    public String getName() {
      return name;
    }

    public void setName(String name) {
      this.name = name;
    }

    public int getValue() {
      return value;
    }

    public void setValue(int value) {
      this.value = value;
    }
  }
}
