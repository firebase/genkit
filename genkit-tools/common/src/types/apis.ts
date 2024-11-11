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
import {
  DatasetSchemaSchema,
  EvalInferenceInputSchema,
  EvalRunKeySchema,
} from './eval';
import {
  GenerationCommonConfigSchema,
  MessageSchema,
  ToolDefinitionSchema,
} from './model';
import { TraceDataSchema } from './trace';

/**
 * This file contains API schemas that are shared between Tools API and Reflection API.
 * It's used directly in the generation of the Reflection API OpenAPI spec.
 */

export const ListTracesRequestSchema = z.object({
  limit: z.number().optional(),
  continuationToken: z.string().optional(),
});

export type ListTracesRequest = z.infer<typeof ListTracesRequestSchema>;

export const ListTracesResponseSchema = z.object({
  traces: z.array(TraceDataSchema),
  continuationToken: z.string().optional(),
});

export type ListTracesResponse = z.infer<typeof ListTracesResponseSchema>;

export const GetTraceRequestSchema = z.object({
  traceId: z.string().describe('ID of the trace.'),
});

export type GetTraceRequest = z.infer<typeof GetTraceRequestSchema>;

export const RunActionRequestSchema = z.object({
  key: z
    .string()
    .describe('Action key that consists of the action type and ID.'),
  input: z
    .any()
    .optional()
    .describe('An input with the type that this action expects.'),
});

export type RunActionRequest = z.infer<typeof RunActionRequestSchema>;

export const CreatePromptRequestSchema = z.object({
  model: z.string(),
  messages: z.array(MessageSchema),
  config: GenerationCommonConfigSchema.passthrough().optional(),
  tools: z.array(ToolDefinitionSchema).optional(),
});

export type CreatePromptRequest = z.infer<typeof CreatePromptRequestSchema>;

export const PageViewSchema = z.object({
  pageTitle: z.string().describe('Page that was viewed by the user.'),
});

export type PageView = z.infer<typeof PageViewSchema>;

// TODO: Add return types if deemed necessary.

export const ListEvalKeysRequestSchema = z.object({
  filter: z
    .object({
      actionRef: z.string().optional(),
    })
    .optional(),
});

export type ListEvalKeysRequest = z.infer<typeof ListEvalKeysRequestSchema>;

export const ListEvalKeysResponseSchema = z.object({
  evalRunKeys: z.array(EvalRunKeySchema),
  // TODO: Add support continuation token
});
export type ListEvalKeysResponse = z.infer<typeof ListEvalKeysResponseSchema>;

export const GetEvalRunRequestSchema = z.object({
  // Eval run name in the form evalRuns/{evalRunId}
  name: z.string(),
});
export type GetEvalRunRequest = z.infer<typeof GetEvalRunRequestSchema>;

export const CreateDatasetRequestSchema = z.object({
  data: EvalInferenceInputSchema,
  datasetId: z.string().optional(),
  schema: DatasetSchemaSchema.optional(),
  targetAction: z.string().optional(),
});

export type CreateDatasetRequest = z.infer<typeof CreateDatasetRequestSchema>;

export const UpdateDatasetRequestSchema = z.object({
  datasetId: z.string(),
  data: EvalInferenceInputSchema.optional(),
  schema: DatasetSchemaSchema.optional(),
  targetAction: z.string().optional(),
});
export type UpdateDatasetRequest = z.infer<typeof UpdateDatasetRequestSchema>;

export const RunNewEvaluationRequestSchema = z.object({
  datasetId: z.string(),
  actionRef: z.string(),
  evaluators: z.array(z.string()).optional(),
  options: z
    .object({
      auth: z.string().optional(),
      actionConfig: z
        .any()
        .describe('addition parameters required for inference')
        .optional(),
    })
    .optional(),
});
export type RunNewEvaluationRequest = z.infer<
  typeof RunNewEvaluationRequestSchema
>;
