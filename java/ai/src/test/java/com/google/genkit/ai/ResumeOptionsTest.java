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

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

/**
 * Unit tests for ResumeOptions.
 */
class ResumeOptionsTest {

  @Test
  void testBuilderWithRespond() {
    ToolResponse response1 = new ToolResponse("ref-1", "tool1", Map.of("result", "ok"));
    ToolResponse response2 = new ToolResponse("ref-2", "tool2", Map.of("result", "done"));

    ResumeOptions options = ResumeOptions.builder().respond(List.of(response1, response2)).build();

    assertNotNull(options.getRespond());
    assertEquals(2, options.getRespond().size());
    assertEquals("ref-1", options.getRespond().get(0).getRef());
    assertEquals("ref-2", options.getRespond().get(1).getRef());
    assertNull(options.getRestart());
  }

  @Test
  void testBuilderWithRestart() {
    ToolRequest request1 = new ToolRequest();
    request1.setName("tool1");
    request1.setRef("ref-1");

    ToolRequest request2 = new ToolRequest();
    request2.setName("tool2");
    request2.setRef("ref-2");

    ResumeOptions options = ResumeOptions.builder().restart(List.of(request1, request2)).build();

    assertNull(options.getRespond());
    assertNotNull(options.getRestart());
    assertEquals(2, options.getRestart().size());
    assertEquals("tool1", options.getRestart().get(0).getName());
    assertEquals("tool2", options.getRestart().get(1).getName());
  }

  @Test
  void testBuilderWithBothRespondAndRestart() {
    ToolResponse response = new ToolResponse("ref-1", "tool1", "result");
    ToolRequest request = new ToolRequest();
    request.setName("tool2");
    request.setRef("ref-2");

    ResumeOptions options = ResumeOptions.builder().respond(List.of(response)).restart(List.of(request)).build();

    assertNotNull(options.getRespond());
    assertEquals(1, options.getRespond().size());
    assertNotNull(options.getRestart());
    assertEquals(1, options.getRestart().size());
  }

  @Test
  void testDefaultConstructor() {
    ResumeOptions options = new ResumeOptions();

    assertNull(options.getRespond());
    assertNull(options.getRestart());
  }

  @Test
  void testSetters() {
    ResumeOptions options = new ResumeOptions();

    ToolResponse response = new ToolResponse("ref", "tool", "output");
    ToolRequest request = new ToolRequest();
    request.setName("tool");

    options.setRespond(List.of(response));
    options.setRestart(List.of(request));

    assertEquals(1, options.getRespond().size());
    assertEquals(1, options.getRestart().size());
  }

  @Test
  void testEmptyBuilder() {
    ResumeOptions options = ResumeOptions.builder().build();

    assertNull(options.getRespond());
    assertNull(options.getRestart());
  }

  @Test
  void testRespondWithEmptyList() {
    ResumeOptions options = ResumeOptions.builder().respond(new ArrayList<>()).build();

    assertNotNull(options.getRespond());
    assertTrue(options.getRespond().isEmpty());
  }

  @Test
  void testRestartWithEmptyList() {
    ResumeOptions options = ResumeOptions.builder().restart(new ArrayList<>()).build();

    assertNotNull(options.getRestart());
    assertTrue(options.getRestart().isEmpty());
  }
}
