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

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

/**
 * Role represents the role of a message sender in a conversation.
 */
public enum Role {
  USER("user"), MODEL("model"), SYSTEM("system"), TOOL("tool");

  private final String value;

  Role(String value) {
    this.value = value;
  }

  @JsonValue
  public String getValue() {
    return value;
  }

  @JsonCreator
  public static Role fromValue(String value) {
    for (Role role : values()) {
      if (role.value.equalsIgnoreCase(value)) {
        return role;
      }
    }
    // Try matching "assistant" to MODEL for compatibility
    if ("assistant".equalsIgnoreCase(value)) {
      return MODEL;
    }
    throw new IllegalArgumentException("Unknown role: " + value);
  }

  @Override
  public String toString() {
    return value;
  }
}
