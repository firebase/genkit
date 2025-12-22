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

import static org.junit.jupiter.api.Assertions.*;

import java.util.Arrays;
import java.util.Map;

import org.junit.jupiter.api.Test;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Unit tests for JSON serialization and deserialization of AI types.
 */
class JsonSerializationTest {

  private final ObjectMapper objectMapper;

  JsonSerializationTest() {
    objectMapper = new ObjectMapper();
    objectMapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
  }

  @Test
  void testMessageSerialization() throws Exception {
    Message message = Message.user("Hello, world!");

    String json = objectMapper.writeValueAsString(message);

    assertNotNull(json);
    assertTrue(json.contains("\"role\":\"user\""));
    assertTrue(json.contains("\"content\""));
  }

  @Test
  void testMessageDeserialization() throws Exception {
    String json = "{\"role\":\"user\",\"content\":[{\"text\":\"Hello\"}]}";

    Message message = objectMapper.readValue(json, Message.class);

    assertEquals(Role.USER, message.getRole());
    assertEquals("Hello", message.getText());
  }

  @Test
  void testMessageRoundTrip() throws Exception {
    Message original = Message.system("You are a helpful assistant.");

    String json = objectMapper.writeValueAsString(original);
    Message deserialized = objectMapper.readValue(json, Message.class);

    assertEquals(original.getRole(), deserialized.getRole());
    assertEquals(original.getText(), deserialized.getText());
  }

  @Test
  void testPartTextSerialization() throws Exception {
    Part part = Part.text("Some text content");

    String json = objectMapper.writeValueAsString(part);

    assertTrue(json.contains("\"text\":\"Some text content\""));
  }

  @Test
  void testPartMediaSerialization() throws Exception {
    Part part = Part.media("image/png", "http://example.com/img.png");

    String json = objectMapper.writeValueAsString(part);

    assertTrue(json.contains("\"media\""));
    assertTrue(json.contains("\"contentType\":\"image/png\""));
    assertTrue(json.contains("\"url\":\"http://example.com/img.png\""));
  }

  @Test
  void testPartDeserialization() throws Exception {
    String json = "{\"text\":\"Hello\"}";

    Part part = objectMapper.readValue(json, Part.class);

    assertEquals("Hello", part.getText());
  }

  @Test
  void testDocumentSerialization() throws Exception {
    Document doc = Document.fromText("Document content", Map.of("source", "test"));

    String json = objectMapper.writeValueAsString(doc);

    assertTrue(json.contains("\"content\""));
    assertTrue(json.contains("\"metadata\""));
    assertTrue(json.contains("\"source\":\"test\""));
  }

  @Test
  void testDocumentDeserialization() throws Exception {
    String json = "{\"content\":[{\"text\":\"Doc text\"}],\"metadata\":{\"key\":\"value\"}}";

    Document doc = objectMapper.readValue(json, Document.class);

    assertEquals("Doc text", doc.text());
    assertEquals("value", doc.getMetadata().get("key"));
  }

  @Test
  void testRoleSerialization() throws Exception {
    String userJson = objectMapper.writeValueAsString(Role.USER);
    String modelJson = objectMapper.writeValueAsString(Role.MODEL);
    String systemJson = objectMapper.writeValueAsString(Role.SYSTEM);
    String toolJson = objectMapper.writeValueAsString(Role.TOOL);

    assertEquals("\"user\"", userJson);
    assertEquals("\"model\"", modelJson);
    assertEquals("\"system\"", systemJson);
    assertEquals("\"tool\"", toolJson);
  }

  @Test
  void testRoleDeserialization() throws Exception {
    assertEquals(Role.USER, objectMapper.readValue("\"user\"", Role.class));
    assertEquals(Role.MODEL, objectMapper.readValue("\"model\"", Role.class));
    assertEquals(Role.SYSTEM, objectMapper.readValue("\"system\"", Role.class));
    assertEquals(Role.TOOL, objectMapper.readValue("\"tool\"", Role.class));
  }

  @Test
  void testRoleAssistantDeserialization() throws Exception {
    // "assistant" should map to MODEL for compatibility
    assertEquals(Role.MODEL, objectMapper.readValue("\"assistant\"", Role.class));
  }

  @Test
  void testMediaSerialization() throws Exception {
    Media media = new Media("video/mp4", "http://example.com/video.mp4");

    String json = objectMapper.writeValueAsString(media);

    assertTrue(json.contains("\"contentType\":\"video/mp4\""));
    assertTrue(json.contains("\"url\":\"http://example.com/video.mp4\""));
  }

  @Test
  void testMediaDeserialization() throws Exception {
    String json = "{\"contentType\":\"audio/mp3\",\"url\":\"http://example.com/audio.mp3\"}";

    Media media = objectMapper.readValue(json, Media.class);

    assertEquals("audio/mp3", media.getContentType());
    assertEquals("http://example.com/audio.mp3", media.getUrl());
  }

  @Test
  void testToolRequestSerialization() throws Exception {
    ToolRequest request = new ToolRequest();
    request.setName("calculator");
    request.setRef("calc-001");
    request.setInput(Map.of("a", 5, "b", 3));

    String json = objectMapper.writeValueAsString(request);

    assertTrue(json.contains("\"name\":\"calculator\""));
    assertTrue(json.contains("\"ref\":\"calc-001\""));
    assertTrue(json.contains("\"input\""));
  }

  @Test
  void testToolResponseSerialization() throws Exception {
    ToolResponse response = new ToolResponse();
    response.setName("calculator");
    response.setRef("calc-001");
    response.setOutput(Map.of("result", 8));

    String json = objectMapper.writeValueAsString(response);

    assertTrue(json.contains("\"name\":\"calculator\""));
    assertTrue(json.contains("\"output\""));
    assertTrue(json.contains("\"result\":8"));
  }

  @Test
  void testComplexMessageSerialization() throws Exception {
    Message message = new Message(Role.USER, Arrays.asList(Part.text("Look at this image: "),
        Part.media("image/png", "http://example.com/img.png")));
    message.setMetadata(Map.of("timestamp", "2025-01-01T12:00:00Z"));

    String json = objectMapper.writeValueAsString(message);
    Message deserialized = objectMapper.readValue(json, Message.class);

    assertEquals(Role.USER, deserialized.getRole());
    assertEquals(2, deserialized.getContent().size());
    assertNotNull(deserialized.getMetadata());
  }

  @Test
  void testNullValuesExcluded() throws Exception {
    Part part = new Part();
    part.setText("Only text");

    String json = objectMapper.writeValueAsString(part);

    assertTrue(json.contains("\"text\":\"Only text\""));
    // Null values should be excluded with @JsonInclude(NON_NULL)
    assertFalse(json.contains("\"media\":null"));
  }
}
