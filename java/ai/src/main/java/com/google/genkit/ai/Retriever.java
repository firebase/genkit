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
 * Retriever is an action that retrieves documents based on a query.
 *
 * Retrievers are used for RAG (Retrieval Augmented Generation) workflows to
 * find relevant documents to include in model prompts.
 */
public class Retriever implements Action<RetrieverRequest, RetrieverResponse, Void> {

  private final String name;
  private final BiFunction<ActionContext, RetrieverRequest, RetrieverResponse> handler;
  private final Map<String, Object> metadata;

  /**
   * Creates a new Retriever.
   *
   * @param name
   *            the retriever name
   * @param handler
   *            the retrieval function
   */
  public Retriever(String name, BiFunction<ActionContext, RetrieverRequest, RetrieverResponse> handler) {
    this.name = name;
    this.handler = handler;
    this.metadata = new HashMap<>();
    this.metadata.put("type", "retriever");
  }

  /**
   * Creates a builder for Retriever.
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
    return ActionType.RETRIEVER;
  }

  @Override
  public ActionDesc getDesc() {
    return ActionDesc.builder().type(ActionType.RETRIEVER).name(name).inputSchema(getInputSchema())
        .outputSchema(getOutputSchema()).metadata(getMetadata()).build();
  }

  @Override
  public RetrieverResponse run(ActionContext ctx, RetrieverRequest input) throws GenkitException {
    try {
      return handler.apply(ctx, input);
    } catch (Exception e) {
      throw new GenkitException("Retriever execution failed: " + e.getMessage(), e);
    }
  }

  @Override
  public RetrieverResponse run(ActionContext ctx, RetrieverRequest input, Consumer<Void> streamCallback)
      throws GenkitException {
    return run(ctx, input);
  }

  @Override
  public JsonNode runJson(ActionContext ctx, JsonNode input, Consumer<JsonNode> streamCallback)
      throws GenkitException {
    RetrieverRequest request = JsonUtils.fromJsonNode(input, RetrieverRequest.class);
    RetrieverResponse response = run(ctx, request);
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
    // Define the input schema to match genkit-tools RetrieverRequest schema
    Map<String, Object> schema = new HashMap<>();
    schema.put("type", "object");

    Map<String, Object> properties = new HashMap<>();

    // query property - DocumentData
    Map<String, Object> queryProp = new HashMap<>();
    queryProp.put("type", "object");
    Map<String, Object> queryProps = new HashMap<>();

    // content array
    Map<String, Object> contentProp = new HashMap<>();
    contentProp.put("type", "array");
    Map<String, Object> contentItemSchema = new HashMap<>();
    contentItemSchema.put("type", "object");
    Map<String, Object> partProps = new HashMap<>();
    Map<String, Object> textProp = new HashMap<>();
    textProp.put("type", "string");
    partProps.put("text", textProp);
    contentItemSchema.put("properties", partProps);
    contentProp.put("items", contentItemSchema);
    queryProps.put("content", contentProp);

    // metadata
    Map<String, Object> metaProp = new HashMap<>();
    metaProp.put("type", "object");
    metaProp.put("additionalProperties", true);
    queryProps.put("metadata", metaProp);

    queryProp.put("properties", queryProps);
    queryProp.put("required", java.util.List.of("content"));
    properties.put("query", queryProp);

    // options property
    Map<String, Object> optionsProp = new HashMap<>();
    optionsProp.put("type", "object");
    Map<String, Object> optionsProps = new HashMap<>();
    Map<String, Object> kProp = new HashMap<>();
    kProp.put("type", "integer");
    kProp.put("description", "Number of documents to retrieve");
    optionsProps.put("k", kProp);
    optionsProp.put("properties", optionsProps);
    properties.put("options", optionsProp);

    schema.put("properties", properties);
    schema.put("required", java.util.List.of("query"));

    return schema;
  }

  @Override
  public Map<String, Object> getOutputSchema() {
    // Define the output schema to match genkit-tools RetrieverResponse schema
    Map<String, Object> schema = new HashMap<>();
    schema.put("type", "object");

    Map<String, Object> properties = new HashMap<>();

    // documents array
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
    docProps.put("metadata", metaProp);

    docItemSchema.put("properties", docProps);
    docsProp.put("items", docItemSchema);
    properties.put("documents", docsProp);

    schema.put("properties", properties);
    schema.put("required", java.util.List.of("documents"));

    return schema;
  }

  @Override
  public Map<String, Object> getMetadata() {
    return metadata;
  }

  @Override
  public void register(Registry registry) {
    registry.registerAction(ActionType.RETRIEVER.keyFromName(name), this);
  }

  /**
   * Builder for Retriever.
   */
  public static class Builder {
    private String name;
    private BiFunction<ActionContext, RetrieverRequest, RetrieverResponse> handler;

    public Builder name(String name) {
      this.name = name;
      return this;
    }

    public Builder handler(BiFunction<ActionContext, RetrieverRequest, RetrieverResponse> handler) {
      this.handler = handler;
      return this;
    }

    public Retriever build() {
      if (name == null) {
        throw new IllegalStateException("Retriever name is required");
      }
      if (handler == null) {
        throw new IllegalStateException("Retriever handler is required");
      }
      return new Retriever(name, handler);
    }
  }
}
