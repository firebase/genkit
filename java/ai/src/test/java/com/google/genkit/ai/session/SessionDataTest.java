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

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

import com.google.genkit.ai.Message;

/** Unit tests for SessionData. */
class SessionDataTest {

  @Test
  void testDefaultConstructor() {
    SessionData<String> data = new SessionData<>();

    assertNull(data.getId());
    assertNull(data.getState());
    assertNotNull(data.getThreads());
    assertTrue(data.getThreads().isEmpty());
  }

  @Test
  void testConstructorWithId() {
    SessionData<String> data = new SessionData<>("test-session-123");

    assertEquals("test-session-123", data.getId());
    assertNull(data.getState());
    assertNotNull(data.getThreads());
    assertTrue(data.getThreads().isEmpty());
  }

  @Test
  void testConstructorWithIdAndState() {
    SessionData<String> data = new SessionData<>("test-session", "initial-state");

    assertEquals("test-session", data.getId());
    assertEquals("initial-state", data.getState());
    assertNotNull(data.getThreads());
    assertTrue(data.getThreads().isEmpty());
  }

  @Test
  void testSetAndGetId() {
    SessionData<String> data = new SessionData<>();
    data.setId("my-session-id");

    assertEquals("my-session-id", data.getId());
  }

  @Test
  void testSetAndGetState() {
    SessionData<Integer> data = new SessionData<>();
    data.setState(42);

    assertEquals(42, data.getState());
  }

  @Test
  void testSetAndGetThreads() {
    SessionData<String> data = new SessionData<>();

    Map<String, List<Message>> threads = new HashMap<>();
    List<Message> messages = new ArrayList<>();
    messages.add(Message.user("Hello"));
    threads.put("main", messages);

    data.setThreads(threads);

    assertEquals(1, data.getThreads().size());
    assertTrue(data.getThreads().containsKey("main"));
    assertEquals(1, data.getThreads().get("main").size());
  }

  @Test
  void testGetThread() {
    SessionData<String> data = new SessionData<>();

    List<Message> messages = new ArrayList<>();
    messages.add(Message.user("Test message"));
    data.setThread("test-thread", messages);

    List<Message> retrieved = data.getThread("test-thread");

    assertNotNull(retrieved);
    assertEquals(1, retrieved.size());
    assertEquals("Test message", retrieved.get(0).getText());
  }

  @Test
  void testGetThreadReturnsNullForNonexistent() {
    SessionData<String> data = new SessionData<>();

    assertNull(data.getThread("nonexistent"));
  }

  @Test
  void testGetOrCreateThread() {
    SessionData<String> data = new SessionData<>();

    // First call should create the thread
    List<Message> thread1 = data.getOrCreateThread("new-thread");
    assertNotNull(thread1);
    assertTrue(thread1.isEmpty());

    // Add a message
    thread1.add(Message.user("Hello"));

    // Second call should return the same thread
    List<Message> thread2 = data.getOrCreateThread("new-thread");
    assertEquals(1, thread2.size());
    assertEquals("Hello", thread2.get(0).getText());
  }

  @Test
  void testSetThread() {
    SessionData<String> data = new SessionData<>();

    List<Message> messages = new ArrayList<>();
    messages.add(Message.user("First"));
    messages.add(Message.model("Second"));

    data.setThread("conversation", messages);

    List<Message> retrieved = data.getThread("conversation");
    assertEquals(2, retrieved.size());
    assertEquals("First", retrieved.get(0).getText());
    assertEquals("Second", retrieved.get(1).getText());
  }

  @Test
  void testSetThreadCreatesDefensiveCopy() {
    SessionData<String> data = new SessionData<>();

    List<Message> messages = new ArrayList<>();
    messages.add(Message.user("Original"));
    data.setThread("thread", messages);

    // Modify original list
    messages.add(Message.model("Added after"));

    // The stored thread should not be affected
    List<Message> retrieved = data.getThread("thread");
    assertEquals(1, retrieved.size());
  }

  @Test
  void testBuilder() {
    SessionData<String> data = SessionData.<String>builder().id("builder-session").state("builder-state").build();

    assertEquals("builder-session", data.getId());
    assertEquals("builder-state", data.getState());
    assertNotNull(data.getThreads());
  }

  @Test
  void testBuilderWithThreads() {
    Map<String, List<Message>> threads = new HashMap<>();
    List<Message> mainThread = new ArrayList<>();
    mainThread.add(Message.user("Hello"));
    threads.put("main", mainThread);

    SessionData<String> data = SessionData.<String>builder().id("session").threads(threads).build();

    assertEquals(1, data.getThreads().size());
    assertTrue(data.getThreads().containsKey("main"));
  }

  @Test
  void testBuilderAddThread() {
    List<Message> messages = new ArrayList<>();
    messages.add(Message.system("System prompt"));

    SessionData<String> data = SessionData.<String>builder().id("session").thread("custom", messages).build();

    assertNotNull(data.getThread("custom"));
    assertEquals(1, data.getThread("custom").size());
  }

  @Test
  void testWithComplexState() {
    // Test with a complex state object
    Map<String, Object> complexState = new HashMap<>();
    complexState.put("userName", "Alice");
    complexState.put("preferences", Map.of("theme", "dark", "language", "en"));
    complexState.put("messageCount", 5);

    SessionData<Map<String, Object>> data = new SessionData<>("complex-session", complexState);

    assertEquals("complex-session", data.getId());
    assertEquals("Alice", data.getState().get("userName"));
    assertEquals(5, data.getState().get("messageCount"));
  }
}
