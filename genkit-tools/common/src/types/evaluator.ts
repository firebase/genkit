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

/**
 * This file defines schema and types that are used by Genkit evaluators.
 *
 * NOTE: Keep this file in sync with genkit/ai/src/evaluator.ts!
 * Eventually tools will be source of truth for these types (by generating a
 * JSON schema) but until then this file must be manually kept in sync
 */
import { z } from 'zod';

//
// IMPORTANT: Keep this file in sync with genkit/ai/src/evaluator.ts!
//

/**
 * Zod schema for a data point for evaluation
 */
export const BaseDataPointSchema = z.object({
  input: z.unknown(),
  output: z.unknown().optional(),
  context: z.array(z.unknown()).optional(),
  reference: z.unknown().optional(),
  testCaseId: z.string().optional(),
  traceIds: z.array(z.string()).optional(),
});
export type BaseDataPoint = z.infer<typeof BaseDataPointSchema>;

// DataPoint that is to be used for actions. This needs testCaseId to be
// present.
export const BaseEvalDataPointSchema = BaseDataPointSchema.extend({
  testCaseId: z.string(),
});
export type BaseEvalDataPoint = z.infer<typeof BaseEvalDataPointSchema>;
// Enum for Score Status
export const EvalStatusEnumSchema = z.enum(['UNKNOWN', 'PASS', 'FAIL']);
/**
 * Zod schema for evaluation score
 */
export const ScoreSchema = z.object({
  id: z
    .string()
    .describe('Optional ID to differentiate different scores')
    .optional(),
  score: z.union([z.number(), z.string(), z.boolean()]).optional(),
  status: EvalStatusEnumSchema.optional(),
  error: z.string().optional(),
  details: z
    .object({
      reasoning: z.string().optional(),
    })
    .passthrough()
    .optional(),
});
export type Score = z.infer<typeof ScoreSchema>;

/**
 * Zod schema for an evaluator action request.
 */
export const EvalRequestSchema = z.object({
  dataset: z.array(BaseDataPointSchema),
  evalRunId: z.string(),
  options: z.unknown(),
});
export type EvalRequest = z.infer<typeof EvalRequestSchema>;

/**
 * Zod schema for single response from evaluator function.
 *
 * Disclaimer, this schema is defined as `EvalResponseSchema` in
 * genkit/js/ai/evaluator.ts. That is a misnomer and this is only the response
 * from the user-provided callback function, we rename this accordingly here.
 */
export const EvalFnResponseSchema = z.object({
  sampleIndex: z.number().optional(),
  testCaseId: z.string(),
  traceId: z.string().optional(),
  spanId: z.string().optional(),
  evaluation: z.union([ScoreSchema, z.array(ScoreSchema)]),
});
export type EvalFnResponse = z.infer<typeof EvalFnResponseSchema>;

/**
 * Zod schema for batch evaluator responses, typically used as the evaluator
 * response for a dataset.
 *
 * Disclaimer, this schema is defined as `EvalResponsesSchema` in
 * genkit/js/ai/evaluator.ts. That is not an ideal name to differentiate from
 * `EvalResponseSchema`, so we rename this to EvalResponse, given that the
 * former now has a new name in this package.
 */
export const EvalResponseSchema = z.array(EvalFnResponseSchema);
export type EvalResponse = z.infer<typeof EvalResponseSchema>;
