import { z } from 'zod';
import { FlowRunner } from './runner';

export interface WorkflowDispatcher<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny
> {
  dispatch(
    flow: FlowRunner<I, O>,
    msg: FlowInvokeEnvelopeMessage
  ): Promise<void>;
}

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
