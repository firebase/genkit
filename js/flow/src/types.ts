import { z } from 'zod';
import { Flow } from './flow';
import { Operation } from '@google-genkit/common';
import { StreamingCallback } from '@google-genkit/common';

export type Invoker<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
> = (
  flow: Flow<I, O, S>,
  msg: FlowInvokeEnvelopeMessage,
  streamingCallback?: StreamingCallback<any>
) => Promise<Operation>;

export type Scheduler<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
> = (
  flow: Flow<I, O, S>,
  msg: FlowInvokeEnvelopeMessage,
  delaySeconds?: number
) => Promise<void>;

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

/**
 * Retry options for flows and steps.
 */
export interface RetryConfig {
  /**
   * Maximum number of times a request should be attempted.
   * If left unspecified, will default to 3.
   */
  maxAttempts?: number;
  /**
   * Maximum amount of time for retrying failed task.
   * If left unspecified will retry indefinitely.
   */
  maxRetrySeconds?: number;
  /**
   * The maximum amount of time to wait between attempts.
   * If left unspecified will default to 1hr.
   */
  maxBackoffSeconds?: number;
  /**
   * The maximum number of times to double the backoff between
   * retries. If left unspecified will default to 16.
   */
  maxDoublings?: number;
  /**
   * The minimum time to wait between attempts. If left unspecified
   * will default to 100ms.
   */
  minBackoffSeconds?: number;
}
