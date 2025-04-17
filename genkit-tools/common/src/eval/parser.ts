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

import * as _ from 'lodash';
import { Action } from '../types/action';
import { EvalInput, EvalMetric, EvalResult } from '../types/eval';
import { EvalFnResponse, EvalResponse } from '../types/evaluator';
import {
  EVALUATOR_METADATA_KEY_DEFINITION,
  EVALUATOR_METADATA_KEY_DISPLAY_NAME,
} from '../utils/eval';

/** Maximum allowed unique strings / enums for generating summaries */
export const MAX_UNIQUE_STRING_DIST = 5;

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
          status: s.status,
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
      displayName: (action.metadata!.evaluator as any)[
        EVALUATOR_METADATA_KEY_DISPLAY_NAME
      ],
      definition: (action.metadata!.evaluator as any)[
        EVALUATOR_METADATA_KEY_DEFINITION
      ],
    };
  }
  return metadata;
}

export function extractMetricSummaries(
  /** key: evaluatorRef */
  scores: Record<string, EvalResponse>
) {
  // key: evaluatorRef or evaluatorRef + scoreId (if available)
  const testCaseCountMap: Record<string, number> = {};

  const entries = Object.entries(scores)
    .map(([evaluator, responseArray]) => {
      testCaseCountMap[evaluator] = responseArray.length;
      return {
        evaluator,
        score: responseArray.flatMap((response) =>
          Array.isArray(response.evaluation)
            ? response.evaluation
            : [response.evaluation]
        ),
      };
    })
    .flatMap((entry) => {
      const groupedScores = _.groupBy(entry.score, 'id');
      const groupedScoresKeys = Object.keys(groupedScores);

      if (
        groupedScoresKeys.length === 1 &&
        groupedScoresKeys[0] === 'undefined'
      ) {
        // No score-level granularity
        return _.flatMap(entry.score, (score) => ({
          evaluator: entry.evaluator,
          testCaseCount: testCaseCountMap[entry.evaluator] ?? 0,
          status: score.status,
          score: score.score,
          error: score.error,
        }));
      } else {
        return _.flatMap(groupedScores, (scores, scoreId) => {
          if (scoreId === 'undefined') {
            return scores.map((score) => ({
              evaluator: entry.evaluator,
              testCaseCount: testCaseCountMap[entry.evaluator] ?? 0,
              status: score.status,
              score: score.score,
              error: score.error,
            }));
          } else {
            // Duplicate tracking to simplify lookup.
            testCaseCountMap[entry.evaluator + '/' + scoreId] =
              testCaseCountMap[entry.evaluator] ?? 0;
            return scores.map((score) => ({
              // Synthetic ID to separate different scores
              evaluator: entry.evaluator + '/' + scoreId,
              testCaseCount: testCaseCountMap[entry.evaluator] ?? 0,
              status: score.status,
              score: score.score,
              error: score.error,
            }));
          }
        });
      }
    });

  const grouped = _.groupBy(entries, 'evaluator');

  const summaries = _.map(grouped, (items, evaluator) => {
    const definedItems = items.filter(
      (item) => typeof item.score !== 'undefined'
    );
    const scoreUndefinedCount = items.filter(
      (item) => typeof item.score === 'undefined'
    ).length;
    const errorCount = items.filter((item) => item.error !== undefined).length;
    const statusDistribution = _.countBy(items, 'status');

    if (definedItems.length > 0) {
      // At least one score be registered for this
      const validItem = definedItems[0];
      const scoreType = typeof validItem.score;
      if (scoreType === 'number') {
        return {
          evaluator,
          testCaseCount: validItem.testCaseCount,
          errorCount,
          scoreUndefinedCount,
          statusDistribution,
          averageScore: _.meanBy(definedItems, 'score'),
        };
      } else if (scoreType === 'boolean') {
        return {
          evaluator,
          testCaseCount: validItem.testCaseCount,
          errorCount,
          scoreUndefinedCount,
          statusDistribution,
          scoreDistribution: _.countBy(definedItems, 'score'),
        };
      } else if (scoreType === 'string') {
        // Treat as enum, but limit to 5 by heuristics
        const scoreDistribution = _.countBy(definedItems, 'score');

        if (Object.keys(scoreDistribution).length <= MAX_UNIQUE_STRING_DIST) {
          return {
            evaluator,
            testCaseCount: validItem.testCaseCount,
            errorCount,
            scoreUndefinedCount,
            scoreDistribution,
            statusDistribution,
          };
        }
      }
    }
    return {
      evaluator,
      testCaseCount: testCaseCountMap[evaluator] ?? 0,
      errorCount,
      scoreUndefinedCount,
      statusDistribution,
    };
  });

  return summaries;
}
