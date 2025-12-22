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
 * Indexer is an action that indexes documents into a vector store.
 *
 * Indexers are used for RAG (Retrieval Augmented Generation) workflows to store
 * documents that can later be retrieved.
 */
public class Indexer implements Action<IndexerRequest, IndexerResponse, Void> {

  private final String name;
  private final BiFunction<ActionContext, IndexerRequest, IndexerResponse> handler;
  private final Map<String, Object> metadata;

  /**
   * Creates a new Indexer.
   *
   * @param name
   *            the indexer name
   * @param handler
   *            the indexing function
   */
  public Indexer(String name, BiFunction<ActionContext, IndexerRequest, IndexerResponse> handler) {
    this.name = name;
    this.handler = handler;
    this.metadata = new HashMap<>();
    this.metadata.put("type", "indexer");
  }

  /**
   * Creates a builder for Indexer.
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
    return ActionType.INDEXER;
  }

  @Override
  public ActionDesc getDesc() {
    return ActionDesc.builder().type(ActionType.INDEXER).name(name).inputSchema(getInputSchema())
        .outputSchema(getOutputSchema()).metadata(getMetadata()).build();
  }

  @Override
  public IndexerResponse run(ActionContext ctx, IndexerRequest input) throws GenkitException {
    try {
      return handler.apply(ctx, input);
    } catch (Exception e) {
      throw new GenkitException("Indexer execution failed: " + e.getMessage(), e);
    }
  }

  @Override
  public IndexerResponse run(ActionContext ctx, IndexerRequest input, Consumer<Void> streamCallback)
      throws GenkitException {
    return run(ctx, input);
  }

  @Override
  public JsonNode runJson(ActionContext ctx, JsonNode input, Consumer<JsonNode> streamCallback)
      throws GenkitException {
    IndexerRequest request = JsonUtils.fromJsonNode(input, IndexerRequest.class);
    IndexerResponse response = run(ctx, request);
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
    // Define the input schema to match genkit-tools IndexerRequest schema
    Map<String, Object> schema = new HashMap<>();
    schema.put("type", "object");

    Map<String, Object> properties = new HashMap<>();

    // documents array property
    Map<String, Object> docsProp = new HashMap<>();
    docsProp.put("type", "array");
    Map<String, Object> docItemSchema = new HashMap<>();
    docItemSchema.put("type", "object");
    Map<String, Object> docProps = new HashMap<>();

    // content array in each document
    Map<String, Object> contentProp = new HashMap<>();
    contentProp.put("type", "array");
    Map<String, Object> partSchema = new HashMap<>();
    partSchema.put("type", "object");
    Map<String, Object> partProps = new HashMap<>();
    Map<String, Object> textProp = new HashMap<>();
    textProp.put("type", "string");
    partProps.put("text", textProp);
    partSchema.put("properties", partProps);
    contentProp.put("items", partSchema);
    docProps.put("content", contentProp);

    // metadata
    Map<String, Object> metaProp = new HashMap<>();
    metaProp.put("type", "object");
    metaProp.put("additionalProperties", true);
    docProps.put("metadata", metaProp);

    docItemSchema.put("properties", docProps);
    docItemSchema.put("required", java.util.List.of("content"));
    docsProp.put("items", docItemSchema);
    properties.put("documents", docsProp);

    // options property
    Map<String, Object> optionsProp = new HashMap<>();
    optionsProp.put("type", "object");
    properties.put("options", optionsProp);

    schema.put("properties", properties);
    schema.put("required", java.util.List.of("documents"));

    return schema;
  }

  @Override
  public Map<String, Object> getOutputSchema() {
    // Indexer returns void/empty response
    Map<String, Object> schema = new HashMap<>();
    schema.put("type", "object");
    return schema;
  }

  @Override
  public Map<String, Object> getMetadata() {
    return metadata;
  }

  @Override
  public void register(Registry registry) {
    registry.registerAction(ActionType.INDEXER.keyFromName(name), this);
  }

  /**
   * Builder for Indexer.
   */
  public static class Builder {
    private String name;
    private BiFunction<ActionContext, IndexerRequest, IndexerResponse> handler;

    public Builder name(String name) {
      this.name = name;
      return this;
    }

    public Builder handler(BiFunction<ActionContext, IndexerRequest, IndexerResponse> handler) {
      this.handler = handler;
      return this;
    }

    public Indexer build() {
      if (name == null) {
        throw new IllegalStateException("Indexer name is required");
      }
      if (handler == null) {
        throw new IllegalStateException("Indexer handler is required");
      }
      return new Indexer(name, handler);
    }
  }
}
