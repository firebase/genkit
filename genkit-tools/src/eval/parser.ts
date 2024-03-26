/**
 * Copyright 2024 Google LLC
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
 */

import { EvalInput, EvalMetric, EvalResult } from '../eval';
import { EvaluatorResponse } from '../types/evaluators';

/**
 * Combines EvalInput with the generated scores to create a storable EvalResult.
 */
export function enrichResultsWithScoring(
  scores: Record<string, EvaluatorResponse>,
  evalDataset: EvalInput[]
): EvalResult[] {
  const scoreMap: Record<string, EvalMetric[]> = {};
  Object.keys(scores).forEach((evaluator) => {
    const evaluatorResponse = scores[evaluator];
    evaluatorResponse.forEach((scoredSample) => {
      if (!scoredSample.testCaseId) {
        throw new Error('testCaseId expected to be present');
      }
      const score = scoredSample.evaluation;
      if (!scoreMap[scoredSample.testCaseId]) {
        scoreMap[scoredSample.testCaseId] = [];
      }
      scoreMap[scoredSample.testCaseId].push({
        evaluator,
        score: score.score,
        rationale: score.details?.reasoning,
        error: score.error,
      });
    });
  });

  return evalDataset.map((evalResult) => {
    return {
      ...evalResult,
      metrics: scoreMap[evalResult.testCaseId] ?? [],
    };
  });
}
