import { EvalInput, EvalResult, EvalMetric, ScoreRecord } from '../eval';

/**
 * Combines EvalInput with the generated scores to create a storable EvalResult.
 */
export function enrichResultsWithScoring(
  scores: ScoreRecord,
  evalDataset: EvalInput[]
): EvalResult[] {
  const scoreMap: Map<string, EvalMetric[]> = new Map();
  Object.keys(scores).forEach((evaluator) => {
    const scoreArr = scores[evaluator];
    scoreArr.forEach((scoredSample) => {
      // TODO: Output the raw score from the evaluator so we don't have to do this.
      // There shouldn't be multiple values because we map this by evaluator.
      const score = Object.values(scoredSample.score)[0];
      if (scoreMap.has(scoredSample.sample.testCaseId)) {
        scoreMap
          .get(scoredSample.sample.testCaseId)
          ?.push({ evaluator, score });
      } else {
        scoreMap.set(scoredSample.sample.testCaseId, [{ evaluator, score }]);
      }
    });
  });

  return evalDataset.map((evalResult) => {
    return {
      ...evalResult,
      metrics: scoreMap.has(evalResult.testCaseId)
        ? scoreMap.get(evalResult.testCaseId)
        : [],
    };
  });
}
