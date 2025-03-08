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

import { Action } from '../types/action';
import { EvalInput, EvalMetric, EvalResult } from '../types/eval';
import { EvalFnResponse, EvalResponse } from '../types/evaluator';
import {
  EVALUATOR_METADATA_KEY_DEFINITION,
  EVALUATOR_METADATA_KEY_DISPLAY_NAME,
} from '../utils/eval';

/**
 * Combines EvalInput with the generated scores to create a storable EvalResult.
 */
export function enrichResultsWithScoring(
  scores: Record<string, EvalResponse>,
  evalDataset: EvalInput[]
): EvalResult[] {
  const scoreMap: Record<string, EvalMetric[]> = {};
  Object.keys(scores).forEach((evaluator) => {
    const evaluatorResponse = scores[evaluator];
    evaluatorResponse.forEach((scoredSample: EvalFnResponse) => {
      if (!scoredSample.testCaseId) {
        throw new Error('testCaseId expected to be present');
      }
      const score = Array.isArray(scoredSample.evaluation)
        ? scoredSample.evaluation
        : [scoredSample.evaluation];
      const existingScores = scoreMap[scoredSample.testCaseId] ?? [];
      const newScores = existingScores.concat(
        score.map((s) => ({
          evaluator,
          score: s.score,
          scoreId: s.id,
          rationale: s.details?.reasoning,
          error: s.error,
          traceId: scoredSample.traceId,
          spanId: scoredSample.spanId,
        }))
      );
      scoreMap[scoredSample.testCaseId] = newScores;
    });
  });

  return evalDataset.map((evalResult) => {
    return {
      ...evalResult,
      metrics: scoreMap[evalResult.testCaseId] ?? [],
    };
  });
}

export function extractMetricsMetadata(evaluatorActions: Action[]) {
  const metadata: Record<string, any> = {};
  for (const action of evaluatorActions) {
    metadata[action.name] = {
      displayName: action.metadata![EVALUATOR_METADATA_KEY_DISPLAY_NAME],
      definition: action.metadata![EVALUATOR_METADATA_KEY_DEFINITION],
    };
  }
  return metadata;
}
