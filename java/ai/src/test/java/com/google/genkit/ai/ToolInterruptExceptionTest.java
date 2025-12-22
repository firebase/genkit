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

import static org.junit.jupiter.api.Assertions.*;

import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

/**
 * Unit tests for ToolInterruptException.
 */
class ToolInterruptExceptionTest {

  @Test
  void testConstructorWithMetadata() {
    Map<String, Object> metadata = new HashMap<>();
    metadata.put("key1", "value1");
    metadata.put("key2", 42);

    ToolInterruptException exception = new ToolInterruptException(metadata);

    assertNotNull(exception.getMetadata());
    assertEquals(2, exception.getMetadata().size());
    assertEquals("value1", exception.getMetadata().get("key1"));
    assertEquals(42, exception.getMetadata().get("key2"));
    assertEquals("Tool execution interrupted", exception.getMessage());
  }

  @Test
  void testConstructorWithNullMetadata() {
    ToolInterruptException exception = new ToolInterruptException(null);

    assertNotNull(exception.getMetadata());
    assertTrue(exception.getMetadata().isEmpty());
  }

  @Test
  void testConstructorWithEmptyMetadata() {
    ToolInterruptException exception = new ToolInterruptException(new HashMap<>());

    assertNotNull(exception.getMetadata());
    assertTrue(exception.getMetadata().isEmpty());
  }

  @Test
  void testMetadataIsImmutableCopy() {
    Map<String, Object> metadata = new HashMap<>();
    metadata.put("key", "original");

    ToolInterruptException exception = new ToolInterruptException(metadata);

    // Modify original
    metadata.put("key", "modified");
    metadata.put("newKey", "newValue");

    // Exception's metadata should not change
    assertEquals("original", exception.getMetadata().get("key"));
    assertFalse(exception.getMetadata().containsKey("newKey"));
  }

  @Test
  void testCanCatchAsException() {
    Map<String, Object> metadata = Map.of("action", "confirm");

    try {
      throw new ToolInterruptException(metadata);
    } catch (ToolInterruptException e) {
      assertEquals("confirm", e.getMetadata().get("action"));
    }
  }

  @Test
  void testIsRuntimeException() {
    ToolInterruptException exception = new ToolInterruptException(new HashMap<>());
    assertTrue(exception instanceof RuntimeException);
  }
}
