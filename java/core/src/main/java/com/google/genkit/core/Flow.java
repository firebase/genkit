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

import java.util.List;
import java.util.Map;
import java.util.function.BiFunction;
import java.util.function.Consumer;
import java.util.function.Function;

import com.fasterxml.jackson.databind.JsonNode;
import com.google.genkit.core.middleware.Middleware;
import com.google.genkit.core.middleware.MiddlewareChain;
import com.google.genkit.core.tracing.SpanMetadata;
import com.google.genkit.core.tracing.Tracer;

/**
 * A Flow is a user-defined Action. It represents a function from input I to
 * output O. The Stream parameter S is for flows that support streaming their
 * results incrementally.
 *
 * <p>
 * Flows are the primary way to organize AI application logic in Genkit. They
 * provide:
 * <ul>
 * <li>Observability through automatic tracing</li>
 * <li>Integration with Genkit developer tools</li>
 * <li>Easy deployment as API endpoints</li>
 * <li>Built-in streaming support</li>
 * </ul>
 *
 * @param <I>
 *            The input type for the flow
 * @param <O>
 *            The output type for the flow
 * @param <S>
 *            The streaming chunk type (use Void for non-streaming flows)
 */
public class Flow<I, O, S> implements Action<I, O, S> {

  private final ActionDef<I, O, S> actionDef;
  private final MiddlewareChain<I, O> middlewareChain;

  /**
   * Creates a new Flow wrapping an ActionDef.
   *
   * @param actionDef
   *            the underlying action definition
   */
  private Flow(ActionDef<I, O, S> actionDef) {
    this(actionDef, new MiddlewareChain<>());
  }

  /**
   * Creates a new Flow wrapping an ActionDef with middleware.
   *
   * @param actionDef
   *            the underlying action definition
   * @param middlewareChain
   *            the middleware chain to use
   */
  private Flow(ActionDef<I, O, S> actionDef, MiddlewareChain<I, O> middlewareChain) {
    this.actionDef = actionDef;
    this.middlewareChain = middlewareChain;
  }

  /**
   * Defines a new non-streaming flow and registers it.
   *
   * @param registry
   *            the registry to register with
   * @param name
   *            the flow name
   * @param inputClass
   *            the input type class
   * @param outputClass
   *            the output type class
   * @param fn
   *            the flow function
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return the created flow
   */
  public static <I, O> Flow<I, O, Void> define(Registry registry, String name, Class<I> inputClass,
      Class<O> outputClass, BiFunction<ActionContext, I, O> fn) {
    return define(registry, name, inputClass, outputClass, fn, null);
  }

  /**
   * Defines a new non-streaming flow with middleware and registers it.
   *
   * @param registry
   *            the registry to register with
   * @param name
   *            the flow name
   * @param inputClass
   *            the input type class
   * @param outputClass
   *            the output type class
   * @param fn
   *            the flow function
   * @param middleware
   *            the middleware to apply
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return the created flow
   */
  public static <I, O> Flow<I, O, Void> define(Registry registry, String name, Class<I> inputClass,
      Class<O> outputClass, BiFunction<ActionContext, I, O> fn, List<Middleware<I, O>> middleware) {
    MiddlewareChain<I, O> chain = new MiddlewareChain<>();
    if (middleware != null) {
      chain.useAll(middleware);
    }

    ActionDef<I, O, Void> actionDef = ActionDef.create(name, ActionType.FLOW, null, null, inputClass, outputClass,
        (ctx, input) -> {
          ActionContext flowCtx = ctx.withFlowName(name);
          if (chain.isEmpty()) {
            return fn.apply(flowCtx, input);
          }
          return chain.execute(input, flowCtx, (c, i) -> fn.apply(c, i));
        });

    Flow<I, O, Void> flow = new Flow<>(actionDef, chain);
    flow.register(registry);
    return flow;
  }

  /**
   * Defines a new streaming flow and registers it.
   *
   * @param registry
   *            the registry to register with
   * @param name
   *            the flow name
   * @param inputClass
   *            the input type class
   * @param outputClass
   *            the output type class
   * @param fn
   *            the streaming flow function
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @param <S>
   *            stream chunk type
   * @return the created flow
   */
  public static <I, O, S> Flow<I, O, S> defineStreaming(Registry registry, String name, Class<I> inputClass,
      Class<O> outputClass, ActionDef.StreamingFunction<I, O, S> fn) {
    ActionDef<I, O, S> actionDef = ActionDef.createStreaming(name, ActionType.FLOW, null, null, inputClass,
        outputClass, (ctx, input, cb) -> {
          ActionContext flowCtx = ctx.withFlowName(name);
          return fn.apply(flowCtx, input, cb);
        });

    Flow<I, O, S> flow = new Flow<>(actionDef);
    flow.register(registry);
    return flow;
  }

