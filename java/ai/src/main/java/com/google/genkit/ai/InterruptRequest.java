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

/**
 * Represents an interrupt request from a tool.
 *
 * <p>
 * When a tool triggers an interrupt, this class captures the tool request
 * information and any associated metadata. The caller can then respond to the
 * interrupt or restart the tool.
 *
 * <p>
 * Example usage:
 *
 * <pre>{@code
 * // Check for interrupts in response
 * List<InterruptRequest> interrupts = response.getInterrupts();
 * if (!interrupts.isEmpty()) {
 * 	InterruptRequest interrupt = interrupts.get(0);
 * 	// Present to user and get response
 * 	String userResponse = getUserInput(interrupt.getToolRequest().getInput());
 *
 * 	// Resume with user's response
 * 	ModelResponse resumed = chat.send(message, SendOptions.builder()
 * 			.resume(ResumeOptions.builder().respond(interrupt.respond(userResponse)).build()).build());
 * }
 * }</pre>
 */
public class InterruptRequest {

  private final ToolRequest toolRequest;
  private final Map<String, Object> metadata;

  /**
   * Creates a new InterruptRequest.
   *
   * @param toolRequest
   *            the original tool request
   * @param metadata
   *            the interrupt metadata
   */
  public InterruptRequest(ToolRequest toolRequest, Map<String, Object> metadata) {
    this.toolRequest = toolRequest;
    this.metadata = metadata != null ? new HashMap<>(metadata) : new HashMap<>();
    // Mark as interrupt
    this.metadata.put("interrupt", true);
  }

  /**
   * Gets the tool request that was interrupted.
   *
   * @return the tool request
   */
  public ToolRequest getToolRequest() {
    return toolRequest;
  }

  /**
   * Gets the interrupt metadata.
   *
   * @return the metadata
   */
  public Map<String, Object> getMetadata() {
    return metadata;
  }

  /**
   * Checks if this is an interrupt.
   *
   * @return true if this is an interrupt (always true for InterruptRequest)
   */
  public boolean isInterrupt() {
    return true;
  }

  /**
   * Creates a tool response to respond to this interrupt.
   *
   * @param output
   *            the output data to respond with
   * @return a ToolResponse part
   */
  public ToolResponse respond(Object output) {
    return respond(output, null);
  }

  /**
   * Creates a tool response to respond to this interrupt with additional
   * metadata.
   *
   * @param output
   *            the output data to respond with
   * @param responseMetadata
   *            additional metadata for the response
   * @return a ToolResponse part
   */
  public ToolResponse respond(Object output, Map<String, Object> responseMetadata) {
    ToolResponse response = new ToolResponse();
    response.setName(toolRequest.getName());
    response.setRef(toolRequest.getRef());
    response.setOutput(output);

    Map<String, Object> meta = new HashMap<>();
    meta.put("interruptResponse", responseMetadata != null ? responseMetadata : true);
    response.setMetadata(meta);

    return response;
  }

  /**
   * Creates a tool request to restart this interrupt.
   *
   * @return a ToolRequest to restart execution
   */
  public ToolRequest restart() {
    return restart(null, null);
  }

  /**
   * Creates a tool request to restart this interrupt with new metadata.
   *
   * @param resumedMetadata
   *            metadata for the resumed execution
   * @return a ToolRequest to restart execution
   */
  public ToolRequest restart(Map<String, Object> resumedMetadata) {
    return restart(resumedMetadata, null);
  }

  /**
   * Creates a tool request to restart this interrupt with new input.
   *
   * @param resumedMetadata
   *            metadata for the resumed execution
   * @param replaceInput
   *            new input to replace the original
   * @return a ToolRequest to restart execution
   */
  public ToolRequest restart(Map<String, Object> resumedMetadata, Object replaceInput) {
    ToolRequest request = new ToolRequest();
    request.setName(toolRequest.getName());
    request.setRef(toolRequest.getRef());
    request.setInput(replaceInput != null ? replaceInput : toolRequest.getInput());

    Map<String, Object> meta = new HashMap<>(this.metadata);
    meta.put("resumed", resumedMetadata != null ? resumedMetadata : true);
    if (replaceInput != null) {
      meta.put("replacedInput", toolRequest.getInput());
    }
    request.setMetadata(meta);

    return request;
  }

  @Override
  public String toString() {
    return "InterruptRequest{" + "toolName=" + (toolRequest != null ? toolRequest.getName() : null) + ", metadata="
        + metadata + '}';
  }
}
