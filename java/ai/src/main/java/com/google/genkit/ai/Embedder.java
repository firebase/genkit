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
 * Embedder is an action that generates embeddings from documents.
 *
 * Embedders convert text or other content into numerical vectors that can be
 * used for similarity search and retrieval.
 */
public class Embedder implements Action<EmbedRequest, EmbedResponse, Void> {

  private final String name;
  private final EmbedderInfo info;
  private final BiFunction<ActionContext, EmbedRequest, EmbedResponse> handler;
  private final Map<String, Object> metadata;

  /**
   * Creates a new Embedder.
   *
   * @param name
   *            the embedder name
   * @param info
   *            the embedder info
   * @param handler
   *            the embedding function
   */
  public Embedder(String name, EmbedderInfo info, BiFunction<ActionContext, EmbedRequest, EmbedResponse> handler) {
    this.name = name;
    this.info = info;
    this.handler = handler;
    this.metadata = new HashMap<>();
    if (info != null) {
      this.metadata.put("info", info);
    }
  }

  /**
   * Creates a builder for Embedder.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  @Override
  public String getName() {
    return name;
  }

  @Override
  public ActionType getType() {
    return ActionType.EMBEDDER;
  }

  @Override
  public ActionDesc getDesc() {
    return ActionDesc.builder().type(ActionType.EMBEDDER).name(name).inputSchema(getInputSchema())
        .outputSchema(getOutputSchema()).metadata(metadata).build();
  }

  @Override
  public EmbedResponse run(ActionContext ctx, EmbedRequest input) throws GenkitException {
    try {
      return handler.apply(ctx, input);
    } catch (Exception e) {
      throw new GenkitException("Embedder execution failed: " + e.getMessage(), e);
    }
  }

  @Override
  public EmbedResponse run(ActionContext ctx, EmbedRequest input, Consumer<Void> streamCallback)
      throws GenkitException {
    return run(ctx, input);
  }

  @Override
  public JsonNode runJson(ActionContext ctx, JsonNode input, Consumer<JsonNode> streamCallback)
      throws GenkitException {
    EmbedRequest request = JsonUtils.fromJsonNode(input, EmbedRequest.class);
    EmbedResponse response = run(ctx, request);
    return JsonUtils.toJsonNode(response);
  }

  @Override
  public ActionRunResult<JsonNode> runJsonWithTelemetry(ActionContext ctx, JsonNode input,
      Consumer<JsonNode> streamCallback) throws GenkitException {
    JsonNode result = runJson(ctx, input, streamCallback);
    return new ActionRunResult<>(result, null, null);
  }

  @Override
  public Map<String, Object> getInputSchema() {
    // Define the input schema for embedders
    // This follows the EmbedRequestSchema from genkit-tools
    Map<String, Object> schema = new HashMap<>();
    schema.put("type", "object");

    Map<String, Object> properties = new HashMap<>();

    // input: array of documents (matching Document structure with content array)
    Map<String, Object> inputProp = new HashMap<>();
    inputProp.put("type", "array");
    inputProp.put("description", "Array of documents to embed");

    // Document schema
    Map<String, Object> docItemSchema = new HashMap<>();
    docItemSchema.put("type", "object");
    Map<String, Object> docProps = new HashMap<>();

    // content array in each document (array of Parts)
    Map<String, Object> contentProp = new HashMap<>();
    contentProp.put("type", "array");
    Map<String, Object> partSchema = new HashMap<>();
    partSchema.put("type", "object");
    Map<String, Object> partProps = new HashMap<>();
    Map<String, Object> textProp = new HashMap<>();
    textProp.put("type", "string");
    textProp.put("description", "Text content to embed");
    partProps.put("text", textProp);
    partSchema.put("properties", partProps);
    contentProp.put("items", partSchema);
    docProps.put("content", contentProp);

    // metadata in document
    Map<String, Object> metaProp = new HashMap<>();
    metaProp.put("type", "object");
    metaProp.put("additionalProperties", true);
    docProps.put("metadata", metaProp);

    docItemSchema.put("properties", docProps);
    docItemSchema.put("required", java.util.List.of("content"));
    inputProp.put("items", docItemSchema);
    properties.put("input", inputProp);

    // options: optional configuration
    Map<String, Object> optionsProp = new HashMap<>();
    optionsProp.put("type", "object");
    optionsProp.put("description", "Optional embedding configuration");
    properties.put("options", optionsProp);

    schema.put("properties", properties);
    schema.put("required", java.util.List.of("input"));

    return schema;
  }

  @Override
  public Map<String, Object> getOutputSchema() {
    // Define the output schema for embedders
    Map<String, Object> schema = new HashMap<>();
    schema.put("type", "object");

    Map<String, Object> properties = new HashMap<>();

    // embeddings: array of embedding objects
    Map<String, Object> embeddingsProp = new HashMap<>();
    embeddingsProp.put("type", "array");
    Map<String, Object> embeddingSchema = new HashMap<>();
    embeddingSchema.put("type", "object");
    Map<String, Object> embeddingProps = new HashMap<>();
    Map<String, Object> embeddingArrayProp = new HashMap<>();
    embeddingArrayProp.put("type", "array");
    Map<String, Object> numberItem = new HashMap<>();
    numberItem.put("type", "number");
    embeddingArrayProp.put("items", numberItem);
    embeddingProps.put("values", embeddingArrayProp);
    embeddingSchema.put("properties", embeddingProps);
    embeddingsProp.put("items", embeddingSchema);
    properties.put("embeddings", embeddingsProp);

    schema.put("properties", properties);

    return schema;
  }

  @Override
  public Map<String, Object> getMetadata() {
    return metadata;
  }

  @Override
  public void register(Registry registry) {
    registry.registerAction(ActionType.EMBEDDER.keyFromName(name), this);
  }

  /**
   * Gets the embedder info.
   *
   * @return the embedder info
   */
  public EmbedderInfo getInfo() {
    return info;
  }

  /**
   * Builder for Embedder.
   */
  public static class Builder {
    private String name;
    private EmbedderInfo info;
    private BiFunction<ActionContext, EmbedRequest, EmbedResponse> handler;

    public Builder name(String name) {
      this.name = name;
      return this;
    }

    public Builder info(EmbedderInfo info) {
      this.info = info;
      return this;
    }

    public Builder handler(BiFunction<ActionContext, EmbedRequest, EmbedResponse> handler) {
      this.handler = handler;
      return this;
    }

    public Embedder build() {
      if (name == null) {
        throw new IllegalStateException("Embedder name is required");
      }
      if (handler == null) {
        throw new IllegalStateException("Embedder handler is required");
      }
      return new Embedder(name, info, handler);
    }
  }
}
