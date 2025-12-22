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

import java.util.List;

/**
 * Configuration for defining an agent (prompt as tool).
 *
 * <p>
 * An agent is a specialized prompt that can be used as a tool, enabling
 * multi-agent systems where one agent can delegate tasks to other specialized
 * agents.
 *
 * <p>
 * Example usage:
 *
 * <pre>{@code
 * // Define a specialized agent
 * AgentConfig reservationAgent = AgentConfig.builder().name("reservationAgent")
 * 		.description("Handles restaurant reservations")
 * 		.system("You are a reservation specialist. Help users make and manage reservations.").model("openai/gpt-4o")
 * 		.tools(List.of(reservationTool, cancelTool)).build();
 *
 * // Use as a tool in a triage agent
 * AgentConfig triageAgent = AgentConfig.builder().name("triageAgent")
 * 		.description("Routes customer requests to appropriate specialists")
 * 		.system("You are a customer service triage agent...").agents(List.of(reservationAgent, menuAgent)) // Sub-agents
 * 																											// as
 * 																											// tools
 * 		.build();
 * }</pre>
 */
public class AgentConfig {

  private String name;
  private String description;
  private String system;
  private String model;
  private List<Tool<?, ?>> tools;
  private List<AgentConfig> agents;
  private GenerationConfig config;
  private OutputConfig output;

  /** Default constructor. */
  public AgentConfig() {
  }

  /**
   * Gets the agent name.
   *
   * @return the name
   */
  public String getName() {
    return name;
  }

  /**
   * Sets the agent name.
   *
   * @param name
   *            the name
   */
  public void setName(String name) {
    this.name = name;
  }

  /**
   * Gets the description.
   *
   * @return the description
   */
  public String getDescription() {
    return description;
  }

  /**
   * Sets the description (used when agent is called as a tool).
   *
   * @param description
   *            the description
   */
  public void setDescription(String description) {
    this.description = description;
  }

  /**
   * Gets the system prompt.
   *
   * @return the system prompt
   */
  public String getSystem() {
    return system;
  }

  /**
   * Sets the system prompt.
   *
   * @param system
   *            the system prompt
   */
  public void setSystem(String system) {
    this.system = system;
  }

  /**
   * Gets the model name.
   *
   * @return the model name
   */
  public String getModel() {
    return model;
  }

  /**
   * Sets the model name.
   *
   * @param model
   *            the model name
   */
  public void setModel(String model) {
    this.model = model;
  }

  /**
   * Gets the tools available to this agent.
   *
   * @return the tools
   */
  public List<Tool<?, ?>> getTools() {
    return tools;
  }

  /**
   * Sets the tools available to this agent.
   *
   * @param tools
   *            the tools
   */
  public void setTools(List<Tool<?, ?>> tools) {
    this.tools = tools;
  }

  /**
   * Gets the sub-agents (agents that can be delegated to).
   *
   * @return the sub-agents
   */
  public List<AgentConfig> getAgents() {
    return agents;
  }

  /**
   * Sets the sub-agents.
   *
   * @param agents
   *            the sub-agents
   */
  public void setAgents(List<AgentConfig> agents) {
    this.agents = agents;
  }

  /**
   * Gets the generation config.
   *
   * @return the generation config
   */
  public GenerationConfig getConfig() {
    return config;
  }

  /**
   * Sets the generation config.
   *
   * @param config
   *            the generation config
   */
  public void setConfig(GenerationConfig config) {
    this.config = config;
  }

  /**
   * Gets the output config.
   *
   * @return the output config
   */
  public OutputConfig getOutput() {
    return output;
  }

  /**
   * Sets the output config.
   *
   * @param output
   *            the output config
   */
  public void setOutput(OutputConfig output) {
    this.output = output;
  }

  /**
   * Creates a new builder.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  /** Builder for AgentConfig. */
  public static class Builder {
    private String name;
    private String description;
    private String system;
    private String model;
    private List<Tool<?, ?>> tools;
    private List<AgentConfig> agents;
    private GenerationConfig config;
    private OutputConfig output;

    /**
     * Sets the agent name.
     *
     * @param name
     *            the name
     * @return this builder
     */
    public Builder name(String name) {
      this.name = name;
      return this;
    }

    /**
     * Sets the description.
     *
     * @param description
     *            the description
     * @return this builder
     */
    public Builder description(String description) {
      this.description = description;
      return this;
    }

    /**
     * Sets the system prompt.
     *
     * @param system
     *            the system prompt
     * @return this builder
     */
    public Builder system(String system) {
      this.system = system;
      return this;
    }

    /**
     * Sets the model name.
     *
     * @param model
     *            the model name
     * @return this builder
     */
    public Builder model(String model) {
      this.model = model;
      return this;
    }

    /**
     * Sets the tools available to this agent.
     *
     * @param tools
     *            the tools
     * @return this builder
     */
    public Builder tools(List<Tool<?, ?>> tools) {
      this.tools = tools;
      return this;
    }

    /**
     * Sets the sub-agents.
     *
     * @param agents
     *            the sub-agents
     * @return this builder
     */
    public Builder agents(List<AgentConfig> agents) {
      this.agents = agents;
      return this;
    }

    /**
     * Sets the generation config.
     *
     * @param config
     *            the generation config
     * @return this builder
     */
    public Builder config(GenerationConfig config) {
      this.config = config;
      return this;
    }

    /**
     * Sets the output config.
     *
     * @param output
     *            the output config
     * @return this builder
     */
    public Builder output(OutputConfig output) {
      this.output = output;
      return this;
    }

    /**
     * Builds the AgentConfig.
     *
     * @return the built config
     */
    public AgentConfig build() {
      AgentConfig agentConfig = new AgentConfig();
      agentConfig.setName(name);
      agentConfig.setDescription(description);
      agentConfig.setSystem(system);
      agentConfig.setModel(model);
      agentConfig.setTools(tools);
      agentConfig.setAgents(agents);
      agentConfig.setConfig(config);
      agentConfig.setOutput(output);
      return agentConfig;
    }
  }
}
