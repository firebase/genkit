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
 * Interface for storing and retrieving evaluation runs.
 */
public interface EvalStore {

  /**
   * Saves an evaluation run.
   *
   * @param evalRun
   *            the evaluation run to save
   * @throws Exception
   *             if save fails
   */
  void save(EvalRun evalRun) throws Exception;

  /**
   * Loads an evaluation run by ID.
   *
   * @param evalRunId
   *            the evaluation run ID
   * @return the evaluation run, or null if not found
   * @throws Exception
   *             if load fails
   */
  EvalRun load(String evalRunId) throws Exception;

  /**
   * Lists all evaluation run keys.
   *
   * @return list of evaluation run keys
   * @throws Exception
   *             if listing fails
   */
  List<EvalRunKey> list() throws Exception;

  /**
   * Lists evaluation run keys with optional filtering.
   *
   * @param actionRef
   *            filter by action reference
   * @param datasetId
   *            filter by dataset ID
   * @return filtered list of evaluation run keys
   * @throws Exception
   *             if listing fails
   */
  List<EvalRunKey> list(String actionRef, String datasetId) throws Exception;

  /**
   * Deletes an evaluation run.
   *
   * @param evalRunId
   *            the evaluation run ID to delete
   * @throws Exception
   *             if deletion fails
   */
  void delete(String evalRunId) throws Exception;
}
