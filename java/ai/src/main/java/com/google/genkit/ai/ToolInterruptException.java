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

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Exception thrown when a tool execution is interrupted.
 *
 * <p>
 * This exception is used to implement the interrupt pattern, which allows tools
 * to pause execution and request user input (human-in-the-loop). When a tool
 * throws this exception, the generation loop stops and returns the interrupt
 * information to the caller.
 *
 * <p>
 * Example usage:
 *
 * <pre>{@code
 * Tool<Input, Output> confirmTool = genkit.defineInterrupt(InterruptConfig.<Input, Output>builder()
 * 		.name("confirmAction").description("Ask user for confirmation before proceeding").inputSchema(Input.class)
 * 		.outputSchema(Output.class).build());
 * }</pre>
 */
public class ToolInterruptException extends RuntimeException {

  private final Map<String, Object> metadata;

  /** Creates a new ToolInterruptException with no metadata. */
  public ToolInterruptException() {
    super("Tool execution interrupted");
    this.metadata = Collections.emptyMap();
  }

  /**
   * Creates a new ToolInterruptException with metadata.
   *
   * @param metadata
   *            additional metadata about the interrupt
   */
  public ToolInterruptException(Map<String, Object> metadata) {
    super("Tool execution interrupted");
    this.metadata = metadata != null
        ? Collections.unmodifiableMap(new HashMap<>(metadata))
        : Collections.emptyMap();
  }

  /**
   * Creates a new ToolInterruptException with a message and metadata.
   *
   * @param message
   *            the exception message
   * @param metadata
   *            additional metadata about the interrupt
   */
  public ToolInterruptException(String message, Map<String, Object> metadata) {
    super(message);
    this.metadata = metadata != null
        ? Collections.unmodifiableMap(new HashMap<>(metadata))
        : Collections.emptyMap();
  }

  /**
   * Gets the interrupt metadata.
   *
   * @return the metadata, never null (returns empty map if not set)
   */
  public Map<String, Object> getMetadata() {
    return metadata;
  }
}
