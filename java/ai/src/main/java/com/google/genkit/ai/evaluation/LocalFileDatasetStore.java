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
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.core.type.TypeReference;
import com.google.genkit.core.JsonUtils;

/**
 * File-based implementation of DatasetStore.
 * 
 * <p>
 * Stores datasets in the .genkit/datasets directory with:
 * <ul>
 * <li>index.json - metadata for all datasets</li>
 * <li>{datasetId}.json - actual dataset data</li>
 * </ul>
 */
public class LocalFileDatasetStore implements DatasetStore {

  private static final Logger logger = LoggerFactory.getLogger(LocalFileDatasetStore.class);

  private static final String GENKIT_DIR = ".genkit";
  private static final String DATASETS_DIR = "datasets";
  private static final String INDEX_FILE = "index.json";

  private static LocalFileDatasetStore instance;

  private final Path storeRoot;
  private final Path indexFile;
  private final Map<String, DatasetMetadata> indexCache;

  /**
   * Gets the singleton instance of the dataset store.
   *
   * @return the dataset store instance
   */
  public static synchronized LocalFileDatasetStore getInstance() {
    if (instance == null) {
      instance = new LocalFileDatasetStore();
    }
    return instance;
  }

  /**
   * Creates a new LocalFileDatasetStore using the default location.
   */
  public LocalFileDatasetStore() {
    this(Paths.get(System.getProperty("user.dir"), GENKIT_DIR, DATASETS_DIR));
  }

  /**
   * Creates a new LocalFileDatasetStore with a custom root path.
   *
   * @param storeRoot
   *            the root directory for storing datasets
   */
  public LocalFileDatasetStore(Path storeRoot) {
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
      logger.error("Failed to initialize dataset store", e);
      throw new RuntimeException("Failed to initialize dataset store", e);
    }
  }

  private void loadIndex() throws IOException {
    if (Files.exists(indexFile)) {
      String content = Files.readString(indexFile);
      Map<String, DatasetMetadata> index = JsonUtils.getObjectMapper().readValue(content,
          new TypeReference<Map<String, DatasetMetadata>>() {
          });
      indexCache.clear();
      indexCache.putAll(index);
    }
  }

  private void saveIndex(Map<String, DatasetMetadata> index) throws IOException {
    String json = JsonUtils.toJson(index);
    Files.writeString(indexFile, json);
  }

  private Path getDatasetFile(String datasetId) {
    return storeRoot.resolve(datasetId + ".json");
  }

  private String generateDatasetId() {
    return "dataset_" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
  }

  @Override
  public DatasetMetadata createDataset(CreateDatasetRequest request) throws Exception {
    String datasetId = request.getDatasetId();
    if (datasetId == null || datasetId.isEmpty()) {
      datasetId = generateDatasetId();
    }

    if (indexCache.containsKey(datasetId)) {
      throw new IllegalArgumentException("Dataset already exists: " + datasetId);
    }

    List<DatasetSample> data = request.getData();
    if (data == null) {
      data = new ArrayList<>();
    }

    // Ensure all samples have testCaseIds
    for (int i = 0; i < data.size(); i++) {
      DatasetSample sample = data.get(i);
      if (sample.getTestCaseId() == null || sample.getTestCaseId().isEmpty()) {
        sample.setTestCaseId("test_case_" + (i + 1));
      }
    }

    String now = Instant.now().toString();
    DatasetMetadata metadata = DatasetMetadata.builder().datasetId(datasetId).size(data.size())
        .schema(request.getSchema())
        .datasetType(request.getDatasetType() != null ? request.getDatasetType() : DatasetType.UNKNOWN)
        .targetAction(request.getTargetAction())
        .metricRefs(request.getMetricRefs() != null ? request.getMetricRefs() : new ArrayList<>()).version(1)
        .createTime(now).updateTime(now).build();

    // Save the dataset data
    String dataJson = JsonUtils.toJson(data);
    Files.writeString(getDatasetFile(datasetId), dataJson);

    // Update the index
    indexCache.put(datasetId, metadata);
    saveIndex(indexCache);

    logger.info("Created dataset: {} with {} samples", datasetId, data.size());
    return metadata;
  }

  @Override
  public DatasetMetadata updateDataset(UpdateDatasetRequest request) throws Exception {
    String datasetId = request.getDatasetId();
    if (datasetId == null || datasetId.isEmpty()) {
      throw new IllegalArgumentException("Dataset ID is required");
    }

    DatasetMetadata existing = indexCache.get(datasetId);
    if (existing == null) {
      throw new IllegalArgumentException("Dataset not found: " + datasetId);
    }

    List<DatasetSample> data = request.getData();
    int size = existing.getSize();

    if (data != null) {
      // Ensure all samples have testCaseIds
      for (int i = 0; i < data.size(); i++) {
        DatasetSample sample = data.get(i);
        if (sample.getTestCaseId() == null || sample.getTestCaseId().isEmpty()) {
          sample.setTestCaseId("test_case_" + (i + 1));
        }
      }
      size = data.size();

      // Save the updated dataset data
      String dataJson = JsonUtils.toJson(data);
      Files.writeString(getDatasetFile(datasetId), dataJson);
    }

    String now = Instant.now().toString();
    DatasetMetadata updated = DatasetMetadata.builder().datasetId(datasetId).size(size)
        .schema(request.getSchema() != null ? request.getSchema() : existing.getSchema())
        .datasetType(existing.getDatasetType())
        .targetAction(
            request.getTargetAction() != null ? request.getTargetAction() : existing.getTargetAction())
        .metricRefs(request.getMetricRefs() != null ? request.getMetricRefs() : existing.getMetricRefs())
        .version(existing.getVersion() + 1).createTime(existing.getCreateTime()).updateTime(now).build();

    // Update the index
    indexCache.put(datasetId, updated);
    saveIndex(indexCache);

    logger.info("Updated dataset: {} (version {})", datasetId, updated.getVersion());
    return updated;
  }

  @Override
  public List<DatasetSample> getDataset(String datasetId) throws Exception {
    if (!indexCache.containsKey(datasetId)) {
      throw new IllegalArgumentException("Dataset not found: " + datasetId);
    }

    Path datasetFile = getDatasetFile(datasetId);
    if (!Files.exists(datasetFile)) {
      throw new IllegalArgumentException("Dataset data file not found: " + datasetId);
    }

    String content = Files.readString(datasetFile);
    return JsonUtils.getObjectMapper().readValue(content, new TypeReference<List<DatasetSample>>() {
    });
  }

  @Override
  public List<DatasetMetadata> listDatasets() throws Exception {
    // Reload index to get latest data
    loadIndex();
    return new ArrayList<>(indexCache.values());
  }

  @Override
  public void deleteDataset(String datasetId) throws Exception {
    if (!indexCache.containsKey(datasetId)) {
      throw new IllegalArgumentException("Dataset not found: " + datasetId);
    }

    // Delete the data file
    Path datasetFile = getDatasetFile(datasetId);
    Files.deleteIfExists(datasetFile);

    // Update the index
    indexCache.remove(datasetId);
    saveIndex(indexCache);

    logger.info("Deleted dataset: {}", datasetId);
  }
}
