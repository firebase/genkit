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

package com.google.genkit.ai.evaluation;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.core.type.TypeReference;
import com.google.genkit.core.JsonUtils;

/**
 * File-based implementation of EvalStore.
 * 
 * <p>
 * Stores evaluation runs in the .genkit/evals directory with:
 * <ul>
 * <li>index.json - metadata for all eval runs</li>
 * <li>{evalRunId}.json - actual eval run data</li>
 * </ul>
 */
public class LocalFileEvalStore implements EvalStore {

  private static final Logger logger = LoggerFactory.getLogger(LocalFileEvalStore.class);

  private static final String GENKIT_DIR = ".genkit";
  private static final String EVALS_DIR = "evals";
  private static final String INDEX_FILE = "index.json";

  private static LocalFileEvalStore instance;

  private final Path storeRoot;
  private final Path indexFile;
  private final Map<String, EvalRunKey> indexCache;

  /**
   * Gets the singleton instance of the eval store.
   *
   * @return the eval store instance
   */
  public static synchronized LocalFileEvalStore getInstance() {
    if (instance == null) {
      instance = new LocalFileEvalStore();
    }
    return instance;
  }

  /**
   * Creates a new LocalFileEvalStore using the default location.
   */
  public LocalFileEvalStore() {
    this(Paths.get(System.getProperty("user.dir"), GENKIT_DIR, EVALS_DIR));
  }

  /**
   * Creates a new LocalFileEvalStore with a custom root path.
   *
   * @param storeRoot
   *            the root directory for storing eval runs
   */
  public LocalFileEvalStore(Path storeRoot) {
    this.storeRoot = storeRoot;
    this.indexFile = storeRoot.resolve(INDEX_FILE);
    this.indexCache = new ConcurrentHashMap<>();
    initializeStore();
  }

  private void initializeStore() {
    try {
      Files.createDirectories(storeRoot);
      if (!Files.exists(indexFile)) {
        saveIndex(new HashMap<>());
      }
      loadIndex();
    } catch (IOException e) {
      logger.error("Failed to initialize eval store", e);
      throw new RuntimeException("Failed to initialize eval store", e);
    }
  }

  private void loadIndex() throws IOException {
    if (Files.exists(indexFile)) {
      String content = Files.readString(indexFile);
      Map<String, EvalRunKey> index = JsonUtils.getObjectMapper().readValue(content,
          new TypeReference<Map<String, EvalRunKey>>() {
          });
      indexCache.clear();
      indexCache.putAll(index);
    }
  }

  private void saveIndex(Map<String, EvalRunKey> index) throws IOException {
    String json = JsonUtils.toJson(index);
    Files.writeString(indexFile, json);
  }

  private Path getEvalRunFile(String evalRunId) {
    return storeRoot.resolve(evalRunId + ".json");
  }

  @Override
  public void save(EvalRun evalRun) throws Exception {
    if (evalRun.getKey() == null || evalRun.getKey().getEvalRunId() == null) {
      throw new IllegalArgumentException("EvalRun must have a key with evalRunId");
    }

    String evalRunId = evalRun.getKey().getEvalRunId();

    // Save the eval run data
    String dataJson = JsonUtils.toJson(evalRun);
    Files.writeString(getEvalRunFile(evalRunId), dataJson);

    // Update the index
    indexCache.put(evalRunId, evalRun.getKey());
    saveIndex(indexCache);

    logger.info("Saved eval run: {}", evalRunId);
  }

  @Override
  public EvalRun load(String evalRunId) throws Exception {
    Path evalRunFile = getEvalRunFile(evalRunId);
    if (!Files.exists(evalRunFile)) {
      return null;
    }

    String content = Files.readString(evalRunFile);
    return JsonUtils.fromJson(content, EvalRun.class);
  }

  @Override
  public List<EvalRunKey> list() throws Exception {
    return list(null, null);
  }

  @Override
  public List<EvalRunKey> list(String actionRef, String datasetId) throws Exception {
    // Reload index to get latest data
    loadIndex();

    return indexCache.values().stream().filter(key -> {
      if (actionRef != null && !actionRef.equals(key.getActionRef())) {
        return false;
      }
      if (datasetId != null && !datasetId.equals(key.getDatasetId())) {
        return false;
      }
      return true;
    }).sorted((a, b) -> {
      // Sort by createdAt descending
      if (a.getCreatedAt() == null)
        return 1;
      if (b.getCreatedAt() == null)
        return -1;
      return b.getCreatedAt().compareTo(a.getCreatedAt());
    }).collect(Collectors.toList());
  }

  @Override
  public void delete(String evalRunId) throws Exception {
    // Delete the data file
    Path evalRunFile = getEvalRunFile(evalRunId);
    Files.deleteIfExists(evalRunFile);

    // Update the index
    indexCache.remove(evalRunId);
    saveIndex(indexCache);

    logger.info("Deleted eval run: {}", evalRunId);
  }
}
