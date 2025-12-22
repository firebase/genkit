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

package com.google.genkit.plugins.googlegenai;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genkit.core.Action;
import com.google.genkit.core.Plugin;

/**
 * Google GenAI plugin for Genkit using the official Google GenAI SDK.
 *
 * <p>
 * This plugin provides access to Google's Gemini models for:
 * <ul>
 * <li>Text generation (Gemini 2.0, 2.5, 3.0 series)</li>
 * <li>Multimodal content (images, video, audio)</li>
 * <li>Embeddings (text-embedding-004, gemini-embedding-001)</li>
 * <li>Function calling/tools</li>
 * </ul>
 *
 * <p>
 * Supports both:
 * <ul>
 * <li>Gemini Developer API (with API key)</li>
 * <li>Vertex AI API (with GCP credentials)</li>
 * </ul>
 *
 * <p>
 * Example usage:
 * 
 * <pre>{@code
 * // Using Gemini Developer API with API key
 * Genkit genkit = Genkit.builder().addPlugin(GoogleGenAIPlugin.create()) // Uses GOOGLE_API_KEY env var
 * 		.build();
 *
 * // Using Vertex AI
 * Genkit genkit = Genkit.builder().addPlugin(GoogleGenAIPlugin.create(
 * 		GoogleGenAIPluginOptions.builder().vertexAI(true).project("my-project").location("us-central1").build()))
 * 		.build();
 *
 * // Generate content
 * GenerateResponse response = genkit
 * 		.generate(GenerateOptions.builder().model("googleai/gemini-2.0-flash").prompt("Hello, world!").build());
 * }</pre>
 */
public class GoogleGenAIPlugin implements Plugin {

  private static final Logger logger = LoggerFactory.getLogger(GoogleGenAIPlugin.class);

  /**
   * Supported Gemini models for text/multimodal generation.
   */
  public static final List<String> SUPPORTED_MODELS = Arrays.asList(
      // Gemini 3.0 series
      "gemini-3-pro-preview",
      // Gemini 2.5 series
      "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite",
      // Gemini 2.0 series
      "gemini-2.0-flash", "gemini-2.0-flash-lite",
      // Gemini 1.5 series (still widely used)
      "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b",
      // Gemma models
      "gemma-3-12b-it", "gemma-3-27b-it", "gemma-3-4b-it", "gemma-3-1b-it", "gemma-3n-e4b-it");

  /**
   * Supported embedding models.
   */
  public static final List<String> SUPPORTED_EMBEDDING_MODELS = Arrays.asList("text-embedding-004",
      "text-embedding-005", "gemini-embedding-001", "text-multilingual-embedding-002");

  /**
   * Supported image generation models (Imagen). Note: imagen-4.0-* models are
   * supported by the Gemini Developer API. imagen-3.0-* models require Vertex AI.
   */
  public static final List<String> SUPPORTED_IMAGE_MODELS = Arrays.asList("imagen-4.0-generate-001",
      "imagen-4.0-fast-generate-001");

  /**
   * Supported TTS models.
   */
  public static final List<String> SUPPORTED_TTS_MODELS = Arrays.asList("gemini-2.5-flash-preview-tts",
      "gemini-2.5-pro-preview-tts");

  /**
   * Supported video generation models (Veo).
   */
  public static final List<String> SUPPORTED_VEO_MODELS = Arrays.asList("veo-2.0-generate-001",
      "veo-3.0-generate-001", "veo-3.0-fast-generate-001", "veo-3.1-generate-preview",
      "veo-3.1-fast-generate-preview");

  private final GoogleGenAIPluginOptions options;

  /**
   * Creates a GoogleGenAIPlugin with default options. Reads API key from
   * GOOGLE_API_KEY or GEMINI_API_KEY environment variable.
   */
  public GoogleGenAIPlugin() {
    this(GoogleGenAIPluginOptions.builder().build());
  }

  /**
   * Creates a GoogleGenAIPlugin with the specified options.
   *
   * @param options
   *            the plugin options
   */
  public GoogleGenAIPlugin(GoogleGenAIPluginOptions options) {
    this.options = options;
  }

  /**
   * Creates a GoogleGenAIPlugin with the specified API key.
   *
   * @param apiKey
   *            the Google API key
   * @return a new GoogleGenAIPlugin
   */
  public static GoogleGenAIPlugin create(String apiKey) {
    return new GoogleGenAIPlugin(GoogleGenAIPluginOptions.builder().apiKey(apiKey).build());
  }

  /**
   * Creates a GoogleGenAIPlugin using environment variables for configuration.
   *
   * @return a new GoogleGenAIPlugin
   */
  public static GoogleGenAIPlugin create() {
    return new GoogleGenAIPlugin();
  }

  /**
   * Creates a GoogleGenAIPlugin with the specified options.
   *
   * @param options
   *            the plugin options
   * @return a new GoogleGenAIPlugin
   */
  public static GoogleGenAIPlugin create(GoogleGenAIPluginOptions options) {
    return new GoogleGenAIPlugin(options);
  }

  /**
   * Creates a GoogleGenAIPlugin configured for Vertex AI.
   *
   * @param project
   *            the GCP project ID
   * @param location
   *            the GCP location
   * @return a new GoogleGenAIPlugin configured for Vertex AI
   */
  public static GoogleGenAIPlugin vertexAI(String project, String location) {
    return new GoogleGenAIPlugin(
        GoogleGenAIPluginOptions.builder().vertexAI(true).project(project).location(location).build());
  }

  @Override
  public String getName() {
    return "googleai";
  }

  @Override
  public List<Action<?, ?, ?>> init() {
    List<Action<?, ?, ?>> actions = new ArrayList<>();

    // Register chat/generation models
    for (String modelName : SUPPORTED_MODELS) {
      GeminiModel model = new GeminiModel(modelName, options);
      actions.add(model);
      logger.debug("Created Gemini model: {}", modelName);
    }

    // Register embedding models
    for (String modelName : SUPPORTED_EMBEDDING_MODELS) {
      GeminiEmbedder embedder = new GeminiEmbedder(modelName, options);
      actions.add(embedder);
      logger.debug("Created Gemini embedder: {}", modelName);
    }

    // Register image generation (Imagen) models
    for (String modelName : SUPPORTED_IMAGE_MODELS) {
      ImagenModel model = new ImagenModel(modelName, options);
      actions.add(model);
      logger.debug("Created Imagen model: {}", modelName);
    }

    // Register TTS models
    for (String modelName : SUPPORTED_TTS_MODELS) {
      TtsModel model = new TtsModel(modelName, options);
      actions.add(model);
      logger.debug("Created TTS model: {}", modelName);
    }

    // Register video generation (Veo) models
    for (String modelName : SUPPORTED_VEO_MODELS) {
      VeoModel model = new VeoModel(modelName, options);
      actions.add(model);
      logger.debug("Created Veo model: {}", modelName);
    }

    String backend = options.isVertexAI() ? "Vertex AI" : "Gemini Developer API";
    logger.info(
        "Google GenAI plugin initialized with {} models, {} embedders, {} image models, {} TTS models, and {} video models using {}",
        SUPPORTED_MODELS.size(), SUPPORTED_EMBEDDING_MODELS.size(), SUPPORTED_IMAGE_MODELS.size(),
        SUPPORTED_TTS_MODELS.size(), SUPPORTED_VEO_MODELS.size(), backend);

    return actions;
  }

  /**
   * Gets the plugin options.
   *
   * @return the options
   */
  public GoogleGenAIPluginOptions getOptions() {
    return options;
  }
}
