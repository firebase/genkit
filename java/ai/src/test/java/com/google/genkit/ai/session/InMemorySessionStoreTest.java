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
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import com.google.genkit.ai.Message;

/** Unit tests for InMemorySessionStore. */
class InMemorySessionStoreTest {

  private InMemorySessionStore<String> store;

  @BeforeEach
  void setUp() {
    store = new InMemorySessionStore<>();
  }

  @Test
  void testSaveAndGet() throws ExecutionException, InterruptedException {
    SessionData<String> data = new SessionData<>("session-1", "test-state");
    data.setThread("main", List.of(Message.user("Hello")));

    store.save("session-1", data).get();

    SessionData<String> retrieved = store.get("session-1").get();

    assertNotNull(retrieved);
    assertEquals("session-1", retrieved.getId());
    assertEquals("test-state", retrieved.getState());
    assertEquals(1, retrieved.getThread("main").size());
  }

  @Test
  void testGetNonexistentSession() throws ExecutionException, InterruptedException {
    SessionData<String> result = store.get("nonexistent").get();

    assertNull(result);
  }

  @Test
  void testDelete() throws ExecutionException, InterruptedException {
    SessionData<String> data = new SessionData<>("to-delete", "state");
    store.save("to-delete", data).get();

    assertTrue(store.exists("to-delete").get());

    store.delete("to-delete").get();

    assertFalse(store.exists("to-delete").get());
    assertNull(store.get("to-delete").get());
  }

  @Test
  void testDeleteNonexistentSession() throws ExecutionException, InterruptedException {
    // Should not throw
    assertDoesNotThrow(() -> store.delete("nonexistent").get());
  }

  @Test
  void testExists() throws ExecutionException, InterruptedException {
    assertFalse(store.exists("new-session").get());

    store.save("new-session", new SessionData<>("new-session")).get();

    assertTrue(store.exists("new-session").get());
  }

  @Test
  void testSize() throws ExecutionException, InterruptedException {
    assertEquals(0, store.size());

    store.save("session-1", new SessionData<>("session-1")).get();
    assertEquals(1, store.size());

    store.save("session-2", new SessionData<>("session-2")).get();
    assertEquals(2, store.size());

    store.delete("session-1").get();
    assertEquals(1, store.size());
  }

  @Test
  void testClear() throws ExecutionException, InterruptedException {
    store.save("session-1", new SessionData<>("session-1")).get();
    store.save("session-2", new SessionData<>("session-2")).get();
    store.save("session-3", new SessionData<>("session-3")).get();

    assertEquals(3, store.size());

    store.clear();

    assertEquals(0, store.size());
    assertNull(store.get("session-1").get());
  }

  @Test
  void testOverwriteSession() throws ExecutionException, InterruptedException {
    SessionData<String> original = new SessionData<>("session", "original-state");
    store.save("session", original).get();

    SessionData<String> updated = new SessionData<>("session", "updated-state");
    store.save("session", updated).get();

    SessionData<String> retrieved = store.get("session").get();
    assertEquals("updated-state", retrieved.getState());
    assertEquals(1, store.size());
  }

  @Test
  void testMultipleSessions() throws ExecutionException, InterruptedException {
    for (int i = 0; i < 10; i++) {
      SessionData<String> data = new SessionData<>("session-" + i, "state-" + i);
      store.save("session-" + i, data).get();
    }

    assertEquals(10, store.size());

    for (int i = 0; i < 10; i++) {
      SessionData<String> retrieved = store.get("session-" + i).get();
      assertNotNull(retrieved);
      assertEquals("state-" + i, retrieved.getState());
    }
  }

  @Test
  void testWithComplexState() throws ExecutionException, InterruptedException {
    // Create a store with complex state type
    InMemorySessionStore<List<Integer>> complexStore = new InMemorySessionStore<>();

    List<Integer> state = new ArrayList<>();
    state.add(1);
    state.add(2);
    state.add(3);

    SessionData<List<Integer>> data = new SessionData<>("complex", state);
    complexStore.save("complex", data).get();

    SessionData<List<Integer>> retrieved = complexStore.get("complex").get();
    assertNotNull(retrieved);
    assertEquals(3, retrieved.getState().size());
    assertEquals(List.of(1, 2, 3), retrieved.getState());
  }

  @Test
  void testAsyncOperations() throws ExecutionException, InterruptedException {
    // Test that operations return proper CompletableFutures
    CompletableFuture<Void> saveFuture = store.save("async-session", new SessionData<>("async-session"));
    assertNotNull(saveFuture);
    saveFuture.get(); // Should complete without exception

    CompletableFuture<SessionData<String>> getFuture = store.get("async-session");
    assertNotNull(getFuture);
    SessionData<String> result = getFuture.get();
    assertNotNull(result);

    CompletableFuture<Boolean> existsFuture = store.exists("async-session");
    assertNotNull(existsFuture);
    assertTrue(existsFuture.get());

    CompletableFuture<Void> deleteFuture = store.delete("async-session");
    assertNotNull(deleteFuture);
    deleteFuture.get(); // Should complete without exception
  }

  @Test
  void testSessionDataWithThreads() throws ExecutionException, InterruptedException {
    SessionData<String> data = new SessionData<>("threaded-session", "state");

    List<Message> mainThread = new ArrayList<>();
    mainThread.add(Message.user("Hello"));
    mainThread.add(Message.model("Hi there!"));
    data.setThread("main", mainThread);

    List<Message> sideThread = new ArrayList<>();
    sideThread.add(Message.user("Different conversation"));
    data.setThread("side", sideThread);

    store.save("threaded-session", data).get();

    SessionData<String> retrieved = store.get("threaded-session").get();
    assertNotNull(retrieved);
    assertEquals(2, retrieved.getThread("main").size());
    assertEquals(1, retrieved.getThread("side").size());
    assertEquals("Hello", retrieved.getThread("main").get(0).getText());
  }
}
