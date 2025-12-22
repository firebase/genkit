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

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.google.genkit.ai.*;
import com.google.genkit.core.ActionContext;
import com.google.genkit.core.GenkitException;

import okhttp3.*;

/**
 * OpenAI embedder implementation for Genkit.
 */
public class OpenAIEmbedder extends Embedder {

  private static final Logger logger = LoggerFactory.getLogger(OpenAIEmbedder.class);
  private static final MediaType JSON_MEDIA_TYPE = MediaType.parse("application/json");

  private final String modelName;
  private final OpenAIPluginOptions options;
  private final OkHttpClient client;
  private final ObjectMapper objectMapper;

  /**
   * Creates a new OpenAIEmbedder.
   *
   * @param modelName
   *            the model name
   * @param options
   *            the plugin options
   */
  public OpenAIEmbedder(String modelName, OpenAIPluginOptions options) {
    super("openai/" + modelName, createEmbedderInfo(modelName), (ctx, req) -> {
      // This will be overridden by the actual implementation
      throw new GenkitException("Handler not initialized");
    });
    this.modelName = modelName;
    this.options = options;
    this.objectMapper = new ObjectMapper();
    this.client = new OkHttpClient.Builder().connectTimeout(options.getTimeout(), TimeUnit.SECONDS)
        .readTimeout(options.getTimeout(), TimeUnit.SECONDS)
        .writeTimeout(options.getTimeout(), TimeUnit.SECONDS).build();
  }

  private static EmbedderInfo createEmbedderInfo(String modelName) {
    EmbedderInfo info = new EmbedderInfo();
    info.setLabel("OpenAI " + modelName);

    // Set dimensions based on model
    switch (modelName) {
      case "text-embedding-3-small" :
        info.setDimensions(1536);
        break;
      case "text-embedding-3-large" :
        info.setDimensions(3072);
        break;
      case "text-embedding-ada-002" :
        info.setDimensions(1536);
        break;
    }

    return info;
  }

  @Override
  public EmbedResponse run(ActionContext context, EmbedRequest request) {
    if (request == null) {
      throw new GenkitException("Embed request is required. Please provide an input with documents to embed.");
    }
    if (request.getDocuments() == null || request.getDocuments().isEmpty()) {
      throw new GenkitException("Embed request must contain at least one document to embed.");
    }
    try {
      return callOpenAI(request);
    } catch (IOException e) {
      throw new GenkitException("OpenAI Embedding API call failed", e);
    }
  }

  private EmbedResponse callOpenAI(EmbedRequest request) throws IOException {
    ObjectNode requestBody = objectMapper.createObjectNode();
    requestBody.put("model", modelName);

    // Convert documents to text array
    ArrayNode input = requestBody.putArray("input");
    for (Document doc : request.getDocuments()) {
      String text = doc.text();
      logger.debug("Document text: '{}' (length: {})",
          text != null ? text.substring(0, Math.min(50, text.length())) : "null",
          text != null ? text.length() : 0);
      if (text == null || text.isEmpty()) {
        logger.warn("Document has empty text, skipping");
        continue;
      }
      input.add(text);
    }

    // Validate that we have at least one input
    if (input.isEmpty()) {
      throw new GenkitException("No valid documents to embed - all documents had empty text");
    }

    // Log the request for debugging
    String requestJson = requestBody.toString();
    logger.info("OpenAI Embedding request body: {}", requestJson);

    Request httpRequest = new Request.Builder().url(options.getBaseUrl() + "/embeddings")
        .header("Authorization", "Bearer " + options.getApiKey()).header("Content-Type", "application/json")
        .post(RequestBody.create(requestBody.toString(), JSON_MEDIA_TYPE)).build();

    if (options.getOrganization() != null) {
      httpRequest = httpRequest.newBuilder().header("OpenAI-Organization", options.getOrganization()).build();
    }

    try (Response response = client.newCall(httpRequest).execute()) {
      if (!response.isSuccessful()) {
        String errorBody = response.body() != null ? response.body().string() : "No error body";
        throw new GenkitException("OpenAI Embedding API error: " + response.code() + " - " + errorBody);
      }

      String responseBody = response.body().string();
      return parseResponse(responseBody);
    }
  }

  private EmbedResponse parseResponse(String responseBody) throws IOException {
    JsonNode root = objectMapper.readTree(responseBody);

    List<EmbedResponse.Embedding> embeddings = new ArrayList<>();

    JsonNode dataNode = root.get("data");
    if (dataNode != null && dataNode.isArray()) {
      for (JsonNode item : dataNode) {
        JsonNode embeddingNode = item.get("embedding");
        if (embeddingNode != null && embeddingNode.isArray()) {
          float[] values = new float[embeddingNode.size()];
          for (int i = 0; i < embeddingNode.size(); i++) {
            values[i] = (float) embeddingNode.get(i).asDouble();
          }
          embeddings.add(new EmbedResponse.Embedding(values));
        }
      }
    }

    return new EmbedResponse(embeddings);
  }
}
