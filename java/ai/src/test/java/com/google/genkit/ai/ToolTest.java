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
 * Unit tests for ToolRequest and ToolResponse.
 */
class ToolTest {

  @Test
  void testToolRequestDefaultConstructor() {
    ToolRequest request = new ToolRequest();

    assertNull(request.getName());
    assertNull(request.getRef());
    assertNull(request.getInput());
  }

  @Test
  void testToolRequestSetName() {
    ToolRequest request = new ToolRequest();
    request.setName("calculator");

    assertEquals("calculator", request.getName());
  }

  @Test
  void testToolRequestSetRef() {
    ToolRequest request = new ToolRequest();
    request.setRef("ref-abc-123");

    assertEquals("ref-abc-123", request.getRef());
  }

  @Test
  void testToolRequestSetInput() {
    ToolRequest request = new ToolRequest();
    Map<String, Object> input = Map.of("a", 5, "b", 3, "operation", "add");
    request.setInput(input);

    assertEquals(input, request.getInput());
    @SuppressWarnings("unchecked")
    Map<String, Object> inputMap = (Map<String, Object>) request.getInput();
    assertEquals(5, inputMap.get("a"));
    assertEquals(3, inputMap.get("b"));
    assertEquals("add", inputMap.get("operation"));
  }

  @Test
  void testToolRequestCompleteSetup() {
    ToolRequest request = new ToolRequest();
    request.setName("search");
    request.setRef("search-001");
    request.setInput(Map.of("query", "Genkit documentation"));

    assertEquals("search", request.getName());
    assertEquals("search-001", request.getRef());
    @SuppressWarnings("unchecked")
    Map<String, Object> inputMap = (Map<String, Object>) request.getInput();
    assertEquals("Genkit documentation", inputMap.get("query"));
  }

  @Test
  void testToolResponseDefaultConstructor() {
    ToolResponse response = new ToolResponse();

    assertNull(response.getName());
    assertNull(response.getRef());
    assertNull(response.getOutput());
  }

  @Test
  void testToolResponseSetName() {
    ToolResponse response = new ToolResponse();
    response.setName("calculator");

    assertEquals("calculator", response.getName());
  }

  @Test
  void testToolResponseSetRef() {
    ToolResponse response = new ToolResponse();
    response.setRef("ref-abc-123");

    assertEquals("ref-abc-123", response.getRef());
  }

  @Test
  void testToolResponseSetOutput() {
    ToolResponse response = new ToolResponse();
    Map<String, Object> output = Map.of("result", 8, "success", true);
    response.setOutput(output);

    assertEquals(output, response.getOutput());
    @SuppressWarnings("unchecked")
    Map<String, Object> outputMap = (Map<String, Object>) response.getOutput();
    assertEquals(8, outputMap.get("result"));
    assertEquals(true, outputMap.get("success"));
  }

  @Test
  void testToolResponseCompleteSetup() {
    ToolResponse response = new ToolResponse();
    response.setName("calculator");
    response.setRef("calc-001");
    response.setOutput(Map.of("result", 42));

    assertEquals("calculator", response.getName());
    assertEquals("calc-001", response.getRef());
    @SuppressWarnings("unchecked")
    Map<String, Object> outputMap = (Map<String, Object>) response.getOutput();
    assertEquals(42, outputMap.get("result"));
  }

  @Test
  void testToolRequestAndResponseMatching() {
    String toolName = "weather";
    String ref = "weather-req-001";

    ToolRequest request = new ToolRequest();
    request.setName(toolName);
    request.setRef(ref);
    request.setInput(Map.of("location", "San Francisco"));

    ToolResponse response = new ToolResponse();
    response.setName(toolName);
    response.setRef(ref);
    response.setOutput(Map.of("temperature", 72, "condition", "sunny"));

    // Request and response should have matching name and ref
    assertEquals(request.getName(), response.getName());
    assertEquals(request.getRef(), response.getRef());
  }

  @Test
  void testToolRequestWithComplexInput() {
    ToolRequest request = new ToolRequest();
    request.setName("database_query");
    request.setInput(Map.of("table", "users", "fields", new String[]{"id", "name", "email"}, "limit", 10, "where",
        Map.of("active", true)));

    assertEquals("database_query", request.getName());
    @SuppressWarnings("unchecked")
    Map<String, Object> inputMap = (Map<String, Object>) request.getInput();
    assertEquals("users", inputMap.get("table"));
    assertEquals(10, inputMap.get("limit"));
  }

  @Test
  void testToolResponseWithNullOutput() {
    ToolResponse response = new ToolResponse();
    response.setName("void_operation");
    response.setRef("void-001");
    response.setOutput(null);

    assertEquals("void_operation", response.getName());
    assertNull(response.getOutput());
  }
}
