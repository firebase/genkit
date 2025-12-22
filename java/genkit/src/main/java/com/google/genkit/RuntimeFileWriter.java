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

import java.io.IOException;
import java.nio.file.*;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * RuntimeFileWriter writes runtime discovery files for the Genkit Dev UI.
 *
 * The Dev UI discovers running Genkit instances by looking for JSON files in
 * the .genkit/runtimes directory.
 */
public class RuntimeFileWriter {

  private static final Logger logger = LoggerFactory.getLogger(RuntimeFileWriter.class);
  private static final ObjectMapper objectMapper = new ObjectMapper();
  private static Path currentRuntimeFile;

  /**
   * Writes a runtime file for Dev UI discovery. Uses findProjectRoot() to locate
   * the project root by searching up for pom.xml.
   *
   * @param port
   *            the reflection server port
   * @param runtimeId
   *            the runtime ID from the reflection server
   */
  public static void write(int port, String runtimeId) {
    String projectRoot = findProjectRoot();
    writeRuntimeFile(port, projectRoot, runtimeId);
  }

  /**
   * Finds the project root by searching up from the current directory.
   * Prioritizes package.json to match the genkit CLI's behavior - this ensures
   * the Java runtime writes to the same .genkit directory the CLI reads from.
   * Falls back to pom.xml/build.gradle only if no package.json is found.
   *
   * @return the project root directory path
   */
  private static String findProjectRoot() {
    Path dir = Paths.get(System.getProperty("user.dir")).toAbsolutePath();

    // First pass: Look for package.json (CLI primary marker) to ensure we match CLI
    // behavior
    // The CLI looks for package.json first, so we need to find the same root it
    // uses
    Path cliRoot = null;
    Path currentDir = dir;
    while (currentDir != null) {
      Path packageJson = currentDir.resolve("package.json");
      if (Files.exists(packageJson)) {
        cliRoot = currentDir;
        logger.debug("Found CLI project root at: {} (found package.json)", currentDir);
        break;
      }
      Path parent = currentDir.getParent();
      if (parent == null || parent.equals(currentDir)) {
        break;
      }
      currentDir = parent;
    }

    // If we found a package.json (CLI root), use that
    if (cliRoot != null) {
      return cliRoot.toString();
    }

    // Second pass: Fall back to Java/other markers if no package.json found
    String[] fallbackMarkers = {"pom.xml", "build.gradle", "go.mod", "pyproject.toml", "requirements.txt"};
    currentDir = dir;
    while (currentDir != null) {
      for (String marker : fallbackMarkers) {
        Path markerFile = currentDir.resolve(marker);
        if (Files.exists(markerFile)) {
          logger.debug("Found project root at: {} (found {})", currentDir, marker);
          return currentDir.toString();
        }
      }

      Path parent = currentDir.getParent();
      if (parent == null || parent.equals(currentDir)) {
        logger.warn("Could not find project root, using current directory");
        return System.getProperty("user.dir");
      }
      currentDir = parent;
    }

    return System.getProperty("user.dir");
  }

  /**
   * Writes a runtime file for Dev UI discovery.
   *
   * @param port
   *            the reflection server port
   * @param projectRoot
   *            the project root directory
   * @param runtimeId
   *            the runtime ID
   */
  public static void writeRuntimeFile(int port, String projectRoot, String runtimeId) {
    try {
      Path runtimesDir = getRuntimesDir(projectRoot);
      Files.createDirectories(runtimesDir);

      Path runtimeFile = runtimesDir.resolve(runtimeId + ".json");

      // Use ISO 8601 format like Go does: 2025-12-21T16:12:32Z
      // Replace colons with underscores for filename compatibility
      String timestamp = Instant.now().atOffset(ZoneOffset.UTC).format(DateTimeFormatter.ISO_INSTANT).replace(":",
          "_");

      Map<String, Object> runtimeInfo = new HashMap<>();
      runtimeInfo.put("id", runtimeId);
      runtimeInfo.put("pid", ProcessHandle.current().pid());
      runtimeInfo.put("reflectionServerUrl", "http://localhost:" + port);
      runtimeInfo.put("timestamp", timestamp);
      runtimeInfo.put("genkitVersion", "java/1.0.0");
      runtimeInfo.put("reflectionApiSpecVersion", 1);

      String json = objectMapper.writeValueAsString(runtimeInfo);
      Files.writeString(runtimeFile, json);
      currentRuntimeFile = runtimeFile;

      logger.info("Runtime file written: {}", runtimeFile);
    } catch (IOException e) {
      logger.error("Failed to write runtime file", e);
    }
  }

  /**
   * Cleans up the runtime file using the current directory as project root.
   */
  public static void cleanup() {
    if (currentRuntimeFile != null) {
      try {
        Files.deleteIfExists(currentRuntimeFile);
        logger.info("Runtime file removed: {}", currentRuntimeFile);
        currentRuntimeFile = null;
      } catch (IOException e) {
        logger.error("Failed to remove runtime file", e);
      }
    } else {
      removeRuntimeFile(System.getProperty("user.dir"));
    }
  }

  /**
   * Removes the runtime file.
   *
   * @param projectRoot
   *            the project root directory
   */
  public static void removeRuntimeFile(String projectRoot) {
    try {
      Path runtimesDir = getRuntimesDir(projectRoot);
      long pid = ProcessHandle.current().pid();

      // Find and delete files matching our PID
      if (Files.exists(runtimesDir)) {
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(runtimesDir, "*.json")) {
          for (Path file : stream) {
            try {
              String content = Files.readString(file);
              Map<String, Object> info = objectMapper.readValue(content, Map.class);
              if (info.get("pid") != null && ((Number) info.get("pid")).longValue() == pid) {
                Files.delete(file);
                logger.info("Runtime file removed: {}", file);
              }
            } catch (Exception e) {
              // Ignore files we can't read
            }
          }
        }
      }
    } catch (IOException e) {
      logger.error("Failed to remove runtime file", e);
    }
  }

  /**
   * Gets the runtimes directory path.
   */
  private static Path getRuntimesDir(String projectRoot) {
    return Paths.get(projectRoot, ".genkit", "runtimes");
  }
}
