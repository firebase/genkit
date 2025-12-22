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
 * Model is the interface for AI model implementations.
 * 
 * Models are registered as actions and can be invoked to generate responses
 * from prompts.
 */
public interface Model extends Action<ModelRequest, ModelResponse, ModelResponseChunk> {

  /**
   * Gets information about the model's capabilities.
   *
   * @return the model info
   */
  ModelInfo getInfo();

  /**
   * Generates a response from the given request.
   *
   * @param ctx
   *            the action context
   * @param request
   *            the model request
   * @return the model response
   * @throws GenkitException
   *             if generation fails
   */
  @Override
  ModelResponse run(ActionContext ctx, ModelRequest request) throws GenkitException;

  /**
   * Generates a streaming response from the given request.
   *
   * @param ctx
   *            the action context
   * @param request
   *            the model request
   * @param streamCallback
   *            callback for streaming chunks
   * @return the final model response
   * @throws GenkitException
   *             if generation fails
   */
  @Override
  default ModelResponse run(ActionContext ctx, ModelRequest request, Consumer<ModelResponseChunk> streamCallback)
      throws GenkitException {
    // Default implementation doesn't support streaming
    return run(ctx, request);
  }

  /**
   * Returns whether this model supports streaming.
   *
   * @return true if streaming is supported
   */
  default boolean supportsStreaming() {
    return false;
  }

  @Override
  default ActionType getType() {
    return ActionType.MODEL;
  }

  @Override
  default ActionDesc getDesc() {
    return ActionDesc.builder().type(ActionType.MODEL).name(getName()).metadata(getMetadata()).build();
  }

  @Override
  default JsonNode runJson(ActionContext ctx, JsonNode input, Consumer<JsonNode> streamCallback)
      throws GenkitException {
    ModelRequest request = JsonUtils.fromJsonNode(input, ModelRequest.class);
    Consumer<ModelResponseChunk> typedCallback = null;
    if (streamCallback != null) {
      typedCallback = chunk -> streamCallback.accept(JsonUtils.toJsonNode(chunk));
    }
    ModelResponse response = run(ctx, request, typedCallback);
    return JsonUtils.toJsonNode(response);
  }

  @Override
  default ActionRunResult<JsonNode> runJsonWithTelemetry(ActionContext ctx, JsonNode input,
      Consumer<JsonNode> streamCallback) throws GenkitException {
    JsonNode result = runJson(ctx, input, streamCallback);
    return new ActionRunResult<>(result, null, null);
  }

  @Override
  default Map<String, Object> getInputSchema() {
    return null;
  }

  @Override
  default Map<String, Object> getOutputSchema() {
    return null;
  }

  @Override
  default Map<String, Object> getMetadata() {
    Map<String, Object> metadata = new HashMap<>();
    if (getInfo() != null) {
      metadata.put("model", getInfo());
    }
    return metadata;
  }

  @Override
  default void register(Registry registry) {
    registry.registerAction(ActionType.MODEL.keyFromName(getName()), this);
  }
}
