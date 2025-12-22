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

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * Unit tests for Role.
 */
class RoleTest {

  @Test
  void testUserRole() {
    assertEquals("user", Role.USER.getValue());
    assertEquals("user", Role.USER.toString());
  }

  @Test
  void testModelRole() {
    assertEquals("model", Role.MODEL.getValue());
    assertEquals("model", Role.MODEL.toString());
  }

  @Test
  void testSystemRole() {
    assertEquals("system", Role.SYSTEM.getValue());
    assertEquals("system", Role.SYSTEM.toString());
  }

  @Test
  void testToolRole() {
    assertEquals("tool", Role.TOOL.getValue());
    assertEquals("tool", Role.TOOL.toString());
  }

  @Test
  void testFromValueUser() {
    assertEquals(Role.USER, Role.fromValue("user"));
  }

  @Test
  void testFromValueModel() {
    assertEquals(Role.MODEL, Role.fromValue("model"));
  }

  @Test
  void testFromValueSystem() {
    assertEquals(Role.SYSTEM, Role.fromValue("system"));
  }

  @Test
  void testFromValueTool() {
    assertEquals(Role.TOOL, Role.fromValue("tool"));
  }

  @Test
  void testFromValueCaseInsensitive() {
    assertEquals(Role.USER, Role.fromValue("USER"));
    assertEquals(Role.USER, Role.fromValue("User"));
    assertEquals(Role.MODEL, Role.fromValue("MODEL"));
    assertEquals(Role.MODEL, Role.fromValue("Model"));
    assertEquals(Role.SYSTEM, Role.fromValue("SYSTEM"));
    assertEquals(Role.SYSTEM, Role.fromValue("System"));
    assertEquals(Role.TOOL, Role.fromValue("TOOL"));
    assertEquals(Role.TOOL, Role.fromValue("Tool"));
  }

  @Test
  void testFromValueAssistantMapsToModel() {
    // For compatibility with other APIs that use "assistant" role
    assertEquals(Role.MODEL, Role.fromValue("assistant"));
    assertEquals(Role.MODEL, Role.fromValue("ASSISTANT"));
    assertEquals(Role.MODEL, Role.fromValue("Assistant"));
  }

  @Test
  void testFromValueUnknown() {
    assertThrows(IllegalArgumentException.class, () -> Role.fromValue("unknown"));
  }

  @Test
  void testFromValueNull() {
    assertThrows(IllegalArgumentException.class, () -> Role.fromValue(null));
  }

  @Test
  void testFromValueEmpty() {
    assertThrows(IllegalArgumentException.class, () -> Role.fromValue(""));
  }

  @ParameterizedTest
  @ValueSource(strings = {"bot", "ai", "human", "admin", "moderator"})
  void testFromValueInvalidValues(String value) {
    assertThrows(IllegalArgumentException.class, () -> Role.fromValue(value));
  }

  @Test
  void testEnumValues() {
    Role[] roles = Role.values();
    assertEquals(4, roles.length);
  }

  @Test
  void testEnumValueOf() {
    assertEquals(Role.USER, Role.valueOf("USER"));
    assertEquals(Role.MODEL, Role.valueOf("MODEL"));
    assertEquals(Role.SYSTEM, Role.valueOf("SYSTEM"));
    assertEquals(Role.TOOL, Role.valueOf("TOOL"));
  }

  @Test
  void testAllRolesHaveUniqueValues() {
    Role[] roles = Role.values();
    for (int i = 0; i < roles.length; i++) {
      for (int j = i + 1; j < roles.length; j++) {
        assertNotEquals(roles[i].getValue(), roles[j].getValue(),
            String.format("Roles %s and %s have same value", roles[i].name(), roles[j].name()));
      }
    }
  }
}
