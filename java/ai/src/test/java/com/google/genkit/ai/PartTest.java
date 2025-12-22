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

import java.util.Map;

import org.junit.jupiter.api.Test;

/**
 * Unit tests for Part.
 */
class PartTest {

  @Test
  void testDefaultConstructor() {
    Part part = new Part();

    assertNull(part.getText());
    assertNull(part.getMedia());
    assertNull(part.getToolRequest());
    assertNull(part.getToolResponse());
    assertNull(part.getData());
    assertNull(part.getMetadata());
  }

  @Test
  void testTextPart() {
    Part part = Part.text("Hello, world!");

    assertEquals("Hello, world!", part.getText());
    assertNull(part.getMedia());
    assertNull(part.getToolRequest());
    assertNull(part.getToolResponse());
  }

  @Test
  void testTextPartWithEmptyString() {
    Part part = Part.text("");

    assertEquals("", part.getText());
  }

  @Test
  void testTextPartWithNull() {
    Part part = Part.text(null);

    assertNull(part.getText());
  }

  @Test
  void testMediaPart() {
    Part part = Part.media("image/png", "http://example.com/image.png");

    assertNull(part.getText());
    assertNotNull(part.getMedia());
    assertEquals("image/png", part.getMedia().getContentType());
    assertEquals("http://example.com/image.png", part.getMedia().getUrl());
  }

  @Test
  void testMediaPartWithDifferentTypes() {
    Part jpegPart = Part.media("image/jpeg", "http://example.com/photo.jpg");
    Part pdfPart = Part.media("application/pdf", "http://example.com/doc.pdf");
    Part audioPart = Part.media("audio/mp3", "http://example.com/sound.mp3");

    assertEquals("image/jpeg", jpegPart.getMedia().getContentType());
    assertEquals("application/pdf", pdfPart.getMedia().getContentType());
    assertEquals("audio/mp3", audioPart.getMedia().getContentType());
  }

  @Test
  void testToolRequestPart() {
    ToolRequest toolRequest = new ToolRequest();
    toolRequest.setName("calculator");
    toolRequest.setRef("ref-123");

    Part part = Part.toolRequest(toolRequest);

    assertNull(part.getText());
    assertNull(part.getMedia());
    assertNotNull(part.getToolRequest());
    assertEquals("calculator", part.getToolRequest().getName());
    assertEquals("ref-123", part.getToolRequest().getRef());
  }

  @Test
  void testToolResponsePart() {
    ToolResponse toolResponse = new ToolResponse();
    toolResponse.setName("calculator");
    toolResponse.setRef("ref-123");
    toolResponse.setOutput(Map.of("result", 42));

    Part part = Part.toolResponse(toolResponse);

    assertNull(part.getText());
    assertNull(part.getMedia());
    assertNull(part.getToolRequest());
    assertNotNull(part.getToolResponse());
    assertEquals("calculator", part.getToolResponse().getName());
  }

  @Test
  void testDataPart() {
    Map<String, Object> data = Map.of("key", "value", "number", 42);
    Part part = Part.data(data);

    assertNull(part.getText());
    assertNotNull(part.getData());
    assertEquals(data, part.getData());
  }

  @Test
  void testSetText() {
    Part part = new Part();
    part.setText("New text");

    assertEquals("New text", part.getText());
  }

  @Test
  void testSetMedia() {
    Part part = new Part();
    Media media = new Media("video/mp4", "http://example.com/video.mp4");
    part.setMedia(media);

    assertNotNull(part.getMedia());
    assertEquals("video/mp4", part.getMedia().getContentType());
  }

  @Test
  void testSetToolRequest() {
    Part part = new Part();
    ToolRequest toolRequest = new ToolRequest();
    toolRequest.setName("search");
    part.setToolRequest(toolRequest);

    assertNotNull(part.getToolRequest());
    assertEquals("search", part.getToolRequest().getName());
  }

  @Test
  void testSetToolResponse() {
    Part part = new Part();
    ToolResponse toolResponse = new ToolResponse();
    toolResponse.setName("search");
    part.setToolResponse(toolResponse);

    assertNotNull(part.getToolResponse());
    assertEquals("search", part.getToolResponse().getName());
  }

  @Test
  void testSetData() {
    Part part = new Part();
    Object data = Map.of("field", "value");
    part.setData(data);

    assertEquals(data, part.getData());
  }

  @Test
  void testSetMetadata() {
    Part part = new Part();
    Map<String, Object> metadata = Map.of("timestamp", "2025-01-01");
    part.setMetadata(metadata);

    assertEquals(metadata, part.getMetadata());
  }

  @Test
  void testPartWithMultipleTypes() {
    // A part should be able to have multiple types set, though typically only one
    // is used
    Part part = new Part();
    part.setText("text content");
    part.setMedia(new Media("image/png", "http://example.com/img.png"));

    assertEquals("text content", part.getText());
    assertNotNull(part.getMedia());
  }
}
