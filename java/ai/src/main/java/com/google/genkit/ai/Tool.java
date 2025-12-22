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
import com.google.genkit.core.tracing.SpanMetadata;
import com.google.genkit.core.tracing.Tracer;

/**
 * Tool represents a function that can be called by an AI model.
 *
 * Tools allow models to interact with external systems and perform actions
 * during generation.
 *
 * @param <I>
 *            the input type
 * @param <O>
 *            the output type
 */
public class Tool<I, O> implements Action<I, O, Void> {

  private final String name;
  private final String description;
  private final Map<String, Object> inputSchema;
  private final Map<String, Object> outputSchema;
  private final BiFunction<ActionContext, I, O> handler;
  private final Map<String, Object> metadata;
  private final Class<I> inputClass;

  /**
   * Creates a new Tool.
   *
   * @param name
   *            the tool name
   * @param description
   *            the tool description
   * @param inputSchema
   *            the input JSON schema
   * @param outputSchema
   *            the output JSON schema
   * @param inputClass
   *            the input class for JSON deserialization
   * @param handler
   *            the tool handler function
   */
  public Tool(String name, String description, Map<String, Object> inputSchema, Map<String, Object> outputSchema,
      Class<I> inputClass, BiFunction<ActionContext, I, O> handler) {
    this.name = name;
    this.description = description;
    this.inputSchema = inputSchema;
    this.outputSchema = outputSchema;
    this.inputClass = inputClass;
    this.handler = handler;
    this.metadata = new HashMap<>();
    this.metadata.put("description", description);
  }

  /**
   * Creates a builder for Tool.
   *
   * @param <I>
   *            the input type
   * @param <O>
   *            the output type
   * @return a new builder
   */
  public static <I, O> Builder<I, O> builder() {
    return new Builder<>();
  }

  @Override
  public String getName() {
    return name;
  }

  @Override
  public ActionType getType() {
    return ActionType.TOOL;
  }

  @Override
  public ActionDesc getDesc() {
    return ActionDesc.builder().type(ActionType.TOOL).name(name).description(description).inputSchema(inputSchema)
        .outputSchema(outputSchema).build();
  }

  @Override
  public O run(ActionContext ctx, I input) throws GenkitException {
    SpanMetadata spanMetadata = SpanMetadata.builder().name(name).type(ActionType.TOOL.getValue()).subtype("tool")
        .build();

    String flowName = ctx.getFlowName();
    if (flowName != null) {
      spanMetadata.getAttributes().put("genkit:metadata:flow:name", flowName);
    }

    return Tracer.runInNewSpan(ctx, spanMetadata, input, (spanCtx, in) -> {
      try {
        O result = handler.apply(ctx.withSpanContext(spanCtx), in);
        return result;
      } catch (AgentHandoffException e) {
        // Re-throw agent handoff exceptions for multi-agent pattern
        throw e;
      } catch (ToolInterruptException e) {
        // Re-throw interrupt exceptions for human-in-the-loop pattern
        throw e;
      } catch (Exception e) {
        if (e instanceof GenkitException) {
          throw (GenkitException) e;
        }
        throw new GenkitException("Tool execution failed: " + e.getMessage(), e);
      }
    });
  }

  @Override
  public O run(ActionContext ctx, I input, Consumer<Void> streamCallback) throws GenkitException {
    return run(ctx, input);
  }

  @Override
  @SuppressWarnings("unchecked")
  public JsonNode runJson(ActionContext ctx, JsonNode input, Consumer<JsonNode> streamCallback)
      throws GenkitException {
    I typedInput = inputClass != null ? JsonUtils.fromJsonNode(input, inputClass) : (I) input;
    O output = run(ctx, typedInput);
    return JsonUtils.toJsonNode(output);
  }

  @Override
  public ActionRunResult<JsonNode> runJsonWithTelemetry(ActionContext ctx, JsonNode input,
      Consumer<JsonNode> streamCallback) throws GenkitException {
    JsonNode result = runJson(ctx, input, streamCallback);
    return new ActionRunResult<>(result, null, null);
  }

  @Override
  public Map<String, Object> getInputSchema() {
    return inputSchema;
  }

  @Override
  public Map<String, Object> getOutputSchema() {
    return outputSchema;
  }

  @Override
  public Map<String, Object> getMetadata() {
    return metadata;
  }

  @Override
  public void register(Registry registry) {
    registry.registerAction(ActionType.TOOL.keyFromName(name), this);
  }

  /**
   * Gets the tool description.
   *
   * @return the description
   */
  public String getDescription() {
    return description;
  }

  /**
   * Gets the input class for JSON deserialization.
   *
   * @return the input class, or null if not specified
   */
  public Class<I> getInputClass() {
    return inputClass;
  }

  /**
   * Gets the tool definition for use in model requests.
   *
   * @return the tool definition
   */
  public ToolDefinition getDefinition() {
    return new ToolDefinition(name, description, inputSchema, outputSchema);
  }