  /**
   * Runs a named step within the current flow. Each call to run results in a new
   * step with its own trace span.
   *
   * @param ctx
   *            the action context (must be a flow context)
   * @param name
   *            the step name
   * @param fn
   *            the step function
   * @param <T>
   *            the step output type
   * @return the step result
   * @throws GenkitException
   *             if not called from within a flow
   */
  public static <T> T run(ActionContext ctx, String name, Function<Void, T> fn) throws GenkitException {
    if (ctx.getFlowName() == null) {
      throw new GenkitException("Flow.run(\"" + name + "\"): must be called from within a flow");
    }

    SpanMetadata spanMetadata = SpanMetadata.builder().name(name).type("flowStep").subtype("flowStep").build();

    return Tracer.runInNewSpan(ctx, spanMetadata, null, (spanCtx, input) -> {
      try {
        return fn.apply(null);
      } catch (Exception e) {
        if (e instanceof GenkitException) {
          throw (GenkitException) e;
        }
        throw new GenkitException("Flow step failed: " + e.getMessage(), e);
      }
    });
  }

  @Override
  public String getName() {
    return actionDef.getName();
  }

  @Override
  public ActionType getType() {
    return actionDef.getType();
  }

  @Override
  public ActionDesc getDesc() {
    return actionDef.getDesc();
  }

  @Override
  public O run(ActionContext ctx, I input) throws GenkitException {
    return actionDef.run(ctx, input);
  }

  @Override
  public O run(ActionContext ctx, I input, Consumer<S> streamCallback) throws GenkitException {
    return actionDef.run(ctx, input, streamCallback);
  }

  @Override
  public JsonNode runJson(ActionContext ctx, JsonNode input, Consumer<JsonNode> streamCallback)
      throws GenkitException {
    return actionDef.runJson(ctx, input, streamCallback);
  }

  @Override
  public ActionRunResult<JsonNode> runJsonWithTelemetry(ActionContext ctx, JsonNode input,
      Consumer<JsonNode> streamCallback) throws GenkitException {
    return actionDef.runJsonWithTelemetry(ctx, input, streamCallback);
  }

  @Override
  public Map<String, Object> getInputSchema() {
    return actionDef.getInputSchema();
  }

  @Override
  public Map<String, Object> getOutputSchema() {
    return actionDef.getOutputSchema();
  }

  @Override
  public Map<String, Object> getMetadata() {
    return actionDef.getMetadata();
  }

  @Override
  public void register(Registry registry) {
    actionDef.register(registry);
  }

  /**
   * Returns the middleware chain for this flow.
   *
   * @return the middleware chain
   */
  public MiddlewareChain<I, O> getMiddlewareChain() {
    return middlewareChain;
  }

  /**
   * Creates a copy of this flow with additional middleware.
   *
   * @param middleware
   *            the middleware to add
   * @return a new flow with the middleware added
   */
  public Flow<I, O, S> withMiddleware(Middleware<I, O> middleware) {
    MiddlewareChain<I, O> newChain = middlewareChain.copy();
    newChain.use(middleware);
    return new Flow<>(actionDef, newChain);
  }

  /**
   * Creates a copy of this flow with additional middleware.
   *
   * @param middlewareList
   *            the middleware to add
   * @return a new flow with the middleware added
   */
  public Flow<I, O, S> withMiddleware(List<Middleware<I, O>> middlewareList) {
    MiddlewareChain<I, O> newChain = middlewareChain.copy();
    newChain.useAll(middlewareList);
    return new Flow<>(actionDef, newChain);
  }

  /**
   * Streams the flow output with the given input. Returns a consumer that can be
   * used with a yield-style iteration pattern.
   *
   * @param ctx
   *            the action context
   * @param input
   *            the flow input
   * @param consumer
   *            the consumer for streaming values
   */
  public void stream(ActionContext ctx, I input, Consumer<StreamingFlowValue<O, S>> consumer) {
    Consumer<S> streamCallback = chunk -> {
      consumer.accept(new StreamingFlowValue<>(false, null, chunk));
    };

    try {
      O output = run(ctx, input, streamCallback);
      consumer.accept(new StreamingFlowValue<>(true, output, null));
    } catch (GenkitException e) {
      throw e;
    }
  }

  /**
   * StreamingFlowValue represents either a streamed chunk or the final output of
   * a flow.
   *
   * @param <O>
   *            the output type
   * @param <S>
   *            the stream chunk type
   */
  public static class StreamingFlowValue<O, S> {
    private final boolean done;
    private final O output;
    private final S stream;

    /**
     * Creates a new StreamingFlowValue.
     *
     * @param done
     *            true if this is the final output
     * @param output
     *            the final output (valid if done is true)
     * @param stream
     *            the stream chunk (valid if done is false)
     */
    public StreamingFlowValue(boolean done, O output, S stream) {
      this.done = done;
      this.output = output;
      this.stream = stream;
    }

    /**
     * Returns true if this is the final output.
     *
     * @return true if done
     */
    public boolean isDone() {
      return done;
    }

    /**
     * Returns the final output. Valid only if isDone() returns true.
     *
     * @return the output
     */
    public O getOutput() {
      return output;
    }

    /**
     * Returns the stream chunk. Valid only if isDone() returns false.
     *
     * @return the stream chunk
     */
    public S getStream() {
      return stream;
    }
  }
}
