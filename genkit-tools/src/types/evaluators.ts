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

export const EvaluatorResponseSchema = z.array(
  z.object({
    sampleIndex: z.number(),
    testCaseId: z.string().optional(),
    evaluation: ScoreSchema,
  })
);

export type EvaluatorResponse = z.infer<typeof EvaluatorResponseSchema>;
