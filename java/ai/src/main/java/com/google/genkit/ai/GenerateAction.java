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
import java.util.UUID;
import java.util.function.Consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.genkit.core.*;
import com.google.genkit.core.tracing.SpanMetadata;
import com.google.genkit.core.tracing.Tracer;

/**
 * GenerateAction is a utility action that provides a unified interface for
 * generating content from AI models. It's registered at /util/generate and is
 * used by the Dev UI.
 */
public class GenerateAction implements Action<GenerateAction.GenerateActionOptions, ModelResponse, ModelResponseChunk> {

  private static final Logger logger = LoggerFactory.getLogger(GenerateAction.class);
  private static final ObjectMapper objectMapper = new ObjectMapper();

  private final Registry registry;

  public GenerateAction(Registry registry) {
    this.registry = registry;
  }

  /**
   * Defines and registers the generate utility action.
   *
   * @param registry
   *            the registry to register with
   * @return the generate action
   */
  public static GenerateAction define(Registry registry) {
    GenerateAction action = new GenerateAction(registry);
    registry.registerAction("/util/generate", action);
    logger.debug("Registered utility action: /util/generate");
    return action;
  }

  @Override
  public String getName() {
    return "generate";
  }

  @Override
  public ActionType getType() {
    return ActionType.UTIL;
  }

  @Override
  public ActionDesc getDesc() {
    return ActionDesc.builder().name("generate").type(ActionType.UTIL)
        .description("Utility action for generating content from AI models").build();
  }

  @Override
  public ModelResponse run(ActionContext ctx, GenerateActionOptions options) throws GenkitException {
    return run(ctx, options, null);
  }

  @Override
  public ModelResponse run(ActionContext ctx, GenerateActionOptions options,
      Consumer<ModelResponseChunk> streamCallback) throws GenkitException {
    if (options == null) {
      throw new GenkitException("GenerateActionOptions cannot be null");
    }

    String modelName = options.getModel();
    if (modelName == null || modelName.isEmpty()) {
      throw new GenkitException("Model name is required");
    }

    // Resolve the model action key
    String modelKey = resolveModelKey(modelName);

    // Look up the model in the registry
    Action<?, ?, ?> action = registry.lookupAction(modelKey);
    if (action == null) {
      throw new GenkitException("Model not found: " + modelName + " (key: " + modelKey + ")");
    }

    if (!(action instanceof Model)) {
      throw new GenkitException("Action is not a model: " + modelKey);
    }

    Model model = (Model) action;

    // Build the model request from the options
    ModelRequest request = buildModelRequest(options);

    logger.debug("Generating with model: {}", modelKey);

    // Create span metadata for the model call
    SpanMetadata spanMetadata = SpanMetadata.builder().name(modelName).type(ActionType.MODEL.getValue())
        .subtype("model").build();

    String flowName = ctx.getFlowName();
    if (flowName != null) {
      spanMetadata.getAttributes().put("genkit:metadata:flow:name", flowName);
    }

    // Run the model wrapped in a span
    return Tracer.runInNewSpan(ctx, spanMetadata, request, (spanCtx, req) -> {
      ActionContext newCtx = ctx.withSpanContext(spanCtx);
      if (streamCallback != null && model.supportsStreaming()) {
        return model.run(newCtx, req, streamCallback);
      } else {
        return model.run(newCtx, req);
      }
    });
  }

  @Override
  public JsonNode runJson(ActionContext ctx, JsonNode input, Consumer<JsonNode> streamCallback)
      throws GenkitException {
    try {
      GenerateActionOptions options = objectMapper.treeToValue(input, GenerateActionOptions.class);
      Consumer<ModelResponseChunk> chunkCallback = null;
      if (streamCallback != null) {
        chunkCallback = chunk -> {
          try {
            streamCallback.accept(objectMapper.valueToTree(chunk));
          } catch (Exception e) {
            logger.error("Error streaming chunk", e);
          }
        };
      }
      ModelResponse response = run(ctx, options, chunkCallback);
      return objectMapper.valueToTree(response);
    } catch (GenkitException e) {
      throw e;
    } catch (Exception e) {
      throw new GenkitException("Failed to process generate action", e);
    }
  }

  @Override
  public ActionRunResult<JsonNode> runJsonWithTelemetry(ActionContext ctx, JsonNode input,
      Consumer<JsonNode> streamCallback) throws GenkitException {
    String traceId = UUID.randomUUID().toString();
    JsonNode result = runJson(ctx, input, streamCallback);
    return new ActionRunResult<>(result, traceId, null);
  }

  @Override
  public Map<String, Object> getInputSchema() {
    Map<String, Object> schema = new HashMap<>();
    schema.put("type", "object");
    Map<String, Object> props = new HashMap<>();
    props.put("model", Map.of("type", "string"));
    props.put("messages", Map.of("type", "array"));
    props.put("config", Map.of("type", "object"));
    props.put("tools", Map.of("type", "array"));
    schema.put("properties", props);
    schema.put("required", List.of("messages"));
    return schema;
  }

