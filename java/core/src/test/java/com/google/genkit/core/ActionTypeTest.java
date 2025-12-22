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

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;

/**
 * Unit tests for ActionType.
 */
class ActionTypeTest {

  @Test
  void testFlowType() {
    assertEquals("flow", ActionType.FLOW.toString());
  }

  @Test
  void testModelType() {
    assertEquals("model", ActionType.MODEL.toString());
  }

  @Test
  void testEmbedderType() {
    assertEquals("embedder", ActionType.EMBEDDER.toString());
  }

  @Test
  void testRetrieverType() {
    assertEquals("retriever", ActionType.RETRIEVER.toString());
  }

  @Test
  void testIndexerType() {
    assertEquals("indexer", ActionType.INDEXER.toString());
  }

  @Test
  void testEvaluatorType() {
    assertEquals("evaluator", ActionType.EVALUATOR.toString());
  }

  @Test
  void testToolType() {
    assertEquals("tool", ActionType.TOOL.toString());
  }

  @Test
  void testPromptType() {
    assertEquals("prompt", ActionType.PROMPT.toString());
  }

  @Test
  void testExecutablePromptType() {
    assertEquals("executable-prompt", ActionType.EXECUTABLE_PROMPT.toString());
  }

  @Test
  void testUtilType() {
    assertEquals("util", ActionType.UTIL.toString());
  }

  @Test
  void testCustomType() {
    assertEquals("custom", ActionType.CUSTOM.toString());
  }

  @Test
  void testKeyFromName() {
    String name = "myAction";
    String key = ActionType.FLOW.keyFromName(name);

    assertEquals("/flow/myAction", key);
  }

  @Test
  void testKeyFromNameModel() {
    String name = "gpt-4";
    String key = ActionType.MODEL.keyFromName(name);

    assertEquals("/model/gpt-4", key);
  }

  @Test
  void testKeyFromNameEmbedder() {
    String name = "text-embedding-ada";
    String key = ActionType.EMBEDDER.keyFromName(name);

    assertEquals("/embedder/text-embedding-ada", key);
  }

  @Test
  void testFromValue() {
    assertEquals(ActionType.FLOW, ActionType.fromValue("flow"));
    assertEquals(ActionType.MODEL, ActionType.fromValue("model"));
    assertEquals(ActionType.EMBEDDER, ActionType.fromValue("embedder"));
    assertEquals(ActionType.RETRIEVER, ActionType.fromValue("retriever"));
    assertEquals(ActionType.INDEXER, ActionType.fromValue("indexer"));
    assertEquals(ActionType.EVALUATOR, ActionType.fromValue("evaluator"));
    assertEquals(ActionType.TOOL, ActionType.fromValue("tool"));
    assertEquals(ActionType.PROMPT, ActionType.fromValue("prompt"));
    assertEquals(ActionType.UTIL, ActionType.fromValue("util"));
  }

  @Test
  void testFromValueIsCaseSensitive() {
    // The fromValue method is case-sensitive
    assertThrows(IllegalArgumentException.class, () -> ActionType.fromValue("FLOW"));
    assertThrows(IllegalArgumentException.class, () -> ActionType.fromValue("Flow"));
    assertThrows(IllegalArgumentException.class, () -> ActionType.fromValue("MODEL"));
    assertThrows(IllegalArgumentException.class, () -> ActionType.fromValue("Model"));
  }

  @Test
  void testFromValueUnknown() {
    assertThrows(IllegalArgumentException.class, () -> ActionType.fromValue("unknown-type"));
  }

  @ParameterizedTest
  @EnumSource(ActionType.class)
  void testAllTypesHaveStringValue(ActionType type) {
    assertNotNull(type.toString());
    assertFalse(type.toString().isEmpty());
  }

  @ParameterizedTest
  @EnumSource(ActionType.class)
  void testKeyFromNameFormat(ActionType type) {
    String key = type.keyFromName("testAction");

    assertTrue(key.startsWith("/"));
    assertTrue(key.contains("testAction"));
  }

  @Test
  void testAllTypesAreUnique() {
    ActionType[] types = ActionType.values();

    for (int i = 0; i < types.length; i++) {
      for (int j = i + 1; j < types.length; j++) {
        assertNotEquals(types[i].toString(), types[j].toString(), String
            .format("ActionTypes %s and %s have same string value", types[i].name(), types[j].name()));
      }
    }
  }

  @Test
  void testEnumValues() {
    ActionType[] types = ActionType.values();
    assertTrue(types.length > 0);
  }

  @Test
  void testEnumValueOf() {
    assertEquals(ActionType.FLOW, ActionType.valueOf("FLOW"));
    assertEquals(ActionType.MODEL, ActionType.valueOf("MODEL"));
  }
}
