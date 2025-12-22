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

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

import com.github.jknack.handlebars.Context;
import com.github.jknack.handlebars.Handlebars;
import com.github.jknack.handlebars.Template;
import com.github.jknack.handlebars.io.StringTemplateSource;
import com.github.jknack.handlebars.io.TemplateLoader;
import com.github.jknack.handlebars.io.TemplateSource;
import com.google.genkit.ai.GenerateOptions;
import com.google.genkit.ai.GenerationConfig;
import com.google.genkit.ai.Model;
import com.google.genkit.ai.ModelRequest;
import com.google.genkit.ai.ModelResponse;
import com.google.genkit.ai.ModelResponseChunk;
import com.google.genkit.ai.Prompt;
import com.google.genkit.core.Action;
import com.google.genkit.core.ActionContext;
import com.google.genkit.core.ActionType;
import com.google.genkit.core.GenkitException;
import com.google.genkit.core.Registry;

/**
 * DotPrompt provides support for .prompt files using Handlebars templating.
 * 
 * .prompt files are structured text files with YAML frontmatter containing
 * configuration options and a Handlebars template body.
 * 
 * Partials are supported by files starting with underscore (e.g.,
 * _style.prompt). Partials are automatically loaded when referenced in
 * templates.
 */
public class DotPrompt<I> {

  /** Registry of partials (for debugging/introspection). */
  private static final Map<String, String> registeredPartials = new ConcurrentHashMap<>();

  /** Custom TemplateLoader that resolves partials from our registry. */
  private static final TemplateLoader partialLoader = new TemplateLoader() {
    @Override
    public TemplateSource sourceAt(String location) throws IOException {
      String partial = registeredPartials.get(location);
      if (partial != null) {
        return new StringTemplateSource(location, partial);
      }
      throw new IOException("Partial not found: " + location);
    }

    @Override
    public String resolve(String location) {
      return location;
    }

    @Override
    public String getPrefix() {
      return "";
    }

    @Override
    public String getSuffix() {
      return "";
    }

    @Override
    public void setPrefix(String prefix) {
    }

    @Override
    public void setSuffix(String suffix) {
    }

    @Override
    public void setCharset(Charset charset) {
    }

    @Override
    public Charset getCharset() {
      return StandardCharsets.UTF_8;
    }
  };

  /** Shared Handlebars instance with registered partials. */
  private static final Handlebars sharedHandlebars = new Handlebars(partialLoader);

  private final String name;
  private final String model;
  private final String template;
  private final Map<String, Object> inputSchema;
  private final GenerationConfig config;
  private final Handlebars handlebars;

  /**
   * Creates a new DotPrompt.
   *
   * @param name
   *            the prompt name
   * @param model
   *            the default model name
   * @param template
   *            the Handlebars template
   * @param inputSchema
   *            the input JSON schema
   * @param config
   *            the default generation config
   */
  public DotPrompt(String name, String model, String template, Map<String, Object> inputSchema,
      GenerationConfig config) {
    this.name = name;
    this.model = model;
    this.template = template;
    this.inputSchema = inputSchema;
    this.config = config;
    this.handlebars = sharedHandlebars; // Use shared instance with registered partials
  }

  /**
   * Registers a partial template that can be included in other prompts. Partials
   * are referenced using {{>partialName}} syntax in templates.
   *
   * @param name
   *            the partial name (without underscore prefix or .prompt extension)
   * @param source
   *            the partial template source
   * @throws GenkitException
   *             if registration fails
   */
  public static void registerPartial(String name, String source) throws GenkitException {
    // Extract just the template body (skip frontmatter if present)
    String templateBody = source;
    if (source.startsWith("---")) {
      int endIndex = source.indexOf("---", 3);
      if (endIndex > 0) {
        templateBody = source.substring(endIndex + 3).trim();
      }
    }
    registeredPartials.put(name, templateBody);
  }

  /**
   * Loads and registers a partial from a resource file. The partial name is
   * derived from the filename (without underscore prefix and .prompt extension).
   *
   * @param resourcePath
   *            the resource path (e.g., "/prompts/_style.prompt")
   * @throws GenkitException
   *             if loading fails
   */
  public static void loadPartialFromResource(String resourcePath) throws GenkitException {
    try (InputStream is = DotPrompt.class.getResourceAsStream(resourcePath)) {
      if (is == null) {
        throw new GenkitException("Partial resource not found: " + resourcePath);
      }
      String content = new String(is.readAllBytes(), StandardCharsets.UTF_8);

      // Extract partial name from path
      String name = resourcePath;
      if (name.contains("/")) {
        name = name.substring(name.lastIndexOf('/') + 1);
      }
      if (name.startsWith("_")) {
        name = name.substring(1);
      }
      if (name.endsWith(".prompt")) {
        name = name.substring(0, name.length() - 7);
      }

      registerPartial(name, content);
    } catch (IOException e) {
      throw new GenkitException("Failed to load partial resource: " + resourcePath, e);
    }
  }

