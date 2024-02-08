import { z } from 'zod';
import { config } from "./config";
import * as registry from "./registry";

// NOTE: Keep this file in sync with genkit-tools/src/types/flow.ts!
// Eventually tools will be source of truth for these types (by generating a
// JSON schema) but until then this file must be manually kept in sync

export interface FlowStateQuery {
  limit?: number;
}

/**
 * Flow state store persistence interface.
 */
export interface FlowStateStore {
  save(id: string, state: FlowState): Promise<void>;
  load(id: string): Promise<FlowState | undefined>;
  list(query?: FlowStateQuery): Promise<FlowState[]>;
}

export const FlowStateExecutionSchema = z.object({
  startTime: z.number().optional(),
  endTime: z.number().optional(),
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
  startTime: z.number(),
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

let flowStateStore: FlowStateStore;

export function setGlobalFlowStateStore(store: FlowStateStore) {
  flowStateStore = store;
}

export function getGlobalFlowStateStore(): FlowStateStore {
  if (!flowStateStore) {
    throw new Error("setGlobalFlowStateStore has not been called, yet")
  }
  return flowStateStore;
}