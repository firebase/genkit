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

package com.google.genkit.plugins.openai;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genkit.core.Action;
import com.google.genkit.core.Plugin;

/**
 * OpenAIPlugin provides OpenAI model integrations for Genkit.
 *
 * This plugin registers OpenAI models (GPT-4, GPT-3.5-turbo, etc.), embeddings
 * (text-embedding-ada-002, etc.), and image generation models (DALL-E,
 * gpt-image-1) as Genkit actions.
 */
public class OpenAIPlugin implements Plugin {

  private static final Logger logger = LoggerFactory.getLogger(OpenAIPlugin.class);

  /**
   * Supported GPT models.
   */
  public static final List<String> SUPPORTED_MODELS = Arrays.asList("gpt-5.2", "gpt-5.1", "gpt-5", "gpt-4o",
      "gpt-4o-mini", "gpt-4-turbo", "gpt-4-turbo-preview", "gpt-4", "gpt-4-32k", "gpt-3.5-turbo",
      "gpt-3.5-turbo-16k", "o1-preview", "o1-mini");

  /**
   * Supported embedding models.
   */
  public static final List<String> SUPPORTED_EMBEDDING_MODELS = Arrays.asList("text-embedding-3-small",
      "text-embedding-3-large", "text-embedding-ada-002");

  /**
   * Supported image generation models.
   */
  public static final List<String> SUPPORTED_IMAGE_MODELS = Arrays.asList("dall-e-3", "dall-e-2", "gpt-image-1");

  private final OpenAIPluginOptions options;

  /**
   * Creates an OpenAIPlugin with default options.
   */
  public OpenAIPlugin() {
    this(OpenAIPluginOptions.builder().build());
  }

  /**
   * Creates an OpenAIPlugin with the specified options.
   *
   * @param options
   *            the plugin options
   */
  public OpenAIPlugin(OpenAIPluginOptions options) {
    this.options = options;
  }

  /**
   * Creates an OpenAIPlugin with the specified API key.
   *
   * @param apiKey
   *            the OpenAI API key
   * @return a new OpenAIPlugin
   */
  public static OpenAIPlugin create(String apiKey) {
    return new OpenAIPlugin(OpenAIPluginOptions.builder().apiKey(apiKey).build());
  }

  /**
   * Creates an OpenAIPlugin using the OPENAI_API_KEY environment variable.
   *
   * @return a new OpenAIPlugin
   */
  public static OpenAIPlugin create() {
    return new OpenAIPlugin();
  }

  @Override
  public String getName() {
    return "openai";
  }

  @Override
  public List<Action<?, ?, ?>> init() {
    List<Action<?, ?, ?>> actions = new ArrayList<>();

    // Register chat models
    for (String modelName : SUPPORTED_MODELS) {
      OpenAIModel model = new OpenAIModel(modelName, options);
      actions.add(model);
      logger.debug("Created OpenAI model: {}", modelName);
    }

    // Register embedding models
    for (String modelName : SUPPORTED_EMBEDDING_MODELS) {
      OpenAIEmbedder embedder = new OpenAIEmbedder(modelName, options);
      actions.add(embedder);
      logger.debug("Created OpenAI embedder: {}", modelName);
    }

    // Register image generation models
    for (String modelName : SUPPORTED_IMAGE_MODELS) {
      OpenAIImageModel imageModel = new OpenAIImageModel(modelName, options);
      actions.add(imageModel);
      logger.debug("Created OpenAI image model: {}", modelName);
    }

    logger.info("OpenAI plugin initialized with {} models, {} embedders, and {} image models",
        SUPPORTED_MODELS.size(), SUPPORTED_EMBEDDING_MODELS.size(), SUPPORTED_IMAGE_MODELS.size());

    return actions;
  }

  /**
   * Gets the plugin options.
   *
   * @return the options
   */
  public OpenAIPluginOptions getOptions() {
    return options;
  }
}
