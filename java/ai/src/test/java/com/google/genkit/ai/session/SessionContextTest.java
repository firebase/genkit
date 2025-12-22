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
import static org.mockito.Mockito.*;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import com.google.genkit.core.Registry;

/**
 * Unit tests for SessionContext.
 */
class SessionContextTest {

  private Registry mockRegistry;
  private InMemorySessionStore<String> store;

  @BeforeEach
  void setUp() {
    // Ensure clean state before each test
    SessionContext.clearSession();
    mockRegistry = mock(Registry.class);
    store = new InMemorySessionStore<>();
  }

  @AfterEach
  void tearDown() {
    // Clean up after each test
    SessionContext.clearSession();
  }

  /**
   * Helper to create a test session.
   */
  private Session<String> createTestSession(String id) {
    SessionData<String> sessionData = new SessionData<>(id, "test-state");
    return new Session<String>(mockRegistry, store, sessionData, () -> null, // We don't need actual chat for
        // context
        // tests
        null // No agent registry needed for these tests
    );
  }

  @Test
  void testCurrentSessionThrowsWhenNotSet() {
    assertThrows(SessionContext.SessionException.class, () -> SessionContext.currentSession());
  }

  @Test
  void testGetCurrentSessionReturnsNullWhenNotSet() {
    assertNull(SessionContext.getCurrentSession());
  }

  @Test
  void testHasSessionReturnsFalseWhenNotSet() {
    assertFalse(SessionContext.hasSession());
  }

  @Test
  void testSetAndGetSession() {
    Session<String> session = createTestSession("test-id");

    SessionContext.setSession(session);

    assertTrue(SessionContext.hasSession());
    assertSame(session, SessionContext.currentSession());
    assertSame(session, SessionContext.getCurrentSession());

    SessionContext.clearSession();
  }

  @Test
  void testRunWithSession() throws Exception {
    Session<String> session = createTestSession("test-session-id");

    AtomicReference<Session<?>> capturedSession = new AtomicReference<>();

    String result = SessionContext.runWithSession(session, () -> {
      capturedSession.set(SessionContext.currentSession());
      return "test-result";
    });

    assertEquals("test-result", result);
    assertSame(session, capturedSession.get());
    // Session should be cleared after runWithSession
    assertFalse(SessionContext.hasSession());
  }

  @Test
  void testRunWithSessionRestoresPreviousSession() throws Exception {
    Session<String> outerSession = createTestSession("outer");
    Session<String> innerSession = createTestSession("inner");

    SessionContext.setSession(outerSession);

    String result = SessionContext.runWithSession(innerSession, () -> {
      assertSame(innerSession, SessionContext.currentSession());
      return "done";
    });

    // Outer session should be restored
    assertSame(outerSession, SessionContext.currentSession());

    SessionContext.clearSession();
  }

  @Test
  void testRunWithSessionHandlesException() {
    Session<String> session = createTestSession("error-session");

    assertThrows(RuntimeException.class, () -> {
      SessionContext.runWithSession(session, () -> {
        throw new RuntimeException("Test exception");
      });
    });

    // Session should be cleared even after exception
    assertFalse(SessionContext.hasSession());
  }

  @Test
  void testThreadIsolation() throws InterruptedException {
    CountDownLatch latch = new CountDownLatch(2);
    AtomicReference<String> thread1SessionId = new AtomicReference<>();
    AtomicReference<String> thread2SessionId = new AtomicReference<>();

    Session<String> session1 = createTestSession("session-1");
    Session<String> session2 = createTestSession("session-2");

    ExecutorService executor = Executors.newFixedThreadPool(2);

    executor.submit(() -> {
      SessionContext.setSession(session1);
      try {
        Thread.sleep(50); // Allow time for overlap
      } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
      }
      thread1SessionId.set(SessionContext.<String>currentSession().getId());
      latch.countDown();
    });

    executor.submit(() -> {
      SessionContext.setSession(session2);
      try {
        Thread.sleep(50); // Allow time for overlap
      } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
      }
      thread2SessionId.set(SessionContext.<String>currentSession().getId());
      latch.countDown();
    });

    assertTrue(latch.await(1, TimeUnit.SECONDS));
    executor.shutdown();

    // Each thread should have its own session
    assertEquals("session-1", thread1SessionId.get());
    assertEquals("session-2", thread2SessionId.get());
  }

  @Test
  void testClearSession() {
    Session<String> session = createTestSession("clear-test");

    SessionContext.setSession(session);
    assertTrue(SessionContext.hasSession());

    SessionContext.clearSession();
    assertFalse(SessionContext.hasSession());
  }

  @Test
  void testNestedRunWithSession() throws Exception {
    Session<String> session1 = createTestSession("session-1");
    Session<String> session2 = createTestSession("session-2");
    Session<String> session3 = createTestSession("session-3");

    AtomicReference<String> level1 = new AtomicReference<>();
    AtomicReference<String> level2 = new AtomicReference<>();
    AtomicReference<String> level3 = new AtomicReference<>();
    AtomicReference<String> afterLevel2 = new AtomicReference<>();

    SessionContext.runWithSession(session1, () -> {
      level1.set(SessionContext.<String>currentSession().getId());

      SessionContext.runWithSession(session2, () -> {
        level2.set(SessionContext.<String>currentSession().getId());

        SessionContext.runWithSession(session3, () -> {
          level3.set(SessionContext.<String>currentSession().getId());
          return null;
        });

        afterLevel2.set(SessionContext.<String>currentSession().getId());
        return null;
      });

      return null;
    });

    assertEquals("session-1", level1.get());
    assertEquals("session-2", level2.get());
    assertEquals("session-3", level3.get());
    assertEquals("session-2", afterLevel2.get());
  }

  @Test
  void testRunWithSessionWithNullSession() throws Exception {
    String result = SessionContext.runWithSession(null, () -> {
      assertFalse(SessionContext.hasSession());
      return "result";
    });

    assertEquals("result", result);
  }
}
