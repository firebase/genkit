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
 * Unit tests for Agent.
 */
class AgentTest {

  /**
   * Helper to create a simple test tool.
   */
  private Tool<String, String> createTestTool(String name) {
    Map<String, Object> schema = new HashMap<>();
    schema.put("type", "string");
    return new Tool<>(name, "Test tool " + name, schema, schema, String.class, (ctx, input) -> "result");
  }

  @Test
  void testAgentCreation() {
    AgentConfig config = AgentConfig.builder().name("testAgent").description("Test agent description")
        .system("You are a test agent.").model("test-model").build();

    Agent agent = new Agent(config);

    assertEquals("testAgent", agent.getName());
    assertEquals("Test agent description", agent.getDescription());
    assertEquals("You are a test agent.", agent.getSystem());
    assertEquals("test-model", agent.getModel());
    assertEquals(config, agent.getConfig());
  }

  @Test
  void testAsTool() {
    AgentConfig config = AgentConfig.builder().name("delegateAgent").description("Handles delegated tasks").build();

    Agent agent = new Agent(config);
    Tool<Map<String, Object>, Agent.AgentTransferResult> tool = agent.asTool();

    assertNotNull(tool);
    assertEquals("delegateAgent", tool.getDefinition().getName());
    assertEquals("Handles delegated tasks", tool.getDefinition().getDescription());
    assertNotNull(tool.getInputSchema());
    assertNotNull(tool.getOutputSchema());
  }

  @Test
  void testGetToolDefinition() {
    AgentConfig config = AgentConfig.builder().name("myAgent").description("My agent").build();

    Agent agent = new Agent(config);
    ToolDefinition def = agent.getToolDefinition();

    assertEquals("myAgent", def.getName());
    assertEquals("My agent", def.getDescription());
    assertNotNull(def.getInputSchema());
  }

  @Test
  void testGetTools() {
    Tool<?, ?> tool1 = createTestTool("tool1");
    Tool<?, ?> tool2 = createTestTool("tool2");

    AgentConfig config = AgentConfig.builder().name("agent").tools(List.of(tool1, tool2)).build();

    Agent agent = new Agent(config);

    assertEquals(2, agent.getTools().size());
    assertTrue(agent.getTools().contains(tool1));
    assertTrue(agent.getTools().contains(tool2));
  }

  @Test
  void testGetAgents() {
    AgentConfig sub1 = AgentConfig.builder().name("sub1").build();
    AgentConfig sub2 = AgentConfig.builder().name("sub2").build();

    AgentConfig config = AgentConfig.builder().name("parent").agents(List.of(sub1, sub2)).build();

    Agent agent = new Agent(config);

    assertEquals(2, agent.getAgents().size());
  }

  @Test
  void testGetAllToolsWithNoSubAgents() {
    Tool<?, ?> tool1 = createTestTool("tool1");
    Tool<?, ?> tool2 = createTestTool("tool2");

    AgentConfig config = AgentConfig.builder().name("agent").tools(List.of(tool1, tool2)).build();

    Agent agent = new Agent(config);
    Map<String, Agent> registry = new HashMap<>();

    List<Tool<?, ?>> allTools = agent.getAllTools(registry);

    assertEquals(2, allTools.size());
  }

  @Test
  void testGetAllToolsWithSubAgents() {
    Tool<?, ?> parentTool = createTestTool("parentTool");

    AgentConfig subConfig = AgentConfig.builder().name("subAgent").description("Sub agent").build();

    AgentConfig config = AgentConfig.builder().name("parent").tools(List.of(parentTool)).agents(List.of(subConfig))
        .build();

    Agent parent = new Agent(config);
    Agent subAgent = new Agent(subConfig);

    Map<String, Agent> registry = new HashMap<>();
    registry.put("subAgent", subAgent);

    List<Tool<?, ?>> allTools = parent.getAllTools(registry);

    // Should have parent tool + sub-agent as tool
    assertEquals(2, allTools.size());
  }

  @Test
  void testAgentTransferResult() {
    Agent.AgentTransferResult result = new Agent.AgentTransferResult("targetAgent");

    assertEquals("targetAgent", result.getTransferredTo());
    assertTrue(result.isTransferred());
    assertTrue(result.toString().contains("targetAgent"));
  }

  @Test
  void testToString() {
    AgentConfig config = AgentConfig.builder().name("myAgent").build();

    Agent agent = new Agent(config);
    String str = agent.toString();

    assertTrue(str.contains("myAgent"));
    assertTrue(str.contains("Agent"));
  }

  @Test
  void testNullToolsAndAgents() {
    AgentConfig config = AgentConfig.builder().name("minimal").build();

    Agent agent = new Agent(config);

    assertNull(agent.getTools());
    assertNull(agent.getAgents());

    Map<String, Agent> registry = new HashMap<>();
    List<Tool<?, ?>> allTools = agent.getAllTools(registry);

    assertTrue(allTools.isEmpty());
  }
}
