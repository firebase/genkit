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

import java.util.HashMap;
import java.util.Map;
import java.util.function.Consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.genkit.core.tracing.SpanContext;
import com.google.genkit.core.tracing.SpanMetadata;
import com.google.genkit.core.tracing.Tracer;

/**
 * ActionDef is the default implementation of an Action. It provides a named,
 * observable operation that can be executed and traced.
 *
 * @param <I>
 *            The input type for the action
 * @param <O>
 *            The output type for the action
 * @param <S>
 *            The streaming chunk type (use Void for non-streaming actions)
 */
public class ActionDef<I, O, S> implements Action<I, O, S> {

  private static final Logger logger = LoggerFactory.getLogger(ActionDef.class);
  private static final ObjectMapper objectMapper = JsonUtils.getObjectMapper();

  private final ActionDesc desc;
  private final StreamingFunction<I, O, S> fn;
  private final Class<I> inputClass;
  private final Class<O> outputClass;
  private Registry registry;

  /**
   * Function interface for streaming actions.
   *
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @param <S>
   *            stream chunk type
   */
  @FunctionalInterface
  public interface StreamingFunction<I, O, S> {
    O apply(ActionContext ctx, I input, Consumer<S> streamCallback) throws GenkitException;
  }

  /**
   * Function interface for non-streaming actions.
   *
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   */
  @FunctionalInterface
  public interface ActionFunction<I, O> {
    O apply(ActionContext ctx, I input) throws GenkitException;
  }

  /**
   * Creates a new ActionDef.
   *
   * @param name
   *            the action name
   * @param type
   *            the action type
   * @param metadata
   *            additional metadata
   * @param inputSchema
   *            the input JSON schema
   * @param inputClass
   *            the input class
   * @param outputClass
   *            the output class
   * @param fn
   *            the action function
   */
  public ActionDef(String name, ActionType type, Map<String, Object> metadata, Map<String, Object> inputSchema,
      Class<I> inputClass, Class<O> outputClass, StreamingFunction<I, O, S> fn) {
    if (name == null || name.isEmpty()) {
      throw new IllegalArgumentException("Action name is required");
    }
    if (type == null) {
      throw new IllegalArgumentException("Action type is required");
    }
    if (fn == null) {
      throw new IllegalArgumentException("Action function is required");
    }

    String description = null;
    if (metadata != null && metadata.get("description") instanceof String) {
      description = (String) metadata.get("description");
    }

    // Generate schemas if not provided
    Map<String, Object> actualInputSchema = inputSchema;
    if (actualInputSchema == null && inputClass != null && inputClass != Void.class) {
      actualInputSchema = SchemaUtils.inferSchema(inputClass);
    }

    Map<String, Object> outputSchema = null;
    if (outputClass != null && outputClass != Void.class) {
      outputSchema = SchemaUtils.inferSchema(outputClass);
    }

    this.desc = ActionDesc.builder().type(type).name(name).description(description).inputSchema(actualInputSchema)
        .outputSchema(outputSchema).metadata(metadata != null ? metadata : new HashMap<>()).build();

    this.fn = fn;
    this.inputClass = inputClass;
    this.outputClass = outputClass;
  }

  /**
   * Creates a non-streaming action.
   *
   * @param name
   *            the action name
   * @param type
   *            the action type
   * @param metadata
   *            additional metadata
   * @param inputSchema
   *            the input JSON schema
   * @param inputClass
   *            the input class
   * @param outputClass
   *            the output class
   * @param fn
   *            the action function
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a new ActionDef
   */
  public static <I, O> ActionDef<I, O, Void> create(String name, ActionType type, Map<String, Object> metadata,
      Map<String, Object> inputSchema, Class<I> inputClass, Class<O> outputClass, ActionFunction<I, O> fn) {
    return new ActionDef<>(name, type, metadata, inputSchema, inputClass, outputClass,
        (ctx, input, cb) -> fn.apply(ctx, input));
  }

  /**
   * Creates a streaming action.
   *
   * @param name
   *            the action name
   * @param type
   *            the action type
   * @param metadata
   *            additional metadata
   * @param inputSchema
   *            the input JSON schema
   * @param inputClass
   *            the input class
   * @param outputClass
   *            the output class
   * @param fn
   *            the streaming function
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @param <S>
   *            stream chunk type
   * @return a new ActionDef
   */
  public static <I, O, S> ActionDef<I, O, S> createStreaming(String name, ActionType type,
      Map<String, Object> metadata, Map<String, Object> inputSchema, Class<I> inputClass, Class<O> outputClass,
      StreamingFunction<I, O, S> fn) {
    return new ActionDef<>(name, type, metadata, inputSchema, inputClass, outputClass, fn);
  }

