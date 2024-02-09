import { z } from 'zod';

/**
 * This file contains API schemas that are shared between Tools API and Reflection API.
 * It's used directly in the generation of the Reflection API OpenAPI spec.
 */

export const EnvTypesSchema = z
  .enum(['dev', 'prod'])
  .describe('Supported environments in the runtime.');

export type EnvTypes = z.infer<typeof EnvTypesSchema>;

export const ListTracesRequestSchema = z.object({ env: EnvTypesSchema });

export type ListTracesRequest = z.infer<typeof ListTracesRequestSchema>;

export const GetTraceRequestSchema = z.object({
  env: EnvTypesSchema,
  traceId: z.string().describe('ID of the trace.'),
});

export type GetTraceRequest = z.infer<typeof GetTraceRequestSchema>;

export const ListFlowStatesRequestSchema = z.object({ env: EnvTypesSchema });

export type ListFlowStatesRequest = z.infer<typeof ListFlowStatesRequestSchema>;

export const GetFlowStateRequestSchema = z.object({
  env: EnvTypesSchema,
  flowId: z.string().describe('ID of the flow state.'),
});

export type GetFlowStateRequest = z.infer<typeof GetFlowStateRequestSchema>;

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

// TODO: Add return types if deemed necessary.
