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
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

/**
 * Unit tests for Message.
 */
class MessageTest {

  @Test
  void testDefaultConstructor() {
    Message message = new Message();

    assertNull(message.getRole());
    assertNotNull(message.getContent());
    assertTrue(message.getContent().isEmpty());
  }

  @Test
  void testConstructorWithRoleAndContent() {
    List<Part> content = Collections.singletonList(Part.text("Hello"));
    Message message = new Message(Role.USER, content);

    assertEquals(Role.USER, message.getRole());
    assertEquals(1, message.getContent().size());
    assertEquals("Hello", message.getContent().get(0).getText());
  }

  @Test
  void testUserMessage() {
    Message message = Message.user("Hello, world!");

    assertEquals(Role.USER, message.getRole());
    assertEquals(1, message.getContent().size());
    assertEquals("Hello, world!", message.getText());
  }

  @Test
  void testSystemMessage() {
    Message message = Message.system("You are a helpful assistant.");

    assertEquals(Role.SYSTEM, message.getRole());
    assertEquals(1, message.getContent().size());
    assertEquals("You are a helpful assistant.", message.getText());
  }

  @Test
  void testModelMessage() {
    Message message = Message.model("I can help you with that.");

    assertEquals(Role.MODEL, message.getRole());
    assertEquals(1, message.getContent().size());
    assertEquals("I can help you with that.", message.getText());
  }

  @Test
  void testToolMessage() {
    List<Part> content = Arrays.asList(Part.text("Tool response 1"), Part.text("Tool response 2"));
    Message message = Message.tool(content);

    assertEquals(Role.TOOL, message.getRole());
    assertEquals(2, message.getContent().size());
  }

  @Test
  void testGetText() {
    List<Part> content = Arrays.asList(Part.text("Hello, "), Part.text("world!"));
    Message message = new Message(Role.USER, content);

    assertEquals("Hello, world!", message.getText());
  }

  @Test
  void testGetTextWithNullContent() {
    Message message = new Message();
    message.setContent(null);

    assertEquals("", message.getText());
  }

  @Test
  void testGetTextWithEmptyContent() {
    Message message = new Message(Role.USER, Collections.emptyList());

    assertEquals("", message.getText());
  }

  @Test
  void testSetRole() {
    Message message = new Message();
    message.setRole(Role.MODEL);

    assertEquals(Role.MODEL, message.getRole());
  }

  @Test
  void testSetContent() {
    Message message = new Message();
    List<Part> content = Collections.singletonList(Part.text("New content"));
    message.setContent(content);

    assertEquals(1, message.getContent().size());
    assertEquals("New content", message.getContent().get(0).getText());
  }

  @Test
  void testSetMetadata() {
    Message message = new Message();
    Map<String, Object> metadata = new HashMap<>();
    metadata.put("key", "value");
    message.setMetadata(metadata);

    assertEquals(metadata, message.getMetadata());
  }

  @Test
  void testConstructorCopiesContentList() {
    List<Part> original = Arrays.asList(Part.text("Hello"));
    Message message = new Message(Role.USER, original);

    // Modifying original list should not affect message
    assertNotSame(original, message.getContent());
  }

  @Test
  void testNullContentInConstructor() {
    Message message = new Message(Role.USER, null);

    assertNotNull(message.getContent());
    assertTrue(message.getContent().isEmpty());
  }

  @Test
  void testGetTextSkipsNonTextParts() {
    List<Part> content = Arrays.asList(Part.text("Hello"), Part.media("image/png", "http://example.com/image.png"),
        Part.text(" World"));
    Message message = new Message(Role.USER, content);

    assertEquals("Hello World", message.getText());
  }
}
