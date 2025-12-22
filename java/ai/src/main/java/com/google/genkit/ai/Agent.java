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

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Represents an agent that can be used as a tool in multi-agent systems.
 *
 * <p>
 * An Agent wraps an AgentConfig and provides a Tool interface for delegation.
 * When the model calls an agent as a tool, the agent's configuration (system
 * prompt, model, tools) is applied to the conversation, effectively
 * "transferring" control to the specialized agent.
 *
 * <p>
 * Example usage:
 *
 * <pre>{@code
 * // Define a specialized agent
 * Agent reservationAgent = genkit
 * 		.defineAgent(AgentConfig.builder().name("reservationAgent").description("Handles restaurant reservations")
 * 				.system("You are a reservation specialist...").tools(List.of(reservationTool)).build());
 *
 * // Use in a parent agent
 * Agent triageAgent = genkit.defineAgent(AgentConfig.builder().name("triageAgent").description("Routes requests")
 * 		.system("Route customer requests to specialists").agents(List.of(reservationAgent.getConfig())).build());
 *
 * // Start chat with triage agent
 * Chat chat = genkit.chat(triageAgent);
 * }</pre>
 */
public class Agent {

  private final AgentConfig config;
  private final Tool<Map<String, Object>, AgentTransferResult> asTool;

  /**
   * Creates a new Agent.
   *
   * @param config
   *            the agent configuration
   */
  @SuppressWarnings("unchecked")
  public Agent(AgentConfig config) {
    this.config = config;
    this.asTool = createAgentTool();
  }

  /**
   * Gets the agent configuration.
   *
   * @return the config
   */
  public AgentConfig getConfig() {
    return config;
  }

  /**
   * Gets the agent name.
   *
   * @return the name
   */
  public String getName() {
    return config.getName();
  }

  /**
   * Gets the agent description.
   *
   * @return the description
   */
  public String getDescription() {
    return config.getDescription();
  }

  /**
   * Gets the system prompt.
   *
   * @return the system prompt
   */
  public String getSystem() {
    return config.getSystem();
  }

  /**
   * Gets the model name.
   *
   * @return the model name
   */
  public String getModel() {
    return config.getModel();
  }

  /**
   * Gets the tools available to this agent.
   *
   * @return the tools
   */
  public List<Tool<?, ?>> getTools() {
    return config.getTools();
  }

  /**
   * Gets the sub-agents.
   *
   * @return the sub-agents
   */
  public List<AgentConfig> getAgents() {
    return config.getAgents();
  }

  /**
   * Gets all tools including sub-agent tools for handoff pattern.
   *
   * <p>
   * This method collects all tools that should be available to the agent,
   * including the agent's own tools and sub-agents as tools (for handoff). When a
   * sub-agent tool is called, the Chat will handle the handoff by switching
   * context to that agent.
   *
   * @param agentRegistry
   *            map of agent name to Agent instance
   * @return combined list of all tools from this agent and sub-agents as tools
   */
  public List<Tool<?, ?>> getAllTools(Map<String, Agent> agentRegistry) {
    List<Tool<?, ?>> allTools = new ArrayList<>();

    // Add this agent's direct tools
    if (config.getTools() != null) {
      allTools.addAll(config.getTools());
    }

    // Add sub-agents as tools (for handoff pattern)
    if (config.getAgents() != null) {
      for (AgentConfig agentConfig : config.getAgents()) {
        Agent agent = agentRegistry.get(agentConfig.getName());
        if (agent != null) {
          // Add the sub-agent as a tool - when called, Chat will handle the handoff
          allTools.add(agent.asTool());
        }
      }
    }

    return allTools;
  }

  /**
   * Returns this agent as a tool that can be used by other agents.
   *
   * @return the agent as a tool
   */
  public Tool<Map<String, Object>, AgentTransferResult> asTool() {
    return asTool;
  }

  /**
   * Gets the tool definition for this agent.
   *
   * @return the tool definition
   */
  public ToolDefinition getToolDefinition() {
    return asTool.getDefinition();
  }

  /** Creates the agent-as-tool wrapper. */
  @SuppressWarnings("unchecked")
  private Tool<Map<String, Object>, AgentTransferResult> createAgentTool() {
    // OpenAI requires "properties" field even if empty
    Map<String, Object> inputSchema = new HashMap<>();
    inputSchema.put("type", "object");
    inputSchema.put("properties", new HashMap<String, Object>());
    inputSchema.put("additionalProperties", true);

    Map<String, Object> outputSchema = new HashMap<>();
    outputSchema.put("type", "object");
    outputSchema.put("properties",
        Map.of("transferredTo", Map.of("type", "string"), "transferred", Map.of("type", "boolean")));

    return new Tool<>(config.getName(),
        config.getDescription() != null ? config.getDescription() : "Transfer to " + config.getName(),
        inputSchema, outputSchema, (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, input) -> {
          // Throw handoff exception to signal the chat to switch to this agent
          throw new AgentHandoffException(config.getName(), config, input);
        });
  }

  /** Result of an agent transfer. */
  public static class AgentTransferResult {
    private final String transferredTo;
    private final boolean transferred;

    public AgentTransferResult(String agentName) {
      this.transferredTo = agentName;
      this.transferred = true;
    }

    public String getTransferredTo() {
      return transferredTo;
    }

    public boolean isTransferred() {
      return transferred;
    }

    @Override
    public String toString() {
      return "transferred to " + transferredTo;
    }
  }

  @Override
  public String toString() {
    return "Agent{" + "name='" + config.getName() + '\'' + '}';
  }
}
