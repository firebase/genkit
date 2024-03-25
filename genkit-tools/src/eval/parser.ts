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
