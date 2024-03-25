export const EVALUATOR_ACTION_PREFIX = '/evaluator';

export function stripEvaluatorNamePrefix(name: string) {
  return name.substring(EVALUATOR_ACTION_PREFIX.length + 1);
}
