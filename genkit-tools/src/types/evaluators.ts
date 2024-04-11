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

export const ScoreSchema = z.object({
  score: z.number().optional(),
  // TODO: use StatusSchema
  error: z.string().optional(),
  details: z
    .object({
      reasoning: z.string().optional(),
    })
    .passthrough()
    .optional(),
});

export const TestCaseSchema = z.object({
  sampleIndex: z.number(),
  testCaseId: z.string().optional(),
  traceId: z.string().optional(),
  spanId: z.string().optional(),
  evaluation: ScoreSchema,
});
export type TestCase = z.infer<typeof TestCaseSchema>;

export const EvalResponseSchema = z.array(TestCaseSchema);
export type EvalResponse = z.infer<typeof EvalResponseSchema>;