  @Override
  public Map<String, Object> getOutputSchema() {
    Map<String, Object> schema = new HashMap<>();
    schema.put("type", "object");
    return schema;
  }

  @Override
  public Map<String, Object> getMetadata() {
    Map<String, Object> metadata = new HashMap<>();
    metadata.put("type", "util");
    return metadata;
  }

  @Override
  public void register(Registry registry) {
    registry.registerAction("/util/generate", this);
  }

  /**
   * Resolves a model name to a registry key. Handles formats like "openai/gpt-4o"
   * -> "/model/openai/gpt-4o"
   */
  private String resolveModelKey(String modelName) {
    if (modelName.startsWith("/model/")) {
      return modelName;
    }
    return "/model/" + modelName;
  }

  /**
   * Builds a ModelRequest from GenerateActionOptions.
   */
  private ModelRequest buildModelRequest(GenerateActionOptions options) {
    ModelRequest.Builder builder = ModelRequest.builder();

    if (options.getMessages() != null) {
      builder.messages(options.getMessages());
    }

    if (options.getConfig() != null) {
      // Convert GenerationConfig to Map<String, Object>
      Map<String, Object> configMap = objectMapper.convertValue(options.getConfig(), Map.class);
      builder.config(configMap);
    }

    if (options.getTools() != null && !options.getTools().isEmpty()) {
      // Resolve tools from registry
      List<ToolDefinition> toolDefs = options.getTools().stream().map(this::resolveToolDefinition)
          .filter(t -> t != null).toList();
      builder.tools(toolDefs);
    }

    if (options.getOutput() != null) {
      builder.output(options.getOutput());
    }

    return builder.build();
  }

  /**
   * Resolves a tool name to its definition from the registry.
   */
  private ToolDefinition resolveToolDefinition(String toolName) {
    String toolKey = toolName.startsWith("/tool/") ? toolName : "/tool/" + toolName;
    Action<?, ?, ?> action = registry.lookupAction(toolKey);
    if (action == null) {
      logger.warn("Tool not found: {}", toolName);
      return null;
    }

    // Get tool definition from the action's desc
    ActionDesc desc = action.getDesc();
    return new ToolDefinition(desc.getName(), desc.getDescription(), desc.getInputSchema(), null);
  }

  /**
   * Options for the generate utility action.
   */
  @JsonIgnoreProperties(ignoreUnknown = true)
  public static class GenerateActionOptions {

    @JsonProperty("model")
    private String model;

    @JsonProperty("messages")
    private List<Message> messages;

    @JsonProperty("tools")
    private List<String> tools;

    @JsonProperty("resources")
    private List<String> resources;

    @JsonProperty("toolChoice")
    private String toolChoice;

    @JsonProperty("config")
    private GenerationConfig config;

    @JsonProperty("output")
    private OutputConfig output;

    @JsonProperty("docs")
    private List<Document> docs;

    @JsonProperty("returnToolRequests")
    private Boolean returnToolRequests;

    @JsonProperty("maxTurns")
    private Integer maxTurns;

    @JsonProperty("stepName")
    private String stepName;

    public String getModel() {
      return model;
    }

    public void setModel(String model) {
      this.model = model;
    }

    public List<Message> getMessages() {
      return messages;
    }

    public void setMessages(List<Message> messages) {
      this.messages = messages;
    }

    public List<String> getTools() {
      return tools;
    }

    public void setTools(List<String> tools) {
      this.tools = tools;
    }

    public List<String> getResources() {
      return resources;
    }

    public void setResources(List<String> resources) {
      this.resources = resources;
    }

    public String getToolChoice() {
      return toolChoice;
    }

    public void setToolChoice(String toolChoice) {
      this.toolChoice = toolChoice;
    }

    public GenerationConfig getConfig() {
      return config;
    }

    public void setConfig(GenerationConfig config) {
      this.config = config;
    }

    public OutputConfig getOutput() {
      return output;
    }

    public void setOutput(OutputConfig output) {
      this.output = output;
    }

    public List<Document> getDocs() {
      return docs;
    }

    public void setDocs(List<Document> docs) {
      this.docs = docs;
    }

    public Boolean getReturnToolRequests() {
      return returnToolRequests;
    }

    public void setReturnToolRequests(Boolean returnToolRequests) {
      this.returnToolRequests = returnToolRequests;
    }

    public Integer getMaxTurns() {
      return maxTurns;
    }

    public void setMaxTurns(Integer maxTurns) {
      this.maxTurns = maxTurns;
    }

    public String getStepName() {
      return stepName;
    }

    public void setStepName(String stepName) {
      this.stepName = stepName;
    }
  }
}
