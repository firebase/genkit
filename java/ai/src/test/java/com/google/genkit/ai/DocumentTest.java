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
 * Unit tests for Document.
 */
class DocumentTest {

  @Test
  void testDefaultConstructor() {
    Document doc = new Document();

    assertNotNull(doc.getContent());
    assertTrue(doc.getContent().isEmpty());
    assertNotNull(doc.getMetadata());
    assertTrue(doc.getMetadata().isEmpty());
  }

  @Test
  void testConstructorWithText() {
    Document doc = new Document("Hello, world!");

    assertEquals(1, doc.getContent().size());
    assertEquals("Hello, world!", doc.text());
    assertNotNull(doc.getMetadata());
  }

  @Test
  void testConstructorWithParts() {
    List<Part> parts = Arrays.asList(Part.text("Part 1"), Part.text("Part 2"));
    Document doc = new Document(parts);

    assertEquals(2, doc.getContent().size());
    assertEquals("Part 1Part 2", doc.text());
  }

  @Test
  void testConstructorWithNullParts() {
    Document doc = new Document((List<Part>) null);

    assertNotNull(doc.getContent());
    assertTrue(doc.getContent().isEmpty());
  }

  @Test
  void testFromText() {
    Document doc = Document.fromText("Test content");

    assertEquals(1, doc.getContent().size());
    assertEquals("Test content", doc.text());
  }

  @Test
  void testFromTextWithMetadata() {
    Map<String, Object> metadata = new HashMap<>();
    metadata.put("source", "test");
    metadata.put("page", 1);

    Document doc = Document.fromText("Test content", metadata);

    assertEquals("Test content", doc.text());
    assertEquals("test", doc.getMetadata().get("source"));
    assertEquals(1, doc.getMetadata().get("page"));
  }

  @Test
  void testFromTextWithNullMetadata() {
    Document doc = Document.fromText("Test content", null);

    assertEquals("Test content", doc.text());
    assertNotNull(doc.getMetadata());
    assertTrue(doc.getMetadata().isEmpty());
  }

  @Test
  void testGetText() {
    Document doc = new Document();
    doc.setContent(Arrays.asList(Part.text("Hello, "), Part.text("world!")));

    assertEquals("Hello, world!", doc.text());
  }

  @Test
  void testGetTextWithEmptyContent() {
    Document doc = new Document();

    assertEquals("", doc.text());
  }

  @Test
  void testGetTextWithNullContent() {
    Document doc = new Document();
    doc.setContent(null);

    assertEquals("", doc.text());
  }

  @Test
  void testGetTextSkipsNonTextParts() {
    Document doc = new Document();
    doc.setContent(Arrays.asList(Part.text("Text"), Part.media("image/png", "http://example.com/img.png"),
        Part.text(" content")));

    assertEquals("Text content", doc.text());
  }

  @Test
  void testSetContent() {
    Document doc = new Document();
    List<Part> content = Collections.singletonList(Part.text("New content"));
    doc.setContent(content);

    assertEquals(1, doc.getContent().size());
    assertEquals("New content", doc.text());
  }

  @Test
  void testSetMetadata() {
    Document doc = new Document("Test");
    Map<String, Object> metadata = Map.of("key", "value");
    doc.setMetadata(metadata);

    assertEquals(metadata, doc.getMetadata());
  }

  @Test
  void testAddPart() {
    Document doc = new Document("Initial");
    doc.getContent().add(Part.text(" Added"));

    assertEquals("Initial Added", doc.text());
  }

  @Test
  void testMetadataOperations() {
    Document doc = new Document("Test");

    doc.getMetadata().put("author", "John");
    doc.getMetadata().put("date", "2025-01-01");

    assertEquals("John", doc.getMetadata().get("author"));
    assertEquals("2025-01-01", doc.getMetadata().get("date"));
  }

  @Test
  void testDocumentWithMedia() {
    Document doc = new Document();
    doc.setContent(
        Arrays.asList(Part.text("Description: "), Part.media("image/png", "http://example.com/image.png")));

    assertEquals(2, doc.getContent().size());
    assertEquals("Description: ", doc.text());
    assertNotNull(doc.getContent().get(1).getMedia());
  }

  @Test
  void testEmptyTextDocument() {
    Document doc = new Document("");

    assertEquals(1, doc.getContent().size());
    assertEquals("", doc.text());
  }
}
