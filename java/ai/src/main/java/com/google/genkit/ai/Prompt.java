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
import java.util.Map;
import java.util.function.BiFunction;
import java.util.function.Consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.google.genkit.core.Action;
import com.google.genkit.core.ActionContext;
import com.google.genkit.core.ActionDesc;
import com.google.genkit.core.ActionRunResult;
import com.google.genkit.core.ActionType;
import com.google.genkit.core.GenkitException;
import com.google.genkit.core.JsonUtils;
import com.google.genkit.core.Registry;

/**
 * Prompt is a template that generates ModelRequests from input variables.
 *
 * Prompts are registered as actions and can be rendered with different input
 * values to create model requests.
 *
 * @param <I>
 *            the input type for the prompt
 */
public class Prompt<I> implements Action<I, ModelRequest, Void> {

  private final String name;
  private final String model;
  private final String template;
  private final Map<String, Object> inputSchema;
  private final GenerationConfig config;
  private final BiFunction<ActionContext, I, ModelRequest> renderer;
  private final Map<String, Object> metadata;
  private final Class<I> inputClass;

  /**
   * Creates a new Prompt.
   *
   * @param name
   *            the prompt name
   * @param model
   *            the default model name
   * @param template
   *            the prompt template
   * @param inputSchema
   *            the input JSON schema
   * @param config
   *            the default generation config
   * @param inputClass
   *            the input class for JSON deserialization
   * @param renderer
   *            the function that renders the prompt
   */
  public Prompt(String name, String model, String template, Map<String, Object> inputSchema, GenerationConfig config,
      Class<I> inputClass, BiFunction<ActionContext, I, ModelRequest> renderer) {
    this.name = name;
    this.model = model;
    this.template = template;
    this.inputSchema = inputSchema;
    this.config = config;
    this.inputClass = inputClass;
    this.renderer = renderer;

    // Build metadata structure to match Go SDK format
    // The metadata.type identifies this as an executable-prompt
    // The metadata.prompt contains the prompt-specific metadata
    this.metadata = new HashMap<>();
    this.metadata.put("type", ActionType.EXECUTABLE_PROMPT.getValue());

    // Build the prompt sub-object with detailed metadata
    Map<String, Object> promptMetadata = new HashMap<>();
    promptMetadata.put("name", name);
    promptMetadata.put("model", model);
    promptMetadata.put("template", template);
    if (inputSchema != null) {
      promptMetadata.put("input", Map.of("schema", inputSchema));
    }
    if (config != null) {
      promptMetadata.put("config", config);
    }
    this.metadata.put("prompt", promptMetadata);
  }

  /**
   * Creates a builder for Prompt.
   *
   * @param <I>
   *            the input type
   * @return a new builder
   */
  public static <I> Builder<I> builder() {
    return new Builder<>();
  }

  @Override
  public String getName() {
    return name;
  }

  @Override
  public ActionType getType() {
    return ActionType.EXECUTABLE_PROMPT;
  }

  @Override
  public ActionDesc getDesc() {
    return ActionDesc.builder().type(ActionType.EXECUTABLE_PROMPT).name(name).inputSchema(inputSchema)
        .metadata(metadata).build();
  }

  @Override
  public ModelRequest run(ActionContext ctx, I input) throws GenkitException {
    try {
      return renderer.apply(ctx, input);
    } catch (Exception e) {
      throw new GenkitException("Prompt rendering failed: " + e.getMessage(), e);
    }
  }

  @Override
  public ModelRequest run(ActionContext ctx, I input, Consumer<Void> streamCallback) throws GenkitException {
    return run(ctx, input);
  }

  @Override
  @SuppressWarnings("unchecked")
  public JsonNode runJson(ActionContext ctx, JsonNode input, Consumer<JsonNode> streamCallback)
      throws GenkitException {
    I typedInput = inputClass != null ? JsonUtils.fromJsonNode(input, inputClass) : (I) input;
    ModelRequest output = run(ctx, typedInput);
    return JsonUtils.toJsonNode(output);
  }

  @Override
  public ActionRunResult<JsonNode> runJsonWithTelemetry(ActionContext ctx, JsonNode input,
      Consumer<JsonNode> streamCallback) throws GenkitException {
    JsonNode result = runJson(ctx, input, streamCallback);
    return new ActionRunResult<>(result, null, null);
  }

  @Override
  public Map<String, Object> getInputSchema() {
    return inputSchema;
  }

  @Override
  public Map<String, Object> getOutputSchema() {
    return null;
  }

  @Override
  public Map<String, Object> getMetadata() {
    return metadata;
  }

  @Override
  public void register(Registry registry) {
    registry.registerAction(ActionType.EXECUTABLE_PROMPT.keyFromName(name), this);
  }

  /**
   * Gets the default model name.
   *
   * @return the model name
   */
  public String getModel() {
    return model;
  }

  /**
   * Gets the prompt template.
   *
   * @return the template
   */
  public String getTemplate() {
    return template;
  }

  /**
   * Gets the default generation config.
   *
   * @return the config
   */
  public GenerationConfig getConfig() {
    return config;
  }

  /**
   * Builder for Prompt.
   *
   * @param <I>
   *            the input type
   */
  public static class Builder<I> {
    private String name;
    private String model;
    private String template;
    private Map<String, Object> inputSchema;
    private GenerationConfig config;
    private Class<I> inputClass;
    private BiFunction<ActionContext, I, ModelRequest> renderer;

    public Builder<I> name(String name) {
      this.name = name;
      return this;
    }

    public Builder<I> model(String model) {
      this.model = model;
      return this;
    }

    public Builder<I> template(String template) {
      this.template = template;
      return this;
    }

    public Builder<I> inputSchema(Map<String, Object> inputSchema) {
      this.inputSchema = inputSchema;
      return this;
    }

    public Builder<I> config(GenerationConfig config) {
      this.config = config;
      return this;
    }

    public Builder<I> inputClass(Class<I> inputClass) {
      this.inputClass = inputClass;
      return this;
    }

    public Builder<I> renderer(BiFunction<ActionContext, I, ModelRequest> renderer) {
      this.renderer = renderer;
      return this;
    }

    public Prompt<I> build() {
      if (name == null) {
        throw new IllegalStateException("Prompt name is required");
      }
      if (renderer == null) {
        throw new IllegalStateException("Prompt renderer is required");
      }
      return new Prompt<>(name, model, template, inputSchema, config, inputClass, renderer);
    }
  }
}
