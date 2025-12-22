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

/**
 * Exception thrown when an agent tool is called to signal a handoff.
 *
 * <p>
 * When the model calls an agent-as-tool, this exception is thrown to signal
 * that the chat should switch context to the target agent. The Chat class
 * catches this exception and updates its system prompt, tools, and model to
 * those of the target agent.
 *
 * <p>
 * This enables the "handoff" pattern where conversations can be transferred
 * between specialized agents.
 */
public class AgentHandoffException extends RuntimeException {

  private final String targetAgentName;
  private final AgentConfig targetAgentConfig;
  private final Map<String, Object> handoffInput;

  /**
   * Creates a new AgentHandoffException.
   *
   * @param targetAgentName
   *            the name of the agent to hand off to
   * @param targetAgentConfig
   *            the configuration of the target agent
   * @param handoffInput
   *            the input passed to the agent tool (can be used for context)
   */
  public AgentHandoffException(String targetAgentName, AgentConfig targetAgentConfig,
      Map<String, Object> handoffInput) {
    super("Handoff to agent: " + targetAgentName);
    this.targetAgentName = targetAgentName;
    this.targetAgentConfig = targetAgentConfig;
    this.handoffInput = handoffInput;
  }

  /**
   * Gets the name of the target agent.
   *
   * @return the target agent name
   */
  public String getTargetAgentName() {
    return targetAgentName;
  }

  /**
   * Gets the configuration of the target agent.
   *
   * @return the target agent config
   */
  public AgentConfig getTargetAgentConfig() {
    return targetAgentConfig;
  }

  /**
   * Gets the input passed to the agent tool.
   *
   * @return the handoff input
   */
  public Map<String, Object> getHandoffInput() {
    return handoffInput;
  }
}