  /**
   * Returns the names of all registered partials.
   *
   * @return set of partial names
   */
  public static java.util.Set<String> getRegisteredPartialNames() {
    return registeredPartials.keySet();
  }

  /**
   * Loads a DotPrompt from a resource file. Automatically loads any partials
   * referenced in the template from the same directory. Partials should be named
   * with underscore prefix (e.g., _style.prompt).
   *
   * @param <I>
   *            the input type
   * @param resourcePath
   *            the resource path
   * @return the loaded DotPrompt
   * @throws GenkitException
   *             if loading fails
   */
  public static <I> DotPrompt<I> loadFromResource(String resourcePath) throws GenkitException {
    try (InputStream is = DotPrompt.class.getResourceAsStream(resourcePath)) {
      if (is == null) {
        throw new GenkitException("Resource not found: " + resourcePath);
      }
      String content = new String(is.readAllBytes(), StandardCharsets.UTF_8);

      // Get the directory path for loading partials
      String directory = resourcePath.contains("/")
          ? resourcePath.substring(0, resourcePath.lastIndexOf('/'))
          : "";

      // Auto-load partials referenced in the template
      autoLoadPartials(content, directory);

      return parse(resourcePath, content);
    } catch (IOException e) {
      throw new GenkitException("Failed to load prompt resource: " + resourcePath, e);
    }
  }

  /**
   * Scans template content for partial references ({{>partialName}}) and loads
   * them. Partials are loaded from the same directory with underscore prefix.
   */
  private static void autoLoadPartials(String content, String directory) {
    // Find all partial references: {{>partialName}} or {{> partialName}}
    java.util.regex.Pattern pattern = java.util.regex.Pattern.compile("\\{\\{>\\s*([\\w-]+)");
    java.util.regex.Matcher matcher = pattern.matcher(content);

    while (matcher.find()) {
      String partialName = matcher.group(1);

      // Skip if already registered
      if (registeredPartials.containsKey(partialName)) {
        continue;
      }

      // Try to load the partial from resource
      String partialPath = directory + "/_" + partialName + ".prompt";
      try (InputStream partialIs = DotPrompt.class.getResourceAsStream(partialPath)) {
        if (partialIs != null) {
          String partialContent = new String(partialIs.readAllBytes(), StandardCharsets.UTF_8);
          registerPartial(partialName, partialContent);
        }
        // If partial not found, Handlebars will report the error when rendering
      } catch (IOException e) {
        // Ignore - partial loading is best-effort, Handlebars will report if missing
      }
    }
  }

  /**
   * Parses a DotPrompt from its string content.
   *
   * @param <I>
   *            the input type
   * @param name
   *            the prompt name
   * @param content
   *            the prompt file content
   * @return the parsed DotPrompt
   * @throws GenkitException
   *             if parsing fails
   */
  public static <I> DotPrompt<I> parse(String name, String content) throws GenkitException {
    // Split frontmatter from template
    String template = content;
    String model = null;
    Map<String, Object> inputSchema = null;
    GenerationConfig config = null;

    if (content.startsWith("---")) {
      int endIndex = content.indexOf("---", 3);
      if (endIndex > 0) {
        String frontmatter = content.substring(3, endIndex).trim();
        template = content.substring(endIndex + 3).trim();

        // Simple YAML parsing for common fields
        for (String line : frontmatter.split("\n")) {
          line = line.trim();
          if (line.startsWith("model:")) {
            model = line.substring(6).trim();
          }
        }
      }
    }

    // Clean up the name (remove extension)
    if (name.endsWith(".prompt")) {
      name = name.substring(0, name.length() - 7);
    }
    if (name.contains("/")) {
      name = name.substring(name.lastIndexOf('/') + 1);
    }

    return new DotPrompt<>(name, model, template, inputSchema, config);
  }

