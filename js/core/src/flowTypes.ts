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

// NOTE: Keep this file in sync with genkit-tools/src/types/flow.ts!
// Eventually tools will be source of truth for these types (by generating a
// JSON schema) but until then this file must be manually kept in sync

export interface FlowStateQuery {
  limit?: number;
  continuationToken?: string;
}
export interface FlowStateQueryResponse {
  flowStates: FlowState[];
  continuationToken?: string;
}

/**
 * Flow state store persistence interface.
 */
export interface FlowStateStore {
  save(id: string, state: FlowState): Promise<void>;
  load(id: string): Promise<FlowState | undefined>;
  list(query?: FlowStateQuery): Promise<FlowStateQueryResponse>;
}

export const FlowStateExecutionSchema = z.object({
  startTime: z
    .number()
    .optional()
    .describe('start time in milliseconds since the epoch'),
  endTime: z
    .number()
    .optional()
    .describe('end time in milliseconds since the epoch'),
  traceIds: z.array(z.string()),
});

export type FlowStateExecution = z.infer<typeof FlowStateExecutionSchema>;

export const FlowResponseSchema = z.object({
  response: z.unknown().nullable(),
});

export const FlowErrorSchema = z.object({
  error: z.string().optional(),
  stacktrace: z.string().optional(),
});

export type FlowError = z.infer<typeof FlowErrorSchema>;

export const FlowResultSchema = FlowResponseSchema.and(FlowErrorSchema);

/**
 * Flow Operation, modelled after:
 * https://cloud.google.com/service-infrastructure/docs/service-management/reference/rpc/google.longrunning#google.longrunning.Operation
 */
export const OperationSchema = z.object({
  name: z
    .string()
    .describe(
      'server-assigned name, which is only unique within the same service that originally ' +
        'returns it.'
    ),
  metadata: z
    .any()
    .optional()
    .describe(
      'Service-specific metadata associated with the operation. It typically contains progress ' +
        'information and common metadata such as create time.'
    ),
  done: z
    .boolean()
    .optional()
    .default(false)
    .describe(
      'If the value is false, it means the operation is still in progress. If true, the ' +
        'operation is completed, and either error or response is available.'
    ),
  result: FlowResultSchema.optional(),
  blockedOnStep: z
    .object({
      name: z.string(),
      schema: z.string().optional(),
    })
    .optional(),
});

export type Operation = z.infer<typeof OperationSchema>;

/**
 * Defines the format for flow state. This is the format used for persisting the state in
 * the {@link FlowStateStore}.
 */
export const FlowStateSchema = z.object({
  name: z.string().optional(),
  flowId: z.string(),
  input: z.unknown(),
  startTime: z.number().describe('start time in milliseconds since the epoch'),
  cache: z.record(
    z.string(),
    z.object({
      value: z.any().optional(),
      empty: z.literal(true).optional(),
    })
  ),
  eventsTriggered: z.record(z.string(), z.any()),
  blockedOnStep: z
    .object({
      name: z.string(),
      schema: z.string().optional(),
    })
    .nullable(),
  operation: OperationSchema,
  traceContext: z.string().optional(),
  executions: z.array(FlowStateExecutionSchema),
});

export type FlowState = z.infer<typeof FlowStateSchema>;
