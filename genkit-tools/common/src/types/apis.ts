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
  DatasetTypeSchema,
  EvalRunKeySchema,
  InferenceDatasetSchema,
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

export const TraceQueryFilterSchema = z.object({
  eq: z.record(z.string(), z.union([z.string(), z.number()])).optional(),
  neq: z.record(z.string(), z.union([z.string(), z.number()])).optional(),
});

export type TraceQueryFilter = z.infer<typeof TraceQueryFilterSchema>;

export const ListTracesRequestSchema = z.object({
  limit: z.number().optional(),
  continuationToken: z.string().optional(),
  filter: TraceQueryFilterSchema.optional(),
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
  context: z
    .any()
    .optional()
    .describe('Additional runtime context data (ex. auth context data).'),
  telemetryLabels: z
    .record(z.string(), z.string())
    .optional()
    .describe('Labels to be applied to telemetry data.'),
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

export const DeleteEvalRunRequestSchema = z.object({
  // Eval run name in the form evalRuns/{evalRunId}
  name: z.string(),
});
export type DeleteEvalRunRequest = z.infer<typeof DeleteEvalRunRequestSchema>;

export const CreateDatasetRequestSchema = z.object({
  data: InferenceDatasetSchema,
  datasetId: z.string().optional(),
  datasetType: DatasetTypeSchema,
  schema: DatasetSchemaSchema.optional(),
  metricRefs: z.array(z.string()).default([]),
  targetAction: z.string().optional(),
});

export type CreateDatasetRequest = z.infer<typeof CreateDatasetRequestSchema>;

export const UpdateDatasetRequestSchema = z.object({
  datasetId: z.string(),
  data: InferenceDatasetSchema.optional(),
  schema: DatasetSchemaSchema.optional(),
  // Set to undefined if no changes in `metricRefs`.
  metricRefs: z.array(z.string()).optional(),
  targetAction: z.string().optional(),
});
export type UpdateDatasetRequest = z.infer<typeof UpdateDatasetRequestSchema>;

export const RunNewEvaluationRequestSchema = z.object({
  dataSource: z.object({
    datasetId: z.string().optional(),
    data: InferenceDatasetSchema.optional(),
  }),
  actionRef: z.string(),
  evaluators: z.array(z.string()).optional(),
  options: z
    .object({
      context: z.string().optional(),
      actionConfig: z
        .any()
        .describe('addition parameters required for inference')
        .optional(),
      batchSize: z
        .number()
        .describe(
          'Batch the dataset into smaller segments that are run in parallel'
        )
        .optional(),
    })
    .optional(),
});
export type RunNewEvaluationRequest = z.infer<
  typeof RunNewEvaluationRequestSchema
>;

export const ValidateDataRequestSchema = z.object({
  dataSource: z.object({
    datasetId: z.string().optional(),
    data: InferenceDatasetSchema.optional(),
  }),
  actionRef: z.string(),
});
export type ValidateDataRequest = z.infer<typeof ValidateDataRequestSchema>;

export const ErrorDetailSchema = z.object({
  path: z.string(),
  message: z.string(),
});
export type ErrorDetail = z.infer<typeof ErrorDetailSchema>;

export const ValidateDataResponseSchema = z.object({
  valid: z.boolean(),
  errors: z
    .record(z.string(), z.array(ErrorDetailSchema))
    .describe(
      'Errors mapping, if any. The key is testCaseId if source is a dataset, otherewise it is the index number (stringified)'
    )
    .optional(),
});
export type ValidateDataResponse = z.infer<typeof ValidateDataResponseSchema>;