  /**
   * Constructs a tool response for an interrupted tool request.
   *
   * <p>
   * This method is used when resuming generation after an interrupt. It creates a
   * tool response part that can be passed to {@link ResumeOptions#getRespond()}.
   *
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * // Get interrupt from response
   * Part interrupt = response.getInterrupts().get(0);
   * 
   * // Create response with user-provided data
   * Part responseData = tool.respond(interrupt, userConfirmation);
   * 
   * // Resume generation
   * ModelResponse resumed = genkit.generate(GenerateOptions.builder().messages(response.getMessages())
   * 		.resume(ResumeOptions.builder().respond(responseData).build()).build());
   * }</pre>
   *
   * @param interrupt
   *            the interrupted tool request part
   * @param output
   *            the output data to respond with
   * @return a tool response part
   */
  public Part respond(Part interrupt, O output) {
    return respond(interrupt, output, null);
  }

  /**
   * Constructs a tool response for an interrupted tool request with metadata.
   *
   * @param interrupt
   *            the interrupted tool request part
   * @param output
   *            the output data to respond with
   * @param metadata
   *            optional metadata to include in the response
   * @return a tool response part
   */
  public Part respond(Part interrupt, O output, Map<String, Object> metadata) {
    if (interrupt == null || interrupt.getToolRequest() == null) {
      throw new IllegalArgumentException("Interrupt must be a tool request part");
    }

    ToolRequest toolRequest = interrupt.getToolRequest();
    Part responsePart = new Part();
    ToolResponse toolResponse = new ToolResponse(toolRequest.getRef(), toolRequest.getName(), output);
    responsePart.setToolResponse(toolResponse);

    // Add interruptResponse marker in metadata
    Map<String, Object> responseMetadata = new HashMap<>();
    responseMetadata.put("interruptResponse", true);
    if (metadata != null) {
      responseMetadata.putAll(metadata);
    }
    responsePart.setMetadata(responseMetadata);

    return responsePart;
  }

  /**
   * Constructs a restart request for an interrupted tool.
   *
   * <p>
   * This method creates a tool request that will cause the tool to be
   * re-executed. The resumed metadata will be passed to the tool handler.
   *
   * <p>
   * Example usage:
   * 
   * <pre>{@code
   * // Get interrupt from response
   * Part interrupt = response.getInterrupts().get(0);
   * 
   * // Create restart request with confirmation metadata
   * Part restartRequest = tool.restart(interrupt, Map.of("confirmed", true));
   * 
   * // Resume generation
   * ModelResponse resumed = genkit.generate(GenerateOptions.builder().messages(response.getMessages())
   * 		.resume(ResumeOptions.builder().restart(restartRequest).build()).build());
   * }</pre>
   *
   * @param interrupt
   *            the interrupted tool request part
   * @param resumedMetadata
   *            metadata to pass to the tool handler's resumed context
   * @return a tool request part for restart
   */
  public Part restart(Part interrupt, Map<String, Object> resumedMetadata) {
    return restart(interrupt, resumedMetadata, null);
  }

  /**
   * Constructs a restart request with replacement input.
   *
   * @param interrupt
   *            the interrupted tool request part
   * @param resumedMetadata
   *            metadata to pass to the tool handler's resumed context
   * @param replaceInput
   *            optional new input to use instead of the original
   * @return a tool request part for restart
   */
  public Part restart(Part interrupt, Map<String, Object> resumedMetadata, I replaceInput) {
    if (interrupt == null || interrupt.getToolRequest() == null) {
      throw new IllegalArgumentException("Interrupt must be a tool request part");
    }

    ToolRequest originalRequest = interrupt.getToolRequest();
    Part restartPart = new Part();

    // Create new tool request with either original or replacement input
    Object inputToUse = replaceInput != null ? replaceInput : originalRequest.getInput();
    ToolRequest restartRequest = new ToolRequest(originalRequest.getName(), inputToUse);
    restartRequest.setRef(originalRequest.getRef());
    restartPart.setToolRequest(restartRequest);

    // Add resumed metadata
    Map<String, Object> restartMetadata = new HashMap<>();
    restartMetadata.put("source", "restart");
    if (resumedMetadata != null) {
      restartMetadata.put("resumed", resumedMetadata);
    } else {
      restartMetadata.put("resumed", true);
    }
    restartPart.setMetadata(restartMetadata);

    return restartPart;
  }

  /**
   * Builder for Tool.
   *
   * @param <I>
   *            the input type
   * @param <O>
   *            the output type
   */
  public static class Builder<I, O> {
    private String name;
    private String description;
    private Map<String, Object> inputSchema;
    private Map<String, Object> outputSchema;
    private Class<I> inputClass;
    private BiFunction<ActionContext, I, O> handler;

    public Builder<I, O> name(String name) {
      this.name = name;
      return this;
    }

    public Builder<I, O> description(String description) {
      this.description = description;
      return this;
    }

    public Builder<I, O> inputSchema(Map<String, Object> inputSchema) {
      this.inputSchema = inputSchema;
      return this;
    }

    public Builder<I, O> outputSchema(Map<String, Object> outputSchema) {
      this.outputSchema = outputSchema;
      return this;
    }

    public Builder<I, O> inputClass(Class<I> inputClass) {
      this.inputClass = inputClass;
      return this;
    }

    public Builder<I, O> handler(BiFunction<ActionContext, I, O> handler) {
      this.handler = handler;
      return this;
    }

    public Tool<I, O> build() {
      if (name == null) {
        throw new IllegalStateException("Tool name is required");
      }
      if (handler == null) {
        throw new IllegalStateException("Tool handler is required");
      }
      return new Tool<>(name, description, inputSchema, outputSchema, inputClass, handler);
    }
  }
}
