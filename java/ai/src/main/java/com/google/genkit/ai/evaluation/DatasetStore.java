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

import java.util.List;

/**
 * Interface for dataset storage operations.
 * 
 * <p>
 * Implementations of this interface handle CRUD operations for datasets used in
 * evaluation workflows.
 */
public interface DatasetStore {

  /**
   * Creates a new dataset.
   *
   * @param request
   *            the create request containing dataset data and metadata
   * @return metadata about the created dataset
   * @throws Exception
   *             if creation fails
   */
  DatasetMetadata createDataset(CreateDatasetRequest request) throws Exception;

  /**
   * Updates an existing dataset.
   *
   * @param request
   *            the update request containing dataset ID and new data
   * @return metadata about the updated dataset
   * @throws Exception
   *             if update fails or dataset not found
   */
  DatasetMetadata updateDataset(UpdateDatasetRequest request) throws Exception;

  /**
   * Gets the data for a dataset.
   *
   * @param datasetId
   *            the dataset ID
   * @return the list of dataset samples
   * @throws Exception
   *             if retrieval fails or dataset not found
   */
  List<DatasetSample> getDataset(String datasetId) throws Exception;

  /**
   * Lists all datasets.
   *
   * @return list of dataset metadata
   * @throws Exception
   *             if listing fails
   */
  List<DatasetMetadata> listDatasets() throws Exception;

  /**
   * Deletes a dataset.
   *
   * @param datasetId
   *            the dataset ID to delete
   * @throws Exception
   *             if deletion fails
   */
  void deleteDataset(String datasetId) throws Exception;
}
