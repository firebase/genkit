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

package com.google.genkit.core;

import java.util.Map;
import java.util.function.Consumer;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * Action is the interface that all Genkit primitives (e.g., flows, models,
 * tools) have in common. An Action represents a named, observable operation
 * that can be executed and traced.
 *
 * <p>
 * Actions are the fundamental building blocks of Genkit applications. They
 * provide:
 * <ul>
 * <li>Named operations that can be discovered and invoked</li>
 * <li>Input/output schema validation</li>
 * <li>Automatic tracing and observability</li>
 * <li>Registry integration for reflection API support</li>
 * </ul>
 *
 * @param <I>
 *            The input type for the action
 * @param <O>
 *            The output type for the action
 * @param <S>
 *            The streaming chunk type (use Void for non-streaming actions)
 */
public interface Action<I, O, S> extends Registerable {

  /**
   * Returns the name of the action.
   *
   * @return the action name
   */
  String getName();

  /**
   * Returns the type of the action.
   *
   * @return the action type
   */
  ActionType getType();

  /**
   * Returns the descriptor of the action containing metadata, schemas, etc.
   *
   * @return the action descriptor
   */
  ActionDesc getDesc();

  /**
   * Runs the action with the given input.
   *
   * @param ctx
   *            the action context
   * @param input
   *            the input to the action
   * @return the output of the action
   * @throws GenkitException
   *             if the action fails
   */
  O run(ActionContext ctx, I input) throws GenkitException;

  /**
   * Runs the action with the given input and streaming callback.
   *
   * @param ctx
   *            the action context
   * @param input
   *            the input to the action
   * @param streamCallback
   *            callback for receiving streaming chunks, may be null
   * @return the output of the action
   * @throws GenkitException
   *             if the action fails
   */
  O run(ActionContext ctx, I input, Consumer<S> streamCallback) throws GenkitException;

  /**
   * Runs the action with JSON input and returns JSON output.
   *
   * @param ctx
   *            the action context
   * @param input
   *            the JSON input
   * @param streamCallback
   *            callback for receiving streaming JSON chunks, may be null
   * @return the JSON output
   * @throws GenkitException
   *             if the action fails
   */
  JsonNode runJson(ActionContext ctx, JsonNode input, Consumer<JsonNode> streamCallback) throws GenkitException;

  /**
   * Runs the action with JSON input and returns the result with telemetry
   * information.
   *
   * @param ctx
   *            the action context
   * @param input
   *            the JSON input
   * @param streamCallback
   *            callback for receiving streaming JSON chunks, may be null
   * @return the action result including telemetry data
   * @throws GenkitException
   *             if the action fails
   */
  ActionRunResult<JsonNode> runJsonWithTelemetry(ActionContext ctx, JsonNode input, Consumer<JsonNode> streamCallback)
      throws GenkitException;

  /**
   * Returns the JSON schema for the action's input type.
   *
   * @return the input schema as a map, or null if not defined
   */
  Map<String, Object> getInputSchema();

  /**
   * Returns the JSON schema for the action's output type.
   *
   * @return the output schema as a map, or null if not defined
   */
  Map<String, Object> getOutputSchema();

  /**
   * Returns additional metadata for the action.
   *
   * @return the metadata map
   */
  Map<String, Object> getMetadata();
}
