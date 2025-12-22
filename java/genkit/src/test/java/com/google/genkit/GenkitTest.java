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

package com.google.genkit;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

import com.google.genkit.core.ActionContext;
import com.google.genkit.core.ActionType;
import com.google.genkit.core.Flow;

/**
 * Unit tests for Genkit.
 */
class GenkitTest {

  @Test
  void testDefaultConstructor() {
    Genkit genkit = new Genkit();
    assertNotNull(genkit);
  }

  @Test
  void testConstructorWithOptions() {
    GenkitOptions options = GenkitOptions.builder().devMode(false).reflectionPort(4000).build();

    Genkit genkit = new Genkit(options);
    assertNotNull(genkit);
  }

  @Test
  void testBuilder() {
    Genkit genkit = Genkit.builder().build();
    assertNotNull(genkit);
  }

  @Test
  void testDefineFlowWithBiFunction() {
    Genkit genkit = new Genkit();

    Flow<String, String, Void> flow = genkit.defineFlow("echoFlow", String.class, String.class,
        (ctx, input) -> "Echo: " + input);

    assertNotNull(flow);
    assertEquals("echoFlow", flow.getName());
    assertEquals(ActionType.FLOW, flow.getType());
  }

  @Test
  void testDefineFlowWithFunction() {
    Genkit genkit = new Genkit();

    Flow<String, Integer, Void> flow = genkit.defineFlow("lengthFlow", String.class, Integer.class, String::length);

    assertNotNull(flow);
    assertEquals("lengthFlow", flow.getName());
  }

  @Test
  void testFlowExecution() {
    Genkit genkit = new Genkit();

    Flow<String, String, Void> flow = genkit.defineFlow("upperCaseFlow", String.class, String.class,
        input -> input.toUpperCase());

    ActionContext ctx = new ActionContext(null, null, null);
    String result = flow.run(ctx, "hello");

    assertEquals("HELLO", result);
  }

  @Test
  void testMultipleFlows() {
    Genkit genkit = new Genkit();

    Flow<String, String, Void> flow1 = genkit.defineFlow("flow1", String.class, String.class, s -> s);
    Flow<Integer, String, Void> flow2 = genkit.defineFlow("flow2", Integer.class, String.class,
        i -> String.valueOf(i));

    assertNotNull(flow1);
    assertNotNull(flow2);
    assertEquals("flow1", flow1.getName());
    assertEquals("flow2", flow2.getName());
  }

  @Test
  void testFlowWithComplexInput() {
    Genkit genkit = new Genkit();

    Flow<TestInput, TestOutput, Void> flow = genkit.defineFlow("complexFlow", TestInput.class, TestOutput.class,
        input -> new TestOutput(input.getName(), input.getValue() * 2));

    assertNotNull(flow);

    ActionContext ctx = new ActionContext(null, null, null);
    TestOutput result = flow.run(ctx, new TestInput("test", 21));

    assertEquals("test", result.getName());
    assertEquals(42, result.getValue());
  }

  @Test
  void testGetRegistry() {
    Genkit genkit = new Genkit();
    assertNotNull(genkit.getRegistry());
  }

  /**
   * Test input class.
   */
  static class TestInput {
    private String name;
    private int value;

    public TestInput() {
    }

    public TestInput(String name, int value) {
      this.name = name;
      this.value = value;
    }

    public String getName() {
      return name;
    }

    public void setName(String name) {
      this.name = name;
    }

    public int getValue() {
      return value;
    }

    public void setValue(int value) {
      this.value = value;
    }
  }

  /**
   * Test output class.
   */
  static class TestOutput {
    private String name;
    private int value;

    public TestOutput() {
    }

    public TestOutput(String name, int value) {
      this.name = name;
      this.value = value;
    }

    public String getName() {
      return name;
    }

    public void setName(String name) {
      this.name = name;
    }

    public int getValue() {
      return value;
    }

    public void setValue(int value) {
      this.value = value;
    }
  }
}
