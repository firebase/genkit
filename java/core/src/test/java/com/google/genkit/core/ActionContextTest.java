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

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Unit tests for ActionContext.
 */
class ActionContextTest {

  private Registry registry;

  @BeforeEach
  void setUp() {
    registry = new DefaultRegistry();
  }

  @Test
  void testConstructorWithAllParameters() {
    String flowName = "testFlow";
    String spanPath = "/flow/testFlow";
    String sessionId = "session123";
    String threadName = "thread1";

    ActionContext context = new ActionContext(null, flowName, spanPath, registry, sessionId, threadName);

    assertNull(context.getSpanContext());
    assertEquals(flowName, context.getFlowName());
    assertEquals(spanPath, context.getSpanPath());
    assertEquals(registry, context.getRegistry());
    assertEquals(sessionId, context.getSessionId());
    assertEquals(threadName, context.getThreadName());
  }

  @Test
  void testConstructorWithFourParameters() {
    String flowName = "testFlow";
    String spanPath = "/flow/testFlow";

    ActionContext context = new ActionContext(null, flowName, spanPath, registry);

    assertNull(context.getSpanContext());
    assertEquals(flowName, context.getFlowName());
    assertEquals(spanPath, context.getSpanPath());
    assertEquals(registry, context.getRegistry());
    assertNull(context.getSessionId());
    assertNull(context.getThreadName());
  }

  @Test
  void testConstructorWithThreeParameters() {
    String flowName = "testFlow";

    ActionContext context = new ActionContext(null, flowName, registry);

    assertNull(context.getSpanContext());
    assertEquals(flowName, context.getFlowName());
    assertNull(context.getSpanPath());
    assertEquals(registry, context.getRegistry());
  }

  @Test
  void testConstructorWithRegistryOnly() {
    ActionContext context = new ActionContext(registry);

    assertNull(context.getSpanContext());
    assertNull(context.getFlowName());
    assertNull(context.getSpanPath());
    assertEquals(registry, context.getRegistry());
    assertNull(context.getSessionId());
    assertNull(context.getThreadName());
  }

  @Test
  void testWithFlowName() {
    ActionContext context = new ActionContext(registry);
    String newFlowName = "newFlow";

    ActionContext newContext = context.withFlowName(newFlowName);

    assertEquals(newFlowName, newContext.getFlowName());
    assertEquals(registry, newContext.getRegistry());
  }

  @Test
  void testWithSpanPath() {
    ActionContext context = new ActionContext(registry);
    String newSpanPath = "/flow/test/step1";

    ActionContext newContext = context.withSpanPath(newSpanPath);

    assertEquals(newSpanPath, newContext.getSpanPath());
    assertEquals(registry, newContext.getRegistry());
  }

  @Test
  void testWithSessionId() {
    ActionContext context = new ActionContext(registry);
    String sessionId = "session456";

    ActionContext newContext = context.withSessionId(sessionId);

    assertEquals(sessionId, newContext.getSessionId());
    assertEquals(registry, newContext.getRegistry());
  }

  @Test
  void testWithThreadName() {
    ActionContext context = new ActionContext(registry);
    String threadName = "worker-thread";

    ActionContext newContext = context.withThreadName(threadName);

    assertEquals(threadName, newContext.getThreadName());
    assertEquals(registry, newContext.getRegistry());
  }

  @Test
  void testContextImmutability() {
    ActionContext original = new ActionContext(null, "flow1", "/path", registry, "session1", "thread1");

    ActionContext modified = original.withFlowName("flow2");

    // Original should be unchanged
    assertEquals("flow1", original.getFlowName());
    assertEquals("flow2", modified.getFlowName());
  }

  @Test
  void testChainedWith() {
    ActionContext context = new ActionContext(registry).withFlowName("myFlow").withSpanPath("/flow/myFlow")
        .withSessionId("session789").withThreadName("main-thread");

    assertEquals("myFlow", context.getFlowName());
    assertEquals("/flow/myFlow", context.getSpanPath());
    assertEquals("session789", context.getSessionId());
    assertEquals("main-thread", context.getThreadName());
  }

  @Test
  void testNullSpanContext() {
    ActionContext context = new ActionContext(null, "testFlow", registry);

    assertNull(context.getSpanContext());
    assertEquals("testFlow", context.getFlowName());
  }
}
