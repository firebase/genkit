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

package com.google.genkit.prompt;

import java.util.Map;
import java.util.function.Consumer;

import com.google.genkit.ai.*;
import com.google.genkit.core.ActionContext;
import com.google.genkit.core.GenkitException;
import com.google.genkit.core.Registry;

/**
 * ExecutablePrompt wraps a DotPrompt and provides direct generation
 * capabilities.
 * 
 * <p>
 * This class allows prompts to be called directly for generation, similar to
 * the JavaScript API: `const response = await helloPrompt({ name: 'John' });`
 * 
 * <p>
 * In Java, this becomes:
 * 
 * <pre>{@code
 * ExecutablePrompt<HelloInput> helloPrompt = genkit.prompt("hello", HelloInput.class);
 * ModelResponse response = helloPrompt.generate(new HelloInput("John"));
 * }</pre>
 * 
 * <p>
 * Or for streaming:
 * 
 * <pre>{@code
 * helloPrompt.stream(input, chunk -> System.out.println(chunk.getText()));
 * }</pre>
 *
 * @param <I>
 *            the input type for the prompt
 */
public class ExecutablePrompt<I> {

  private final DotPrompt<I> dotPrompt;
  private final Registry registry;
  private final Class<I> inputClass;
  private GenerateFunction generateFunction;

  /**
   * Functional interface for the generate function. This allows ExecutablePrompt
   * to use Genkit.generate() for tool/interrupt support.
   */
  @FunctionalInterface
  public interface GenerateFunction {
    ModelResponse generate(GenerateOptions options) throws GenkitException;
  }

  /**
   * Creates a new ExecutablePrompt.
   *
   * @param dotPrompt
   *            the underlying DotPrompt
   * @param registry
   *            the Genkit registry
   * @param inputClass
   *            the input class for type checking
   */
  public ExecutablePrompt(DotPrompt<I> dotPrompt, Registry registry, Class<I> inputClass) {
    this.dotPrompt = dotPrompt;
    this.registry = registry;
    this.inputClass = inputClass;
  }

  /**
   * Sets the generate function to use Genkit.generate() for tool/interrupt
   * support.
   *
   * @param generateFunction
   *            the generate function
   * @return this for chaining
   */
  public ExecutablePrompt<I> withGenerateFunction(GenerateFunction generateFunction) {
    this.generateFunction = generateFunction;
    return this;
  }

  /**
   * Generates a response using the default model specified in the prompt.
   *
   * @param input
   *            the prompt input
   * @return the model response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse generate(I input) throws GenkitException {
    return generate(input, null);
  }

  /**
   * Generates a response with custom options.
   *
   * <p>
   * If a generateFunction is set (via Genkit), this uses Genkit.generate() which
   * supports tools and interrupts. Otherwise, it calls the model directly.
   *
   * @param input
   *            the prompt input
   * @param options
   *            optional generation options to override prompt defaults
   * @return the model response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse generate(I input, GenerateOptions options) throws GenkitException {
    ModelRequest request = dotPrompt.toModelRequest(input);
    String modelName = resolveModel(options);

    // If we have a generate function (from Genkit), use it for tool/interrupt
    // support
    if (generateFunction != null) {
      GenerateOptions.Builder genOptions = GenerateOptions.builder().model(modelName)
          .messages(request.getMessages());

      // Add system message if present
      if (request.getMessages() != null && !request.getMessages().isEmpty()) {
        Message systemMsg = request.getMessages().stream().filter(m -> m.getRole() == Role.SYSTEM).findFirst()
            .orElse(null);
        if (systemMsg != null && systemMsg.getContent() != null && !systemMsg.getContent().isEmpty()) {
          genOptions.system(systemMsg.getContent().get(0).getText());
        }
      }

      // Add tools if present in options
      if (options != null && options.getTools() != null) {
        genOptions.tools(options.getTools());
      }

      // Add resume options if present
      if (options != null && options.getResume() != null) {
        genOptions.resume(options.getResume());
      }

      // Add config if present
      if (options != null && options.getConfig() != null) {
        genOptions.config(options.getConfig());
      } else if (dotPrompt.getConfig() != null) {
        genOptions.config(dotPrompt.getConfig());
      }

      return generateFunction.generate(genOptions.build());
    }

    // Fall back to direct model call (no tool/interrupt support)
    Model model = getModel(modelName);
    ActionContext ctx = new ActionContext(registry);

    // Merge generation config from options if provided
    if (options != null && options.getConfig() != null) {
      // Override with options config
      request = mergeConfig(request, options);
    }

    return model.run(ctx, request);
  }

  /**
   * Generates a response with streaming.
   *
   * @param input
   *            the prompt input
   * @param streamCallback
   *            callback for streaming chunks
   * @return the final model response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse stream(I input, Consumer<ModelResponseChunk> streamCallback) throws GenkitException {
    return stream(input, null, streamCallback);
  }

  /**
   * Generates a response with streaming and custom options.
   *
   * @param input
   *            the prompt input
   * @param options
   *            optional generation options
   * @param streamCallback
   *            callback for streaming chunks
   * @return the final model response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse stream(I input, GenerateOptions options, Consumer<ModelResponseChunk> streamCallback)
      throws GenkitException {
    ModelRequest request = dotPrompt.toModelRequest(input);
    String modelName = resolveModel(options);

    Model model = getModel(modelName);
    ActionContext ctx = new ActionContext(registry);

    if (options != null && options.getConfig() != null) {
      request = mergeConfig(request, options);
    }

    return model.run(ctx, request, streamCallback);
  }

  /**
   * Renders the prompt template without generating.
   *
   * @param input
   *            the prompt input
   * @return the rendered prompt text
   * @throws GenkitException
   *             if rendering fails
   */
  public String render(I input) throws GenkitException {
    return dotPrompt.render(input);
  }

