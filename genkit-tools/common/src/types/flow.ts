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

import { extendZodWithOpenApi } from '@asteasolutions/zod-to-openapi';
import * as z from 'zod';

extendZodWithOpenApi(z);

// NOTE: Keep this file in sync with genkit/flow/src/types.ts!
// Eventually tools will be source of truth for these types (by generating a
// JSON schema) but until then this file must be manually kept in sync

/**
 * The message format used by the flow task queue and control interface.
 */
export const FlowInvokeEnvelopeMessageSchema = z.object({
  // Start new flow.
  start: z
    .object({
      input: z.unknown().optional(),
      labels: z.record(z.string(), z.string()).optional(),
    })
    .optional(),
  // Schedule new flow.
  schedule: z
    .object({
      input: z.unknown().optional(),
      delay: z.number().optional(),
    })
    .optional(),
  // Run previously scheduled flow.
  runScheduled: z
    .object({
      flowId: z.string(),
    })
    .optional(),
  // Retry failed step (only if step is setup for retry)
  retry: z
    .object({
      flowId: z.string(),
    })
    .optional(),
  // Resume an interrupted flow.
  resume: z
    .object({
      flowId: z.string(),
      payload: z.unknown().optional(),
    })
    .optional(),
  // State check for a given flow ID. No side effects, can be used to check flow state.
  state: z
    .object({
      flowId: z.string(),
    })
    .optional(),
});
export type FlowInvokeEnvelopeMessage = z.infer<
  typeof FlowInvokeEnvelopeMessageSchema
>;

export const FlowActionInputSchema = FlowInvokeEnvelopeMessageSchema.extend({
  auth: z.unknown().optional(),
});

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
