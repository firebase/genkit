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

import java.util.List;
import java.util.Map;

import com.google.genkit.ai.Agent;
import com.google.genkit.ai.GenerationConfig;
import com.google.genkit.ai.OutputConfig;
import com.google.genkit.ai.Tool;

/**
 * ChatOptions provides configuration options for creating a Chat instance.
 *
 * @param <S>
 *            the type of the session state
 */
public class ChatOptions<S> {

  private String model;
  private String system;
  private List<Tool<?, ?>> tools;
  private OutputConfig output;
  private GenerationConfig config;
  private Map<String, Object> context;
  private Integer maxTurns;
  private Map<String, Agent> agentRegistry;

  /**
   * Default constructor.
   */
  public ChatOptions() {
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
   * Gets the available tools.
   *
   * @return the tools
   */
  public List<Tool<?, ?>> getTools() {
    return tools;
  }

  /**
   * Sets the available tools.
   *
   * @param tools
   *            the tools
   */
  public void setTools(List<Tool<?, ?>> tools) {
    this.tools = tools;
  }

  /**
   * Gets the output configuration.
   *
   * @return the output configuration
   */
  public OutputConfig getOutput() {
    return output;
  }

  /**
   * Sets the output configuration.
   *
   * @param output
   *            the output configuration
   */
  public void setOutput(OutputConfig output) {
    this.output = output;
  }

  /**
   * Gets the generation configuration.
   *
   * @return the generation configuration
   */
  public GenerationConfig getConfig() {
    return config;
  }

  /**
   * Sets the generation configuration.
   *
   * @param config
   *            the generation configuration
   */
  public void setConfig(GenerationConfig config) {
    this.config = config;
  }

  /**
   * Gets the additional context.
   *
   * @return the context
   */
  public Map<String, Object> getContext() {
    return context;
  }

  /**
   * Sets the additional context.
   *
   * @param context
   *            the context
   */
  public void setContext(Map<String, Object> context) {
    this.context = context;
  }

  /**
   * Gets the maximum conversation turns.
   *
   * @return the max turns
   */
  public Integer getMaxTurns() {
    return maxTurns;
  }

  /**
   * Sets the maximum conversation turns.
   *
   * @param maxTurns
   *            the max turns
   */
  public void setMaxTurns(Integer maxTurns) {
    this.maxTurns = maxTurns;
  }

  /**
   * Gets the agent registry for multi-agent handoffs.
   *
   * @return the agent registry
   */
  public Map<String, Agent> getAgentRegistry() {
    return agentRegistry;
  }

  /**
   * Sets the agent registry for multi-agent handoffs.
   *
   * @param agentRegistry
   *            the agent registry
   */
  public void setAgentRegistry(Map<String, Agent> agentRegistry) {
    this.agentRegistry = agentRegistry;
  }

  /**
   * Creates a builder for ChatOptions.
   *
   * @param <S>
   *            the state type
   * @return a new builder
   */
  public static <S> Builder<S> builder() {
    return new Builder<>();
  }

  /**
   * Builder for ChatOptions.
   *
   * @param <S>
   *            the state type
   */
  public static class Builder<S> {
    private String model;
    private String system;
    private List<Tool<?, ?>> tools;
    private OutputConfig output;
    private GenerationConfig config;
    private Map<String, Object> context;
    private Integer maxTurns;
    private Map<String, Agent> agentRegistry;

    /**
     * Sets the model name.
     *
     * @param model
     *            the model name
     * @return this builder
     */
    public Builder<S> model(String model) {
      this.model = model;
      return this;
    }

    /**
     * Sets the system prompt.
     *
     * @param system
     *            the system prompt
     * @return this builder
     */
    public Builder<S> system(String system) {
      this.system = system;
      return this;
    }

    /**
     * Sets the available tools.
     *
     * @param tools
     *            the tools
     * @return this builder
     */
    public Builder<S> tools(List<Tool<?, ?>> tools) {
      this.tools = tools;
      return this;
    }

    /**
     * Sets the output configuration.
     *
     * @param output
     *            the output configuration
     * @return this builder
     */
    public Builder<S> output(OutputConfig output) {
      this.output = output;
      return this;
    }

    /**
     * Sets the generation configuration.
     *
     * @param config
     *            the generation configuration
     * @return this builder
     */
    public Builder<S> config(GenerationConfig config) {
      this.config = config;
      return this;
    }

    /**
     * Sets the additional context.
     *
     * @param context
     *            the context
     * @return this builder
     */
    public Builder<S> context(Map<String, Object> context) {
      this.context = context;
      return this;
    }

    /**
     * Sets the maximum conversation turns.
     *
     * @param maxTurns
     *            the max turns
     * @return this builder
     */
    public Builder<S> maxTurns(Integer maxTurns) {
      this.maxTurns = maxTurns;
      return this;
    }

    /**
     * Sets the agent registry for multi-agent handoffs.
     *
     * @param agentRegistry
     *            the agent registry
     * @return this builder
     */
    public Builder<S> agentRegistry(Map<String, Agent> agentRegistry) {
      this.agentRegistry = agentRegistry;
      return this;
    }

    /**
     * Builds the ChatOptions.
     *
     * @return the built ChatOptions
     */
    public ChatOptions<S> build() {
      ChatOptions<S> options = new ChatOptions<>();
      options.setModel(model);
      options.setSystem(system);
      options.setTools(tools);
      options.setOutput(output);
      options.setConfig(config);
      options.setContext(context);
      options.setMaxTurns(maxTurns);
      options.setAgentRegistry(agentRegistry);
      return options;
    }
  }
}
