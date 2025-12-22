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

package com.google.genkit.ai.session;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

import com.google.genkit.ai.GenerationConfig;
import com.google.genkit.ai.OutputConfig;

/** Unit tests for ChatOptions. */
class ChatOptionsTest {

  @Test
  void testDefaultConstructor() {
    ChatOptions<String> options = new ChatOptions<>();

    assertNull(options.getModel());
    assertNull(options.getSystem());
    assertNull(options.getConfig());
    assertNull(options.getTools());
    assertNull(options.getOutput());
    assertNull(options.getContext());
    assertNull(options.getMaxTurns());
  }

  @Test
  void testSetAndGetModel() {
    ChatOptions<String> options = new ChatOptions<>();
    options.setModel("gpt-4");

    assertEquals("gpt-4", options.getModel());
  }

  @Test
  void testSetAndGetSystem() {
    ChatOptions<String> options = new ChatOptions<>();
    options.setSystem("You are a helpful assistant.");

    assertEquals("You are a helpful assistant.", options.getSystem());
  }

  @Test
  void testSetAndGetConfig() {
    ChatOptions<String> options = new ChatOptions<>();
    GenerationConfig config = GenerationConfig.builder().temperature(0.7).build();
    options.setConfig(config);

    assertSame(config, options.getConfig());
  }

  @Test
  void testSetAndGetOutput() {
    ChatOptions<String> options = new ChatOptions<>();
    OutputConfig output = new OutputConfig();
    options.setOutput(output);

    assertSame(output, options.getOutput());
  }

  @Test
  void testSetAndGetContext() {
    ChatOptions<String> options = new ChatOptions<>();
    Map<String, Object> context = new HashMap<>();
    context.put("key1", "value1");
    context.put("key2", 42);
    options.setContext(context);

    assertNotNull(options.getContext());
    assertEquals("value1", options.getContext().get("key1"));
    assertEquals(42, options.getContext().get("key2"));
  }

  @Test
  void testSetAndGetMaxTurns() {
    ChatOptions<String> options = new ChatOptions<>();
    options.setMaxTurns(10);

    assertEquals(10, options.getMaxTurns());
  }

  @Test
  void testBuilderEmpty() {
    ChatOptions<String> options = ChatOptions.<String>builder().build();

    assertNull(options.getModel());
    assertNull(options.getSystem());
    assertNull(options.getConfig());
    assertNull(options.getTools());
    assertNull(options.getOutput());
    assertNull(options.getContext());
    assertNull(options.getMaxTurns());
  }

  @Test
  void testBuilderWithModel() {
    ChatOptions<String> options = ChatOptions.<String>builder().model("claude-3").build();

    assertEquals("claude-3", options.getModel());
  }

  @Test
  void testBuilderWithSystem() {
    ChatOptions<String> options = ChatOptions.<String>builder().system("You are a coding assistant.").build();

    assertEquals("You are a coding assistant.", options.getSystem());
  }

  @Test
  void testBuilderWithConfig() {
    GenerationConfig config = GenerationConfig.builder().temperature(0.5).maxOutputTokens(100).build();

    ChatOptions<String> options = ChatOptions.<String>builder().config(config).build();

    assertSame(config, options.getConfig());
  }

  @Test
  void testBuilderWithOutput() {
    OutputConfig output = new OutputConfig();

    ChatOptions<String> options = ChatOptions.<String>builder().output(output).build();

    assertSame(output, options.getOutput());
  }

  @Test
  void testBuilderWithContext() {
    Map<String, Object> context = new HashMap<>();
    context.put("userId", "user123");

    ChatOptions<String> options = ChatOptions.<String>builder().context(context).build();

    assertNotNull(options.getContext());
    assertEquals("user123", options.getContext().get("userId"));
  }

  @Test
  void testBuilderWithMaxTurns() {
    ChatOptions<String> options = ChatOptions.<String>builder().maxTurns(5).build();

    assertEquals(5, options.getMaxTurns());
  }

  @Test
  void testBuilderWithAllOptions() {
    GenerationConfig config = GenerationConfig.builder().temperature(0.7).build();
    OutputConfig output = new OutputConfig();
    Map<String, Object> context = new HashMap<>();
    context.put("key", "value");

    ChatOptions<String> options = ChatOptions.<String>builder().model("gemini-pro")
        .system("You are an expert programmer.").config(config).output(output).context(context).maxTurns(20)
        .build();

    assertEquals("gemini-pro", options.getModel());
    assertEquals("You are an expert programmer.", options.getSystem());
    assertSame(config, options.getConfig());
    assertSame(output, options.getOutput());
    assertEquals("value", options.getContext().get("key"));
    assertEquals(20, options.getMaxTurns());
  }

  @Test
  void testBuilderChaining() {
    ChatOptions.Builder<String> builder = ChatOptions.<String>builder();

    // Test that builder methods return the builder for chaining
    assertSame(builder, builder.model("model"));
    assertSame(builder, builder.system("system"));
    assertSame(builder, builder.config(GenerationConfig.builder().build()));
    assertSame(builder, builder.output(new OutputConfig()));
    assertSame(builder, builder.context(new HashMap<>()));
    assertSame(builder, builder.maxTurns(10));
  }

  @Test
  void testLongSystemPrompt() {
    String longPrompt = "You are a helpful assistant. " + "You should always be polite and professional. "
        + "Never provide harmful or misleading information. " + "If you don't know something, say so. "
        + "Always cite your sources when possible.";

    ChatOptions<String> options = ChatOptions.<String>builder().system(longPrompt).build();

    assertEquals(longPrompt, options.getSystem());
  }

  @Test
  void testMultipleBuilds() {
    ChatOptions.Builder<String> builder = ChatOptions.<String>builder().model("model1").maxTurns(5);

    ChatOptions<String> options1 = builder.build();
    assertEquals("model1", options1.getModel());
    assertEquals(5, options1.getMaxTurns());

    // Modify and build again
    builder.model("model2").maxTurns(10);
    ChatOptions<String> options2 = builder.build();

    assertEquals("model2", options2.getModel());
    assertEquals(10, options2.getMaxTurns());
  }

  @Test
  void testWithComplexState() {
    // Test with a custom state type
    ChatOptions<TestState> options = ChatOptions.<TestState>builder().model("test-model")
        .system("Test system prompt").maxTurns(15).build();

    assertEquals("test-model", options.getModel());
    assertEquals("Test system prompt", options.getSystem());
    assertEquals(15, options.getMaxTurns());
  }

  @Test
  void testEmptyContext() {
    ChatOptions<String> options = ChatOptions.<String>builder().context(new HashMap<>()).build();

    assertNotNull(options.getContext());
    assertTrue(options.getContext().isEmpty());
  }

  @Test
  void testZeroMaxTurns() {
    ChatOptions<String> options = ChatOptions.<String>builder().maxTurns(0).build();

    assertEquals(0, options.getMaxTurns());
  }

  /** Simple test state class. */
  static class TestState {
    private final String name;
    private final int value;

    TestState(String name, int value) {
      this.name = name;
      this.value = value;
    }

    String getName() {
      return name;
    }

    int getValue() {
      return value;
    }
  }
}
