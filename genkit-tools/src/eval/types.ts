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

import { z } from 'zod';

/**
 * List request to fetch all EvalRunKeys from the EvalStore.
 */
export interface ListEvalKeysRequest {
  filter?: {
    actionId?: string;
  };
}

/**
 * List response of all relevant EvalRunKeys from the EvalStore.
 */
export interface ListEvalKeysResponse {
  results: EvalRunKey[];
}

/**
 * A unique identifier for an Evaluation Run.
 */
export const EvalRunKeySchema = z.object({
  actionId: z.string().optional(),
  evalRunId: z.string(),
  createdAt: z.string(),
});
export type EvalRunKey = z.infer<typeof EvalRunKeySchema>;

export const EvalMetricSchema = z.object({
  evaluator: z.string(),
  score: z.union([z.number(), z.string(), z.boolean()]).optional(),
  rationale: z.string().optional(),
  error: z.string().optional(),
  traceId: z.string().optional(),
  spanId: z.string().optional(),
});
export type EvalMetric = z.infer<typeof EvalMetricSchema>;

/**
 * Alias for evaluator score output.
 */
export type ScoreRecord = Record<
  string, // evaluator identifier
  ScoreValue[] // array of scores for this evaluator
>;

/**
 * Minimal interface of required fields from evaluator output.
 */
export interface ScoreValue {
  sample: { testCaseId: string };
  score: Record<string, number>;
}

/**
 * A record that is ready for evaluation.
 *
 * TODO: consider renaming.
 */
export const EvalInputSchema = z.object({
  testCaseId: z.string(),
  input: z.any(),
  output: z.any(),
  context: z.array(z.string()).optional(),
  groundTruth: z.any().optional(),
  traceIds: z.array(z.string()),
});
export type EvalInput = z.infer<typeof EvalInputSchema>;

/**
 * The scored result of an evaluation of an individual inference.
 */
export const EvalResultSchema = z.object({
  testCaseId: z.string(),
  input: z.any(),
  output: z.any(),
  context: z.array(z.string()).optional(),
  groundTruth: z.any().optional(),
  metrics: z.array(EvalMetricSchema).optional(),
  traceIds: z.array(z.string()),
});
export type EvalResult = z.infer<typeof EvalResultSchema>;

/**
 * A container for the results of evaluation over a batch of test cases.
 */
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
