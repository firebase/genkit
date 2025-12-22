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
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genai.Client;
import com.google.genai.types.ContentEmbedding;
import com.google.genai.types.EmbedContentConfig;
import com.google.genai.types.EmbedContentResponse;
import com.google.genai.types.HttpOptions;
import com.google.genkit.ai.EmbedRequest;
import com.google.genkit.ai.EmbedResponse;
import com.google.genkit.ai.Embedder;
import com.google.genkit.ai.EmbedderInfo;
import com.google.genkit.core.ActionContext;
import com.google.genkit.core.GenkitException;

/**
 * Gemini embedder implementation using the official Google GenAI SDK.
 */
public class GeminiEmbedder extends Embedder {

  private static final Logger logger = LoggerFactory.getLogger(GeminiEmbedder.class);

  private final String modelName;
  private final GoogleGenAIPluginOptions options;
  private final Client client;

  /**
   * Creates a new GeminiEmbedder.
   *
   * @param modelName
   *            the embedding model name (e.g., "text-embedding-004",
   *            "gemini-embedding-001")
   * @param options
   *            the plugin options
   */
  public GeminiEmbedder(String modelName, GoogleGenAIPluginOptions options) {
    super("googleai/" + modelName, createEmbedderInfo(modelName), (ctx, req) -> {
      throw new GenkitException("Handler not initialized");
    });
    this.modelName = modelName;
    this.options = options;
    this.client = createClient();
  }

  private Client createClient() {
    Client.Builder builder = Client.builder();

    if (options.isVertexAI()) {
      builder.vertexAI(true);
      if (options.getProject() != null) {
        builder.project(options.getProject());
      }
      if (options.getLocation() != null) {
        builder.location(options.getLocation());
      }
      if (options.getApiKey() != null) {
        builder.apiKey(options.getApiKey());
      }
    } else {
      builder.apiKey(options.getApiKey());
    }

    HttpOptions httpOptions = options.toHttpOptions();
    if (httpOptions != null) {
      builder.httpOptions(httpOptions);
    }

    return builder.build();
  }

  private static EmbedderInfo createEmbedderInfo(String modelName) {
    EmbedderInfo info = new EmbedderInfo();
    info.setLabel("Google AI " + modelName);

    // Default dimensions for Gemini embedding models
    switch (modelName) {
      case "text-embedding-004" :
      case "text-embedding-005" :
        info.setDimensions(768);
        break;
      case "gemini-embedding-001" :
        info.setDimensions(768);
        break;
      case "text-multilingual-embedding-002" :
        info.setDimensions(768);
        break;
      default :
        info.setDimensions(768); // Default
    }

    return info;
  }

  @Override
  public EmbedResponse run(ActionContext context, EmbedRequest request) {
    if (request == null) {
      throw new GenkitException("Embed request is required.");
    }
    if (request.getDocuments() == null || request.getDocuments().isEmpty()) {
      throw new GenkitException("Embed request must contain at least one document.");
    }

    try {
      return callGeminiEmbed(request);
    } catch (Exception e) {
      throw new GenkitException("Gemini Embedding API call failed: " + e.getMessage(), e);
    }
  }

  private EmbedResponse callGeminiEmbed(EmbedRequest request) {
    List<EmbedResponse.Embedding> embeddings = new ArrayList<>();

    for (com.google.genkit.ai.Document doc : request.getDocuments()) {
      String text = doc.text();
      if (text == null || text.isEmpty()) {
        logger.warn("Document has empty text, skipping");
        continue;
      }

      // Build embed config
      EmbedContentConfig.Builder configBuilder = EmbedContentConfig.builder();

      // Apply options from config
      if (request.getOptions() != null) {
        if (request.getOptions().containsKey("taskType")) {
          String taskType = (String) request.getOptions().get("taskType");
          configBuilder.taskType(taskType);
        }
        if (request.getOptions().containsKey("title")) {
          configBuilder.title((String) request.getOptions().get("title"));
        }
        if (request.getOptions().containsKey("outputDimensionality")) {
          configBuilder.outputDimensionality(
              ((Number) request.getOptions().get("outputDimensionality")).intValue());
        }
      }

      EmbedContentResponse response = client.models.embedContent(modelName, text, configBuilder.build());

      if (response.embeddings().isPresent() && !response.embeddings().get().isEmpty()) {
        ContentEmbedding embedding = response.embeddings().get().get(0);
        if (embedding.values().isPresent()) {
          List<Float> values = embedding.values().get();
          float[] floatValues = new float[values.size()];
          for (int i = 0; i < values.size(); i++) {
            floatValues[i] = values.get(i);
          }
          embeddings.add(new EmbedResponse.Embedding(floatValues));
        }
      }
    }

    return new EmbedResponse(embeddings);
  }
}
