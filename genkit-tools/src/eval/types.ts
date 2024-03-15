import { z } from 'zod';

export interface ListEvalKeysRequest {
  filter?: {
    actionId?: string;
  };
}

export interface ListEvalKeysResponse {
  results: EvalRunKey[];
}

export const EvalRunKeySchema = z.object({
  actionId: z.string().optional(),
  evalRunId: z.string(),
  createdAt: z.coerce.date(),
});
export type EvalRunKey = z.infer<typeof EvalRunKeySchema>;

export const EvalMetricSchema = z.object({
  evaluator: z.string(),
  score: z.union([z.number(), z.string(), z.boolean()]),
  rationale: z.string(),
});
export type EvalMetric = z.infer<typeof EvalMetricSchema>;

export const EvalResultSchema = z.object({
  input: z.any(),
  output: z.any(),
  context: z.array(z.string()).optional(),
  groundTruth: z.any().optional(),
  metrics: z.array(EvalMetricSchema).optional(),
  traceIds: z.array(z.string()),
});
export type EvalResult = z.infer<typeof EvalResultSchema>;

export const EvalRunSchema = z.object({
  key: EvalRunKeySchema,
  results: z.array(EvalResultSchema),
});
export type EvalRun = z.infer<typeof EvalRunSchema>;

/**
 * Eval dataset store persistence interface.
 */
export interface EvalStore {
  /**
   * Persist an EvalRun
   * @param evalRun the result of evaluating a collection of test cases.
   */
  save(evalRun: EvalRun): Promise<void>;

  /**
   * Load a single EvalRun from storage
   * @param evalRunId the ID of the EvalRun
   * @param actionId (optional) the ID of the action used to generate output.
   */
  load(evalRunId: string, actionId?: string): Promise<EvalRun | undefined>;

  /**
   * List the keys of all EvalRuns from storage
   * @param query (optional) filter criteria for the result list
   */
  list(query?: ListEvalKeysRequest): Promise<ListEvalKeysResponse>;
}