  /**
   * Renders the prompt with the given input.
   *
   * @param input
   *            the input data
   * @return the rendered prompt text
   * @throws GenkitException
   *             if rendering fails
   */
  public String render(I input) throws GenkitException {
    try {
      Template compiledTemplate = handlebars.compileInline(template);
      Context context = Context.newBuilder(input).build();
      return compiledTemplate.apply(context);
    } catch (IOException e) {
      throw new GenkitException("Failed to render prompt template", e);
    }
  }

  /**
   * Renders the prompt and creates a ModelRequest.
   *
   * @param input
   *            the input data
   * @return the model request
   * @throws GenkitException
   *             if rendering fails
   */
  public ModelRequest toModelRequest(I input) throws GenkitException {
    String rendered = render(input);

    ModelRequest.Builder builder = ModelRequest.builder().addUserMessage(rendered);

    if (config != null) {
      // Convert GenerationConfig to Map
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
      // Include custom config for model-specific options
      if (config.getCustom() != null) {
        configMap.putAll(config.getCustom());
      }
      builder.config(configMap);
    }

    return builder.build();
  }

  /**
   * Creates a Prompt action from this DotPrompt.
   *
   * @param inputClass
   *            the input class
   * @return the Prompt action
   */
  public Prompt<I> toPrompt(Class<I> inputClass) {
    return Prompt.<I>builder().name(name).model(model).template(template).inputSchema(inputSchema).config(config)
        .inputClass(inputClass).renderer((ctx, input) -> toModelRequest(input)).build();
  }

  /**
   * Registers this DotPrompt as an action.
   *
   * @param registry
   *            the registry
   * @param inputClass
   *            the input class
   */
  public void register(Registry registry, Class<I> inputClass) {
    Prompt<I> prompt = toPrompt(inputClass);
    prompt.register(registry);
  }

  /**
   * Generates a response using this prompt with the given registry.
   * 
   * <p>
   * This method allows generating directly from a DotPrompt without needing to go
   * through ExecutablePrompt. The model is looked up from the registry using the
   * model name specified in the prompt.
   *
   * @param registry
   *            the registry to look up the model
   * @param input
   *            the prompt input
   * @return the model response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse generate(Registry registry, I input) throws GenkitException {
    return generate(registry, input, null, null);
  }

  /**
   * Generates a response using this prompt with custom options.
   *
   * @param registry
   *            the registry to look up the model
   * @param input
   *            the prompt input
   * @param options
   *            optional generation options to override prompt defaults
   * @return the model response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse generate(Registry registry, I input, GenerateOptions options) throws GenkitException {
    return generate(registry, input, options, null);
  }

  /**
   * Generates a response using this prompt with streaming.
   *
   * @param registry
   *            the registry to look up the model
   * @param input
   *            the prompt input
   * @param options
   *            optional generation options
   * @param streamCallback
   *            callback for streaming chunks
   * @return the model response
   * @throws GenkitException
   *             if generation fails
   */
  public ModelResponse generate(Registry registry, I input, GenerateOptions options,
      Consumer<ModelResponseChunk> streamCallback) throws GenkitException {
    ModelRequest request = toModelRequest(input);
    String modelName = resolveModel(options);

    Model modelAction = getModel(registry, modelName);
    ActionContext ctx = new ActionContext(registry);

    if (options != null && options.getConfig() != null) {
      request = mergeConfig(request, options);
    }

    if (streamCallback != null) {
      return modelAction.run(ctx, request, streamCallback);
    } else {
      return modelAction.run(ctx, request);
    }
  }

  // Private helper methods for generation

  private String resolveModel(GenerateOptions options) {
    if (options != null && options.getModel() != null && !options.getModel().isEmpty()) {
      return options.getModel();
    }
    if (model == null || model.isEmpty()) {
      throw new GenkitException("No model specified in prompt or options");
    }
    return model;
  }

  private Model getModel(Registry registry, String modelName) {
    Action<?, ?, ?> action = registry.lookupAction(ActionType.MODEL, modelName);
    if (action == null) {
      String key = ActionType.MODEL.keyFromName(modelName);
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

    Map<String, Object> configMap = new HashMap<>();
    if (request.getConfig() != null) {
      configMap.putAll(request.getConfig());
    }

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

  // Getters

  public String getName() {
    return name;
  }

  public String getModel() {
    return model;
  }

  public String getTemplate() {
    return template;
  }

  public Map<String, Object> getInputSchema() {
    return inputSchema;
  }

  public GenerationConfig getConfig() {
    return config;
  }
}
