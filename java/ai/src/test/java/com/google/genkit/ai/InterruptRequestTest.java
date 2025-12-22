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

import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

/**
 * Unit tests for InterruptRequest.
 */
class InterruptRequestTest {

  @Test
  void testConstructor() {
    ToolRequest toolRequest = new ToolRequest();
    toolRequest.setName("confirm");
    toolRequest.setRef("ref-123");
    toolRequest.setInput(Map.of("action", "purchase"));

    Map<String, Object> metadata = new HashMap<>();
    metadata.put("amount", 100);

    InterruptRequest request = new InterruptRequest(toolRequest, metadata);

    assertEquals(toolRequest, request.getToolRequest());
    assertNotNull(request.getMetadata());
    assertEquals(100, request.getMetadata().get("amount"));
    assertTrue(request.isInterrupt());
  }

  @Test
  void testConstructorWithNullMetadata() {
    ToolRequest toolRequest = new ToolRequest();
    toolRequest.setName("confirm");

    InterruptRequest request = new InterruptRequest(toolRequest, null);

    assertNotNull(request.getMetadata());
    assertTrue(request.isInterrupt());
  }

  @Test
  void testRespond() {
    ToolRequest toolRequest = new ToolRequest();
    toolRequest.setName("confirm");
    toolRequest.setRef("ref-123");

    InterruptRequest request = new InterruptRequest(toolRequest, new HashMap<>());

    // Respond with confirmation
    Map<String, Object> response = Map.of("confirmed", true);
    ToolResponse toolResponse = request.respond(response);

    assertEquals("ref-123", toolResponse.getRef());
    assertEquals("confirm", toolResponse.getName());
    assertEquals(response, toolResponse.getOutput());
  }

  @Test
  void testRestart() {
    ToolRequest toolRequest = new ToolRequest();
    toolRequest.setName("confirm");
    toolRequest.setRef("ref-123");
    toolRequest.setInput(Map.of("action", "purchase"));

    InterruptRequest request = new InterruptRequest(toolRequest, new HashMap<>());

    // Restart returns the original tool request
    ToolRequest restartRequest = request.restart();

    assertEquals("confirm", restartRequest.getName());
    assertEquals("ref-123", restartRequest.getRef());
    assertEquals(Map.of("action", "purchase"), restartRequest.getInput());
  }

  @Test
  void testRestartWithModifiedInput() {
    ToolRequest toolRequest = new ToolRequest();
    toolRequest.setName("confirm");
    toolRequest.setRef("ref-123");
    toolRequest.setInput(Map.of("action", "purchase", "amount", 100));

    InterruptRequest request = new InterruptRequest(toolRequest, new HashMap<>());

    // Restart with modified input
    Map<String, Object> newMetadata = Map.of("reason", "retry");
    Map<String, Object> newInput = Map.of("action", "purchase", "amount", 50);

    ToolRequest restartRequest = request.restart(newMetadata, newInput);

    assertEquals("confirm", restartRequest.getName());
    // Should have same ref
    assertEquals("ref-123", restartRequest.getRef());
    // But new input
    assertEquals(newInput, restartRequest.getInput());
  }

  @Test
  void testRestartWithNullNewInput() {
    ToolRequest toolRequest = new ToolRequest();
    toolRequest.setName("confirm");
    toolRequest.setRef("ref-123");
    Object originalInput = Map.of("action", "purchase");
    toolRequest.setInput(originalInput);

    InterruptRequest request = new InterruptRequest(toolRequest, new HashMap<>());

    // Restart with null new input should keep original
    ToolRequest restartRequest = request.restart(null, null);

    assertEquals(originalInput, restartRequest.getInput());
  }

  @Test
  void testMetadataContainsInterruptFlag() {
    ToolRequest toolRequest = new ToolRequest();
    toolRequest.setName("test");

    Map<String, Object> metadata = new HashMap<>();
    metadata.put("custom", "value");

    InterruptRequest request = new InterruptRequest(toolRequest, metadata);

    assertTrue((Boolean) request.getMetadata().get("interrupt"));
    assertEquals("value", request.getMetadata().get("custom"));
  }

  @Test
  void testGetToolName() {
    ToolRequest toolRequest = new ToolRequest();
    toolRequest.setName("myInterrupt");

    InterruptRequest request = new InterruptRequest(toolRequest, new HashMap<>());

    assertEquals("myInterrupt", request.getToolRequest().getName());
  }
}
