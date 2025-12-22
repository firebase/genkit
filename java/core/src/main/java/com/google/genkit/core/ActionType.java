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

/**
 * ActionType represents the kind of an action. Each type corresponds to a
 * different Genkit primitive or capability.
 */
public enum ActionType {
  /**
   * A retriever action that fetches documents from a vector store or other
   * source.
   */
  RETRIEVER("retriever"),

  /**
   * An indexer action that indexes documents into a vector store.
   */
  INDEXER("indexer"),

  /**
   * An embedder action that converts content to vector embeddings.
   */
  EMBEDDER("embedder"),

  /**
   * An evaluator action that assesses the quality of generated content.
   */
  EVALUATOR("evaluator"),

  /**
   * A flow action representing a user-defined workflow.
   */
  FLOW("flow"),

  /**
   * A model action for AI model inference.
   */
  MODEL("model"),

  /**
   * A background model action for long-running inference operations.
   */
  BACKGROUND_MODEL("background-model"),

  /**
   * An executable prompt action that can generate content directly. Uses the key
   * format "/executable-prompt/{name}" to match Go SDK. This is the primary
   * prompt type used by the Genkit Developer UI.
   */
  EXECUTABLE_PROMPT("executable-prompt"),

  /**
   * A prompt action that renders templates to generate model requests. Uses the
   * key format "/prompt/{name}" to match the JS SDK.
   */
  PROMPT("prompt"),

  /**
   * A resource action for managing external resources.
   */
  RESOURCE("resource"),

  /**
   * A tool action that can be called by AI models.
   */
  TOOL("tool"),

  /**
   * A tool action using the v2 multipart format.
   */
  TOOL_V2("tool.v2"),

  /**
   * A utility action for internal operations.
   */
  UTIL("util"),

  /**
   * A custom action type for user-defined action types.
   */
  CUSTOM("custom"),

  /**
   * An action for checking operation status.
   */
  CHECK_OPERATION("check-operation"),

  /**
   * An action for cancelling operations.
   */
  CANCEL_OPERATION("cancel-operation");

  private final String value;

  ActionType(String value) {
    this.value = value;
  }

  /**
   * Returns the string value of the action type.
   *
   * @return the action type string value
   */
  public String getValue() {
    return value;
  }

  /**
   * Creates an ActionType from a string value.
   *
   * @param value
   *            the string value
   * @return the corresponding ActionType
   * @throws IllegalArgumentException
   *             if the value doesn't match any ActionType
   */
  public static ActionType fromValue(String value) {
    for (ActionType type : values()) {
      if (type.value.equals(value)) {
        return type;
      }
    }
    throw new IllegalArgumentException("Unknown action type: " + value);
  }

  /**
   * Creates the registry key for an action of this type with the given name.
   *
   * @param name
   *            the action name
   * @return the registry key
   */
  public String keyFromName(String name) {
    return "/" + value + "/" + name;
  }

  @Override
  public String toString() {
    return value;
  }
}
