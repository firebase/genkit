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

/**
 * Functional interface for evaluator functions.
 * 
 * <p>
 * An evaluator function takes a data point and optional options, and returns an
 * evaluation response containing scores.
 *
 * @param <O>
 *            the type of evaluator-specific options
 */
@FunctionalInterface
public interface EvaluatorFn<O> {

  /**
   * Evaluates a single data point.
   *
   * @param dataPoint
   *            the data point to evaluate
   * @param options
   *            optional evaluator-specific options
   * @return the evaluation response
   * @throws Exception
   *             if evaluation fails
   */
  EvalResponse evaluate(EvalDataPoint dataPoint, O options) throws Exception;
}
