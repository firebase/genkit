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

/**
 * Unit tests for GenkitOptions.
 */
class GenkitOptionsTest {

  @Test
  void testDefaultBuilder() {
    GenkitOptions options = GenkitOptions.builder().build();

    assertNotNull(options);
    // Default values may depend on environment, so just check not null
    assertNotNull(options.getProjectRoot());
  }

  @Test
  void testDevMode() {
    GenkitOptions options = GenkitOptions.builder().devMode(true).build();

    assertTrue(options.isDevMode());

    options = GenkitOptions.builder().devMode(false).build();

    assertFalse(options.isDevMode());
  }

  @Test
  void testReflectionPort() {
    GenkitOptions options = GenkitOptions.builder().reflectionPort(5000).build();

    assertEquals(5000, options.getReflectionPort());
  }

  @Test
  void testProjectRoot() {
    GenkitOptions options = GenkitOptions.builder().projectRoot("/custom/project/root").build();

    assertEquals("/custom/project/root", options.getProjectRoot());
  }

  @Test
  void testPromptDir() {
    GenkitOptions options = GenkitOptions.builder().promptDir("/custom/prompts").build();

    assertEquals("/custom/prompts", options.getPromptDir());
  }

  @Test
  void testDefaultPromptDir() {
    GenkitOptions options = GenkitOptions.builder().build();

    assertEquals("/prompts", options.getPromptDir());
  }

  @Test
  void testBuilderChaining() {
    GenkitOptions options = GenkitOptions.builder().devMode(true).reflectionPort(4321).projectRoot("/my/project")
        .promptDir("/my/prompts").build();

    assertTrue(options.isDevMode());
    assertEquals(4321, options.getReflectionPort());
    assertEquals("/my/project", options.getProjectRoot());
    assertEquals("/my/prompts", options.getPromptDir());
  }

  @Test
  void testMultipleBuildCalls() {
    GenkitOptions.Builder builder = GenkitOptions.builder().devMode(true).reflectionPort(3000);

    GenkitOptions options1 = builder.build();
    GenkitOptions options2 = builder.build();

    // Both should have same values
    assertEquals(options1.isDevMode(), options2.isDevMode());
    assertEquals(options1.getReflectionPort(), options2.getReflectionPort());
  }

  @Test
  void testBuilderModificationAfterBuild() {
    GenkitOptions.Builder builder = GenkitOptions.builder().devMode(true);

    GenkitOptions options1 = builder.build();

    builder.devMode(false);
    GenkitOptions options2 = builder.build();

    // Options1 should not be affected
    assertTrue(options1.isDevMode());
    assertFalse(options2.isDevMode());
  }

  @Test
  void testDifferentPortValues() {
    for (int port : new int[]{0, 1, 1024, 3000, 8080, 65535}) {
      GenkitOptions options = GenkitOptions.builder().reflectionPort(port).build();

      assertEquals(port, options.getReflectionPort());
    }
  }

  @Test
  void testProjectRootVariations() {
    String[] paths = {"/", "/usr/local", "C:\\Users\\test", "relative/path", "./current", "../parent"};

    for (String path : paths) {
      GenkitOptions options = GenkitOptions.builder().projectRoot(path).build();

      assertEquals(path, options.getProjectRoot());
    }
  }
}
