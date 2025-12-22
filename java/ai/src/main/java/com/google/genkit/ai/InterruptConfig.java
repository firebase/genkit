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

import java.util.Map;
import java.util.function.Function;

/**
 * Configuration for defining an interrupt tool.
 *
 * <p>
 * An interrupt is a special type of tool that pauses generation to request user
 * input (human-in-the-loop pattern). When the model calls an interrupt tool,
 * execution stops and the interrupt information is returned to the caller for
 * handling.
 *
 * <p>
 * Example usage:
 *
 * <pre>{@code
 * InterruptConfig<ConfirmInput, ConfirmOutput> config = InterruptConfig.<ConfirmInput, ConfirmOutput>builder()
 * 		.name("confirmAction").description("Ask user to confirm the action").inputType(ConfirmInput.class)
 * 		.outputType(ConfirmOutput.class).requestMetadata(input -> Map.of("action", input.getAction())).build();
 * }</pre>
 *
 * @param <I>
 *            the input type
 * @param <O>
 *            the output type (response type)
 */
public class InterruptConfig<I, O> {

  private String name;
  private String description;
  private Class<I> inputType;
  private Class<O> outputType;
  private Map<String, Object> inputSchema;
  private Map<String, Object> outputSchema;
  private Function<I, Map<String, Object>> requestMetadata;

  /** Default constructor. */
  public InterruptConfig() {
  }

  /**
   * Gets the interrupt name.
   *
   * @return the name
   */
  public String getName() {
    return name;
  }

  /**
   * Sets the interrupt name.
   *
   * @param name
   *            the name
   */
  public void setName(String name) {
    this.name = name;
  }

  /**
   * Gets the description.
   *
   * @return the description
   */
  public String getDescription() {
    return description;
  }

  /**
   * Sets the description.
   *
   * @param description
   *            the description
   */
  public void setDescription(String description) {
    this.description = description;
  }

  /**
   * Gets the input type class.
   *
   * @return the input type class
   */
  public Class<I> getInputType() {
    return inputType;
  }

  /**
   * Sets the input type class.
   *
   * @param inputType
   *            the input type class
   */
  public void setInputType(Class<I> inputType) {
    this.inputType = inputType;
  }

  /**
   * Gets the output type class.
   *
   * @return the output type class
   */
  public Class<O> getOutputType() {
    return outputType;
  }

  /**
   * Sets the output type class.
   *
   * @param outputType
   *            the output type class
   */
  public void setOutputType(Class<O> outputType) {
    this.outputType = outputType;
  }

  /**
   * Gets the input schema.
   *
   * @return the input schema
   */
  public Map<String, Object> getInputSchema() {
    return inputSchema;
  }

  /**
   * Sets the input schema.
   *
   * @param inputSchema
   *            the input schema
   */
  public void setInputSchema(Map<String, Object> inputSchema) {
    this.inputSchema = inputSchema;
  }

  /**
   * Gets the output schema.
   *
   * @return the output schema
   */
  public Map<String, Object> getOutputSchema() {
    return outputSchema;
  }

  /**
   * Sets the output schema.
   *
   * @param outputSchema
   *            the output schema
   */
  public void setOutputSchema(Map<String, Object> outputSchema) {
    this.outputSchema = outputSchema;
  }

  /**
   * Gets the request metadata function.
   *
   * @return the request metadata function
   */
  public Function<I, Map<String, Object>> getRequestMetadata() {
    return requestMetadata;
  }

  /**
   * Sets the request metadata function.
   *
   * @param requestMetadata
   *            the request metadata function
   */
  public void setRequestMetadata(Function<I, Map<String, Object>> requestMetadata) {
    this.requestMetadata = requestMetadata;
  }

  /**
   * Creates a new builder.
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

  /** Builder for InterruptConfig. */
  public static class Builder<I, O> {
    private String name;
    private String description;
    private Class<I> inputType;
    private Class<O> outputType;
    private Map<String, Object> inputSchema;
    private Map<String, Object> outputSchema;
    private Function<I, Map<String, Object>> requestMetadata;

    /**
     * Sets the interrupt name.
     *
     * @param name
     *            the name
     * @return this builder
     */
    public Builder<I, O> name(String name) {
      this.name = name;
      return this;
    }

    /**
     * Sets the description.
     *
     * @param description
     *            the description
     * @return this builder
     */
    public Builder<I, O> description(String description) {
      this.description = description;
      return this;
    }

    /**
     * Sets the input type class.
     *
     * @param inputType
     *            the input type class
     * @return this builder
     */
    public Builder<I, O> inputType(Class<I> inputType) {
      this.inputType = inputType;
      return this;
    }

    /**
     * Sets the output type class.
     *
     * @param outputType
     *            the output type class
     * @return this builder
     */
    public Builder<I, O> outputType(Class<O> outputType) {
      this.outputType = outputType;
      return this;
    }

    /**
     * Sets the input schema.
     *
     * @param inputSchema
     *            the input schema
     * @return this builder
     */
    public Builder<I, O> inputSchema(Map<String, Object> inputSchema) {
      this.inputSchema = inputSchema;
      return this;
    }

    /**
     * Sets the output schema.
     *
     * @param outputSchema
     *            the output schema
     * @return this builder
     */
    public Builder<I, O> outputSchema(Map<String, Object> outputSchema) {
      this.outputSchema = outputSchema;
      return this;
    }

    /**
     * Sets the request metadata function.
     *
     * <p>
     * This function is called with the tool input when the interrupt is triggered,
     * and should return metadata that will be included in the interrupt.
     *
     * @param requestMetadata
     *            function to generate metadata from input
     * @return this builder
     */
    public Builder<I, O> requestMetadata(Function<I, Map<String, Object>> requestMetadata) {
      this.requestMetadata = requestMetadata;
      return this;
    }

    /**
     * Builds the InterruptConfig.
     *
     * @return the built config
     */
    public InterruptConfig<I, O> build() {
      InterruptConfig<I, O> config = new InterruptConfig<>();
      config.setName(name);
      config.setDescription(description);
      config.setInputType(inputType);
      config.setOutputType(outputType);
      config.setInputSchema(inputSchema);
      config.setOutputSchema(outputSchema);
      config.setRequestMetadata(requestMetadata);
      return config;
    }
  }
}
