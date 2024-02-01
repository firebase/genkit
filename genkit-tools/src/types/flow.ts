import * as z from 'zod';

/**
 * The message format used by the flow task queue and control interface.
 */
export const FlowInvokeEnvelopeMessageSchema = z.object({
  input: z.unknown().optional(),
  flowId: z.string().optional(),
  resume: z
    .object({
      payload: z.unknown(),
    })
    .optional(),
});
export type FlowInvokeEnvelopeMessage = z.infer<
  typeof FlowInvokeEnvelopeMessageSchema
>;

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
        'returns it.',
    ),
  metadata: z
    .unknown()
    .optional()
    .describe(
      'Service-specific metadata associated with the operation. It typically contains progress ' +
        'information and common metadata such as create time.',
    ),
  done: z
    .boolean()
    .optional()
    .default(false)
    .describe(
      'If the value is false, it means the operation is still in progress. If true, the ' +
        'operation is completed, and either error or response is available.',
    ),
  result: FlowResultSchema.optional(),
});

export type Operation = z.infer<typeof OperationSchema>;

/**
 * Defines the format for flow state. This is the format used for persisting the state in
 * the Flow state store.
 */
export const FlowStateSchema = z.object({
  name: z.string().optional(),
  flowId: z.string(),
  input: z.unknown(),
  startTime: z.number(),
  cache: z.record(
    z.string(),
    z.object({
      value: z.unknown().optional(),
      empty: z.literal(true).optional(),
    }),
  ),
  eventsTriggered: z.record(z.string(), z.unknown()),
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
