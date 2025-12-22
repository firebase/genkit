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

package com.google.genkit.ai.session;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

/** Unit tests for SessionOptions. */
class SessionOptionsTest {

  @Test
  void testDefaultConstructor() {
    SessionOptions<String> options = new SessionOptions<>();

    assertNull(options.getStore());
    assertNull(options.getInitialState());
    assertNull(options.getSessionId());
  }

  @Test
  void testSetAndGetStore() {
    SessionOptions<String> options = new SessionOptions<>();
    InMemorySessionStore<String> store = new InMemorySessionStore<>();

    options.setStore(store);

    assertSame(store, options.getStore());
  }

  @Test
  void testSetAndGetInitialState() {
    SessionOptions<Integer> options = new SessionOptions<>();
    options.setInitialState(42);

    assertEquals(42, options.getInitialState());
  }

  @Test
  void testSetAndGetSessionId() {
    SessionOptions<String> options = new SessionOptions<>();
    options.setSessionId("custom-session-id");

    assertEquals("custom-session-id", options.getSessionId());
  }

  @Test
  void testBuilderEmpty() {
    SessionOptions<String> options = SessionOptions.<String>builder().build();

    assertNull(options.getStore());
    assertNull(options.getInitialState());
    assertNull(options.getSessionId());
  }

  @Test
  void testBuilderWithStore() {
    InMemorySessionStore<String> store = new InMemorySessionStore<>();

    SessionOptions<String> options = SessionOptions.<String>builder().store(store).build();

    assertSame(store, options.getStore());
  }

  @Test
  void testBuilderWithInitialState() {
    SessionOptions<String> options = SessionOptions.<String>builder().initialState("initial-value").build();

    assertEquals("initial-value", options.getInitialState());
  }

  @Test
  void testBuilderWithSessionId() {
    SessionOptions<String> options = SessionOptions.<String>builder().sessionId("my-session-123").build();

    assertEquals("my-session-123", options.getSessionId());
  }

  @Test
  void testBuilderWithAllOptions() {
    InMemorySessionStore<String> store = new InMemorySessionStore<>();

    SessionOptions<String> options = SessionOptions.<String>builder().store(store).initialState("test-state")
        .sessionId("session-456").build();

    assertSame(store, options.getStore());
    assertEquals("test-state", options.getInitialState());
    assertEquals("session-456", options.getSessionId());
  }

  @Test
  void testBuilderChaining() {
    SessionOptions.Builder<String> builder = SessionOptions.<String>builder();

    // Test that builder methods return the builder for chaining
    assertSame(builder, builder.store(new InMemorySessionStore<>()));
    assertSame(builder, builder.initialState("state"));
    assertSame(builder, builder.sessionId("id"));
  }

  @Test
  void testWithComplexState() {
    // Test with a custom state class
    TestState state = new TestState("Alice", 25);

    SessionOptions<TestState> options = SessionOptions.<TestState>builder().initialState(state)
        .sessionId("complex-state-session").build();

    assertEquals("Alice", options.getInitialState().getName());
    assertEquals(25, options.getInitialState().getAge());
  }

  /** Simple test state class. */
  static class TestState {
    private final String name;
    private final int age;

    TestState(String name, int age) {
      this.name = name;
      this.age = age;
    }

    String getName() {
      return name;
    }

    int getAge() {
      return age;
    }
  }
}
