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
import { EvalRunKeySchema } from '../eval/types';
import { EnvTypesSchema } from './apis';

export const ListEvalKeysRequestSchema = z.object({
  env: EnvTypesSchema.optional(),
  filter: z
    .object({
      actionId: z.string().optional(),
    })
    .optional(),
  // TODO: Add support for limit and continuation token
});

export type ListEvalKeysRequest = z.infer<typeof ListEvalKeysRequestSchema>;

export const ListEvalKeysResponseSchema = z.object({
  evalRunKeys: z.array(EvalRunKeySchema),
  // TODO: Add support continuation token
});

export type ListEvalKeysResponse = z.infer<typeof ListEvalKeysResponseSchema>;

export const GetEvalRunRequestSchema = z.object({
  env: EnvTypesSchema.optional(),
  // Eval run name in the form actions/{action}/evalRun/{evalRun}
  // where `action` can be blank e.g. actions/-/evalRun/{evalRun}
  name: z.string(),
});

export type GetEvalRunRequest = z.infer<typeof GetEvalRunRequestSchema>;
