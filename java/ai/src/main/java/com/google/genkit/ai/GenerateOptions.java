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

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Options for text generation requests.
 */
public class GenerateOptions {

  private final String model;
  private final String prompt;
  private final List<Message> messages;
  private final List<Document> docs;
  private final String system;
  private final List<Tool<?, ?>> tools;
  private final Object toolChoice;
  private final OutputConfig output;
  private final GenerationConfig config;
  private final Map<String, Object> context;
  private final Integer maxTurns;
  private final ResumeOptions resume;

  /**
   * Creates new GenerateOptions.
   *
   * @param model
   *            the model name
   * @param prompt
   *            simple text prompt
   * @param messages
   *            conversation messages
   * @param docs
   *            documents for context
   * @param system
   *            system prompt
   * @param tools
   *            available tools
   * @param toolChoice
   *            tool selection strategy
   * @param output
   *            output configuration
   * @param config
   *            generation configuration
   * @param context
   *            additional context
   * @param maxTurns
   *            maximum conversation turns
   * @param resume
   *            options for resuming after an interrupt
   */
  public GenerateOptions(String model, String prompt, List<Message> messages, List<Document> docs, String system,
      List<Tool<?, ?>> tools, Object toolChoice, OutputConfig output, GenerationConfig config,
      Map<String, Object> context, Integer maxTurns, ResumeOptions resume) {
    this.model = model;
    this.prompt = prompt;
    this.messages = messages;
    this.docs = docs;
    this.system = system;
    this.tools = tools;
    this.toolChoice = toolChoice;
    this.output = output;
    this.config = config;
    this.context = context;
    this.maxTurns = maxTurns;
    this.resume = resume;
  }

  /**
   * Creates a builder for GenerateOptions.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
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
   * Gets the text prompt.
   *
   * @return the prompt
   */
  public String getPrompt() {
    return prompt;
  }

  /**
   * Gets the conversation messages.
   *
   * @return the messages
   */
  public List<Message> getMessages() {
    return messages;
  }

  /**
   * Gets the documents for context.
   *
   * @return the documents
   */
  public List<Document> getDocs() {
    return docs;
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
   * Gets the available tools.
   *
   * @return the tools
   */
  public List<Tool<?, ?>> getTools() {
    return tools;
  }

  /**
   * Gets the tool choice strategy.
   *
   * @return the tool choice
   */
  public Object getToolChoice() {
    return toolChoice;
  }

  /**
   * Gets the output configuration.
   *
   * @return the output config
   */
  public OutputConfig getOutput() {
    return output;
  }

  /**
   * Gets the generation configuration.
   *
   * @return the config
   */
  public GenerationConfig getConfig() {
    return config;
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
   * Gets the maximum conversation turns.
   *
   * @return the max turns
   */
  public Integer getMaxTurns() {
    return maxTurns;
  }

  /**
   * Gets the resume options for continuing after an interrupt.
   *
   * @return the resume options, or null if not resuming
   */
  public ResumeOptions getResume() {
    return resume;
  }

  /**
   * Converts these options to a ModelRequest.
   *
   * @return a ModelRequest
   */
  public ModelRequest toModelRequest() {
    ModelRequest.Builder builder = ModelRequest.builder();

    if (messages != null && !messages.isEmpty()) {
      builder.messages(messages);
    } else if (prompt != null) {
      builder.addUserMessage(prompt);
    }

    if (system != null) {
      builder.addSystemMessage(system);
    }

    if (tools != null && !tools.isEmpty()) {
      List<ToolDefinition> toolDefs = tools.stream().map(Tool::getDefinition).collect(Collectors.toList());
      builder.tools(toolDefs);
    }

    if (config != null) {
      // Convert GenerationConfig to a Map for the ModelRequest
      Map<String, Object> configMap = new HashMap<>();
      if (config.getTemperature() != null) {
        configMap.put("temperature", config.getTemperature());
      }
      if (config.getMaxOutputTokens() != null) {
        configMap.put("maxOutputTokens", config.getMaxOutputTokens());
      }
      if (config.getTopP() != null) {
        configMap.put("topP", config.getTopP());
      }
      if (config.getTopK() != null) {
        configMap.put("topK", config.getTopK());
      }
      if (config.getStopSequences() != null) {
        configMap.put("stopSequences", config.getStopSequences());
      }
      if (config.getPresencePenalty() != null) {
        configMap.put("presencePenalty", config.getPresencePenalty());
      }
      if (config.getFrequencyPenalty() != null) {
        configMap.put("frequencyPenalty", config.getFrequencyPenalty());
      }
      if (config.getSeed() != null) {
        configMap.put("seed", config.getSeed());
      }
      // Include custom config for model-specific options (e.g., image generation)
      if (config.getCustom() != null) {
        configMap.putAll(config.getCustom());
      }
      builder.config(configMap);
    }

    if (output != null) {
      builder.output(output);
    }

    if (docs != null && !docs.isEmpty()) {
      builder.context(docs);
    }

    return builder.build();
  }

  /**
   * Builder for GenerateOptions.
   */
  public static class Builder {
    private String model;
    private String prompt;
    private List<Message> messages;
    private List<Document> docs;
    private String system;
    private List<Tool<?, ?>> tools;
    private Object toolChoice;
    private OutputConfig output;
    private GenerationConfig config;
    private Map<String, Object> context;
    private Integer maxTurns;
    private ResumeOptions resume;

    public Builder model(String model) {
      this.model = model;
      return this;
    }

    public Builder prompt(String prompt) {
      this.prompt = prompt;
      return this;
    }

    public Builder messages(List<Message> messages) {
      this.messages = messages;
      return this;
    }

    public Builder docs(List<Document> docs) {
      this.docs = docs;
      return this;
    }

    public Builder system(String system) {
      this.system = system;
      return this;
    }

    public Builder tools(List<Tool<?, ?>> tools) {
      this.tools = tools;
      return this;
    }

    public Builder toolChoice(Object toolChoice) {
      this.toolChoice = toolChoice;
      return this;
    }

    public Builder output(OutputConfig output) {
      this.output = output;
      return this;
    }

    public Builder config(GenerationConfig config) {
      this.config = config;
      return this;
    }

    public Builder context(Map<String, Object> context) {
      this.context = context;
      return this;
    }

    public Builder maxTurns(Integer maxTurns) {
      this.maxTurns = maxTurns;
      return this;
    }

    /**
     * Sets the resume options for continuing after an interrupt.
     *
     * @param resume
     *            the resume options
     * @return this builder
     */
    public Builder resume(ResumeOptions resume) {
      this.resume = resume;
      return this;
    }

    public GenerateOptions build() {
      return new GenerateOptions(model, prompt, messages, docs, system, tools, toolChoice, output, config,
          context, maxTurns, resume);
    }
  }
}
