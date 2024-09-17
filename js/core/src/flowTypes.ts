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
 * Used for flow control.
 */
export const FlowInvokeEnvelopeMessageSchema = z.object({
  // Start new flow.
  start: z.object({
    input: z.unknown().optional(),
    labels: z.record(z.string(), z.string()).optional(),
  }),
});

export type FlowInvokeEnvelopeMessage = z.infer<
  typeof FlowInvokeEnvelopeMessageSchema
>;

/**
 * Used by the flow action.
 */
export const FlowActionInputSchema = FlowInvokeEnvelopeMessageSchema.extend({
  auth: z.unknown().optional(),
});

export type FlowActionInput = z.infer<typeof FlowActionInputSchema>;