  /**
   * Gets the ModelRequest that would be sent to the model.
   *
   * @param input
   *            the prompt input
   * @return the model request
   * @throws GenkitException
   *             if conversion fails
   */
  public ModelRequest toModelRequest(I input) throws GenkitException {
    return dotPrompt.toModelRequest(input);
  }

  /**
   * Converts this executable prompt to a Prompt action.
   *
   * @return the Prompt action
   */
  public Prompt<I> toPrompt() {
    return dotPrompt.toPrompt(inputClass);
  }

  /**
   * Registers this prompt as an action in the registry.
   */
  public void register() {
    dotPrompt.register(registry, inputClass);
  }

  /**
   * Gets the underlying DotPrompt.
   *
   * @return the DotPrompt
   */
  public DotPrompt<I> getDotPrompt() {
    return dotPrompt;
  }

  /**
   * Gets the prompt name.
   *
   * @return the name
   */
  public String getName() {
    return dotPrompt.getName();
  }

  /**
   * Gets the default model name.
   *
   * @return the model name
   */
  public String getModel() {
    return dotPrompt.getModel();
  }

  /**
   * Gets the template.
   *
   * @return the template
   */
  public String getTemplate() {
    return dotPrompt.getTemplate();
  }

  /**
   * Gets the generation config.
   *
   * @return the config
   */
  public GenerationConfig getConfig() {
    return dotPrompt.getConfig();
  }

  // Private helper methods

  private String resolveModel(GenerateOptions options) {
    // Options model takes precedence
    if (options != null && options.getModel() != null && !options.getModel().isEmpty()) {
      return options.getModel();
    }
    // Fall back to prompt's default model
    String model = dotPrompt.getModel();
    if (model == null || model.isEmpty()) {
      throw new GenkitException("No model specified in prompt or options");
    }
    return model;
  }

  private Model getModel(String modelName) {
    // Try direct lookup first
    com.google.genkit.core.Action<?, ?, ?> action = registry.lookupAction(com.google.genkit.core.ActionType.MODEL,
        modelName);

    if (action == null) {
      // Try with model/ prefix
      String key = com.google.genkit.core.ActionType.MODEL.keyFromName(modelName);
      action = registry.lookupAction(key);
    }

    if (action == null) {
      throw new GenkitException("Model not found: " + modelName);
    }

    if (!(action instanceof Model)) {
      throw new GenkitException("Action is not a model: " + modelName);
    }

    return (Model) action;
  }

  private ModelRequest mergeConfig(ModelRequest request, GenerateOptions options) {
    GenerationConfig optionsConfig = options.getConfig();
    if (optionsConfig == null) {
      return request;
    }

    // Build new config map merging prompt config with options config
    Map<String, Object> configMap = new java.util.HashMap<>();
    if (request.getConfig() != null) {
      configMap.putAll(request.getConfig());
    }

    // Override with options config
    if (optionsConfig.getTemperature() != null) {
      configMap.put("temperature", optionsConfig.getTemperature());
    }
    if (optionsConfig.getMaxOutputTokens() != null) {
      configMap.put("maxOutputTokens", optionsConfig.getMaxOutputTokens());
    }
    if (optionsConfig.getTopP() != null) {
      configMap.put("topP", optionsConfig.getTopP());
    }
    if (optionsConfig.getTopK() != null) {
      configMap.put("topK", optionsConfig.getTopK());
    }

    return ModelRequest.builder().messages(request.getMessages()).config(configMap).tools(request.getTools())
        .output(request.getOutput()).build();
  }
}