  @Override
  public String getName() {
    return desc.getName();
  }

  @Override
  public ActionType getType() {
    return desc.getType();
  }

  @Override
  public ActionDesc getDesc() {
    return desc;
  }

  @Override
  public O run(ActionContext ctx, I input) throws GenkitException {
    return run(ctx, input, null);
  }

  @Override
  public O run(ActionContext ctx, I input, Consumer<S> streamCallback) throws GenkitException {
    logger.debug("Action.run: name={}, input={}", getName(), input);

    // Determine the subtype based on action type for proper telemetry
    // categorization
    String subtype = getSubtypeForTelemetry(desc.getType());

    SpanMetadata spanMetadata = SpanMetadata.builder().name(desc.getName()).type(desc.getType().getValue())
        .subtype(subtype).build();

    String flowName = ctx.getFlowName();
    if (flowName != null) {
      spanMetadata.getAttributes().put("genkit:metadata:flow:name", flowName);
    }

    return Tracer.runInNewSpan(ctx, spanMetadata, input, (spanCtx, in) -> {
      try {
        O result = fn.apply(ctx.withSpanContext(spanCtx), in, streamCallback);
        logger.debug("Action.run complete: name={}, result={}", getName(), result);
        return result;
      } catch (Exception e) {
        logger.error("Action.run failed: name={}, error={}", getName(), e.getMessage(), e);
        if (e instanceof GenkitException) {
          throw (GenkitException) e;
        }
        throw new GenkitException("Action execution failed: " + e.getMessage(), e);
      }
    });
  }

  @Override
  @SuppressWarnings("unchecked")
  public JsonNode runJson(ActionContext ctx, JsonNode input, Consumer<JsonNode> streamCallback)
      throws GenkitException {
    try {
      I typedInput = null;
      if (inputClass != null && inputClass != Void.class && input != null) {
        typedInput = objectMapper.treeToValue(input, inputClass);
      }

      Consumer<S> typedCallback = null;
      if (streamCallback != null) {
        typedCallback = chunk -> {
          try {
            JsonNode jsonChunk = objectMapper.valueToTree(chunk);
            streamCallback.accept(jsonChunk);
          } catch (Exception e) {
            throw new RuntimeException("Failed to serialize stream chunk", e);
          }
        };
      }

      O result = run(ctx, typedInput, typedCallback);

      if (result == null) {
        return null;
      }
      return objectMapper.valueToTree(result);
    } catch (Exception e) {
      if (e instanceof GenkitException) {
        throw (GenkitException) e;
      }
      throw new GenkitException("JSON action execution failed: " + e.getMessage(), e);
    }
  }

  @Override
  public ActionRunResult<JsonNode> runJsonWithTelemetry(ActionContext ctx, JsonNode input,
      Consumer<JsonNode> streamCallback) throws GenkitException {
    SpanContext spanContext = ctx.getSpanContext();
    String traceId = spanContext != null ? spanContext.getTraceId() : null;
    String spanId = spanContext != null ? spanContext.getSpanId() : null;

    JsonNode result = runJson(ctx, input, streamCallback);

    // Get updated span info after execution
    SpanContext currentSpan = ctx.getSpanContext();
    if (currentSpan != null) {
      traceId = currentSpan.getTraceId();
      spanId = currentSpan.getSpanId();
    }

    return new ActionRunResult<>(result, traceId, spanId);
  }

  @Override
  public Map<String, Object> getInputSchema() {
    return desc.getInputSchema();
  }

  @Override
  public Map<String, Object> getOutputSchema() {
    return desc.getOutputSchema();
  }

  @Override
  public Map<String, Object> getMetadata() {
    return desc.getMetadata();
  }

  @Override
  public void register(Registry registry) {
    this.registry = registry;
    registry.registerAction(desc.getKey(), this);
  }

  /**
   * Returns the registry this action is registered with.
   *
   * @return the registry, or null if not registered
   */
  public Registry getRegistry() {
    return registry;
  }

  /**
   * Returns the subtype for telemetry based on the action type. This matches the
   * JS/Go SDK format for proper trace categorization.
   *
   * @param type
   *            the action type
   * @return the subtype string for telemetry
   */
  private static String getSubtypeForTelemetry(ActionType type) {
    if (type == null) {
      return null;
    }
    switch (type) {
      case MODEL :
        return "model";
      case TOOL :
        return "tool";
      case FLOW :
        return "flow";
      case EMBEDDER :
        return "embedder";
      case RETRIEVER :
        return "retriever";
      case INDEXER :
        return "indexer";
      case EVALUATOR :
        return "evaluator";
      case PROMPT :
        return "prompt";
      default :
        return type.getValue();
    }
  }
}
