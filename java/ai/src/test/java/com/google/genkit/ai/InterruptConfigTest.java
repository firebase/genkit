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
 * Unit tests for InterruptConfig.
 */
class InterruptConfigTest {

  @Test
  void testBuilderWithAllFields() {
    Map<String, Object> inputSchema = Map.of("type", "object", "properties", Map.of());
    Map<String, Object> outputSchema = Map.of("type", "string");

    InterruptConfig<TestInput, TestOutput> config = InterruptConfig.<TestInput, TestOutput>builder().name("confirm")
        .description("Asks for confirmation").inputType(TestInput.class).outputType(TestOutput.class)
        .inputSchema(inputSchema).outputSchema(outputSchema)
        .requestMetadata(input -> Map.of("action", input.action)).build();

    assertEquals("confirm", config.getName());
    assertEquals("Asks for confirmation", config.getDescription());
    assertEquals(TestInput.class, config.getInputType());
    assertEquals(TestOutput.class, config.getOutputType());
    assertEquals(inputSchema, config.getInputSchema());
    assertEquals(outputSchema, config.getOutputSchema());
    assertNotNull(config.getRequestMetadata());
  }

  @Test
  void testBuilderWithMinimalFields() {
    InterruptConfig<TestInput, TestOutput> config = InterruptConfig.<TestInput, TestOutput>builder().name("simple")
        .description("Simple interrupt").inputType(TestInput.class).outputType(TestOutput.class).build();

    assertEquals("simple", config.getName());
    assertEquals("Simple interrupt", config.getDescription());
    assertEquals(TestInput.class, config.getInputType());
    assertEquals(TestOutput.class, config.getOutputType());
    assertNull(config.getInputSchema());
    assertNull(config.getOutputSchema());
    assertNull(config.getRequestMetadata());
  }

  @Test
  void testRequestMetadataFunction() {
    InterruptConfig<TestInput, TestOutput> config = InterruptConfig.<TestInput, TestOutput>builder().name("confirm")
        .description("Confirm action").inputType(TestInput.class).outputType(TestOutput.class)
        .requestMetadata(input -> {
          Map<String, Object> metadata = new HashMap<>();
          metadata.put("action", input.action);
          metadata.put("amount", input.amount);
          return metadata;
        }).build();

    TestInput input = new TestInput();
    input.action = "purchase";
    input.amount = 100;

    Map<String, Object> metadata = config.getRequestMetadata().apply(input);

    assertEquals("purchase", metadata.get("action"));
    assertEquals(100, metadata.get("amount"));
  }

  @Test
  void testDefaultConstructor() {
    InterruptConfig<String, String> config = new InterruptConfig<>();

    assertNull(config.getName());
    assertNull(config.getDescription());
    assertNull(config.getInputType());
    assertNull(config.getOutputType());
    assertNull(config.getInputSchema());
    assertNull(config.getOutputSchema());
    assertNull(config.getRequestMetadata());
  }

  @Test
  void testSetters() {
    InterruptConfig<TestInput, TestOutput> config = new InterruptConfig<>();

    config.setName("test");
    config.setDescription("Test description");
    config.setInputType(TestInput.class);
    config.setOutputType(TestOutput.class);

    assertEquals("test", config.getName());
    assertEquals("Test description", config.getDescription());
    assertEquals(TestInput.class, config.getInputType());
    assertEquals(TestOutput.class, config.getOutputType());
  }

  // Test helper classes
  static class TestInput {
    String action;
    int amount;
  }

  static class TestOutput {
    boolean confirmed;
  }
}
