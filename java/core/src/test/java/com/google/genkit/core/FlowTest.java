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
 * Unit tests for Flow.
 */
class FlowTest {

  private Registry registry;

  @BeforeEach
  void setUp() {
    registry = new DefaultRegistry();
  }

  @Test
  void testDefineFlow() {
    Flow<String, String, Void> flow = Flow.define(registry, "echoFlow", String.class, String.class,
        (ctx, input) -> "Echo: " + input);

    assertNotNull(flow);
    assertEquals("echoFlow", flow.getName());
    assertEquals(ActionType.FLOW, flow.getType());
  }

  @Test
  void testFlowIsRegistered() {
    Flow<String, String, Void> flow = Flow.define(registry, "testFlow", String.class, String.class,
        (ctx, input) -> input.toUpperCase());

    String key = ActionType.FLOW.keyFromName("testFlow");
    Action<?, ?, ?> registered = registry.lookupAction(key);

    assertNotNull(registered);
    // The registered action is the internal ActionDef, not the Flow wrapper
    assertNotNull(registered.getDesc());
  }

  @Test
  void testFlowRun() {
    Flow<String, String, Void> flow = Flow.define(registry, "transformFlow", String.class, String.class,
        (ctx, input) -> input.toLowerCase());

    ActionContext ctx = new ActionContext(registry);
    String result = flow.run(ctx, "HELLO WORLD");

    assertEquals("hello world", result);
  }

  @Test
  void testFlowWithContext() {
    Flow<String, String, Void> flow = Flow.define(registry, "contextFlow", String.class, String.class,
        (ctx, input) -> {
          // Flow should set the flow name in context
          assertEquals("contextFlow", ctx.getFlowName());
          return input;
        });

    ActionContext ctx = new ActionContext(registry);
    flow.run(ctx, "test");
  }

  @Test
  void testFlowDesc() {
    Flow<String, Integer, Void> flow = Flow.define(registry, "countFlow", String.class, Integer.class,
        (ctx, input) -> input.length());

    ActionDesc desc = flow.getDesc();

    assertNotNull(desc);
    assertEquals("countFlow", desc.getName());
  }

  @Test
  void testDefineStreamingFlow() {
    Flow<String, String, String> flow = Flow.defineStreaming(registry, "streamingFlow", String.class, String.class,
        (ctx, input, cb) -> {
          if (cb != null) {
            cb.accept("chunk1");
            cb.accept("chunk2");
          }
          return "final result";
        });

    assertNotNull(flow);
    assertEquals("streamingFlow", flow.getName());
    assertEquals(ActionType.FLOW, flow.getType());
  }

  @Test
  void testStreamingFlowWithCallback() {
    StringBuilder chunks = new StringBuilder();

    Flow<String, String, String> flow = Flow.defineStreaming(registry, "chunkingFlow", String.class, String.class,
        (ctx, input, cb) -> {
          String[] words = input.split(" ");
          for (String word : words) {
            if (cb != null) {
              cb.accept(word);
            }
          }
          return input;
        });

    ActionContext ctx = new ActionContext(registry);
    java.util.function.Consumer<String> streamCallback = chunks::append;
    String result = flow.run(ctx, "hello world", streamCallback);

    assertEquals("hello world", result);
    assertEquals("helloworld", chunks.toString());
  }

  @Test
  void testFlowRunThrowsGenkitException() {
    Flow<String, String, Void> flow = Flow.define(registry, "errorFlow", String.class, String.class,
        (ctx, input) -> {
          throw new GenkitException("Intentional error");
        });

    ActionContext ctx = new ActionContext(registry);

    assertThrows(GenkitException.class, () -> flow.run(ctx, "test"));
  }

  @Test
  void testMultipleFlowsInRegistry() {
    Flow.define(registry, "flow1", String.class, String.class, (ctx, input) -> input);
    Flow.define(registry, "flow2", String.class, Integer.class, (ctx, input) -> input.length());
    Flow.define(registry, "flow3", Integer.class, String.class, (ctx, input) -> String.valueOf(input));

    assertNotNull(registry.lookupAction(ActionType.FLOW.keyFromName("flow1")));
    assertNotNull(registry.lookupAction(ActionType.FLOW.keyFromName("flow2")));
    assertNotNull(registry.lookupAction(ActionType.FLOW.keyFromName("flow3")));
  }

  @Test
  void testFlowStepRunOutsideFlowThrowsException() {
    ActionContext ctx = new ActionContext(registry);

    // Flow.run (step) should throw when not called from within a flow
    java.util.function.Function<Void, String> stepFn = (v) -> "result";
    assertThrows(GenkitException.class, () -> Flow.run(ctx, "stepName", stepFn));
  }
}
