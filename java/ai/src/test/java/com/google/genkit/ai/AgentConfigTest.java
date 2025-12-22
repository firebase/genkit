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
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

/**
 * Unit tests for AgentConfig.
 */
class AgentConfigTest {

  /**
   * Helper to create a simple test tool.
   */
  private Tool<String, String> createTestTool(String name) {
    Map<String, Object> schema = new HashMap<>();
    schema.put("type", "string");
    return new Tool<>(name, "Test tool " + name, schema, schema, String.class, (ctx, input) -> "result");
  }

  @Test
  void testBuilderWithAllFields() {
    Tool<?, ?> tool1 = createTestTool("tool1");
    Tool<?, ?> tool2 = createTestTool("tool2");

    AgentConfig subAgent = AgentConfig.builder().name("subAgent").description("Sub agent").build();

    GenerationConfig genConfig = GenerationConfig.builder().temperature(0.7).build();

    OutputConfig outputConfig = new OutputConfig();
    outputConfig.setFormat(OutputFormat.JSON);

    AgentConfig config = AgentConfig.builder().name("mainAgent").description("Main agent description")
        .system("You are a helpful assistant.").model("openai/gpt-4o").tools(List.of(tool1, tool2))
        .agents(List.of(subAgent)).config(genConfig).output(outputConfig).build();

    assertEquals("mainAgent", config.getName());
    assertEquals("Main agent description", config.getDescription());
    assertEquals("You are a helpful assistant.", config.getSystem());
    assertEquals("openai/gpt-4o", config.getModel());
    assertEquals(2, config.getTools().size());
    assertEquals(1, config.getAgents().size());
    assertEquals("subAgent", config.getAgents().get(0).getName());
    assertEquals(genConfig, config.getConfig());
    assertEquals(outputConfig, config.getOutput());
  }

  @Test
  void testBuilderWithMinimalFields() {
    AgentConfig config = AgentConfig.builder().name("simpleAgent").description("A simple agent").build();

    assertEquals("simpleAgent", config.getName());
    assertEquals("A simple agent", config.getDescription());
    assertNull(config.getSystem());
    assertNull(config.getModel());
    assertNull(config.getTools());
    assertNull(config.getAgents());
    assertNull(config.getConfig());
    assertNull(config.getOutput());
  }

  @Test
  void testDefaultConstructor() {
    AgentConfig config = new AgentConfig();

    assertNull(config.getName());
    assertNull(config.getDescription());
    assertNull(config.getSystem());
    assertNull(config.getModel());
    assertNull(config.getTools());
    assertNull(config.getAgents());
    assertNull(config.getConfig());
    assertNull(config.getOutput());
  }

  @Test
  void testSetters() {
    AgentConfig config = new AgentConfig();
    Tool<?, ?> tool = createTestTool("testTool");
    AgentConfig subAgent = AgentConfig.builder().name("sub").build();
    GenerationConfig genConfig = GenerationConfig.builder().build();
    OutputConfig outputConfig = new OutputConfig();

    config.setName("agent");
    config.setDescription("desc");
    config.setSystem("system");
    config.setModel("model");
    config.setTools(List.of(tool));
    config.setAgents(List.of(subAgent));
    config.setConfig(genConfig);
    config.setOutput(outputConfig);

    assertEquals("agent", config.getName());
    assertEquals("desc", config.getDescription());
    assertEquals("system", config.getSystem());
    assertEquals("model", config.getModel());
    assertEquals(1, config.getTools().size());
    assertEquals(1, config.getAgents().size());
    assertEquals(genConfig, config.getConfig());
    assertEquals(outputConfig, config.getOutput());
  }

  @Test
  void testNestedAgents() {
    AgentConfig level3 = AgentConfig.builder().name("level3").description("Level 3 agent").build();

    AgentConfig level2 = AgentConfig.builder().name("level2").description("Level 2 agent").agents(List.of(level3))
        .build();

    AgentConfig level1 = AgentConfig.builder().name("level1").description("Level 1 agent").agents(List.of(level2))
        .build();

    assertEquals("level1", level1.getName());
    assertEquals(1, level1.getAgents().size());
    assertEquals("level2", level1.getAgents().get(0).getName());
    assertEquals(1, level1.getAgents().get(0).getAgents().size());
    assertEquals("level3", level1.getAgents().get(0).getAgents().get(0).getName());
  }

  @Test
  void testMultipleToolsAndAgents() {
    Tool<?, ?> tool1 = createTestTool("tool1");
    Tool<?, ?> tool2 = createTestTool("tool2");
    Tool<?, ?> tool3 = createTestTool("tool3");

    AgentConfig sub1 = AgentConfig.builder().name("sub1").build();
    AgentConfig sub2 = AgentConfig.builder().name("sub2").build();

    AgentConfig config = AgentConfig.builder().name("main").tools(List.of(tool1, tool2, tool3))
        .agents(List.of(sub1, sub2)).build();

    assertEquals(3, config.getTools().size());
    assertEquals(2, config.getAgents().size());
  }
}
