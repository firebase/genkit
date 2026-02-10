/**
 * Copyright 2026 Google LLC
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

import {
  GenkitError,
  generateMiddleware,
  z,
  type GenerateMiddleware,
  type StatusName,
} from 'genkit';

export const RetryOptionsSchema = z
  .object({
    /**
     * The maximum number of times to retry a failed request.
     * @default 3
     */
    maxRetries: z.number().optional(),
    /**
     * An array of `StatusName` values that should trigger a retry.
     * @default ['UNAVAILABLE', 'DEADLINE_EXCEEDED', 'RESOURCE_EXHAUSTED', 'ABORTED', 'INTERNAL']
     */
    statuses: z.array(z.string()).optional(),
    /**
     * The initial delay between retries, in milliseconds.
     * @default 1000
     */
    initialDelayMs: z.number().optional(),
    /**
     * The maximum delay between retries, in milliseconds.
     * @default 60000
     */
    maxDelayMs: z.number().optional(),
    /**
     * The factor by which the delay increases after each retry (exponential backoff).
     * @default 2
     */
    backoffFactor: z.number().optional(),
    /**
     * Whether to disable jitter on the delay. Jitter adds a random factor to the
     * delay to help prevent a "thundering herd" of clients all retrying at the
     * same time.
     * @default false
     */
    noJitter: z.boolean().optional(),
  })
  .passthrough();

export interface RetryOptions extends z.infer<typeof RetryOptionsSchema> {
  /**
   * A callback to be executed on each retry attempt.
   */
  onError?: (error: Error, attempt: number) => void;
}

const DEFAULT_RETRY_STATUSES: StatusName[] = [
  'UNAVAILABLE',
  'DEADLINE_EXCEEDED',
  'RESOURCE_EXHAUSTED',
  'ABORTED',
  'INTERNAL',
];

let __setTimeout: (
  callback: (...args: any[]) => void,
  ms?: number
) => NodeJS.Timeout = setTimeout;

/**
 * FOR TESTING ONLY.
 * @internal
 */
export const TEST_ONLY = {
  setRetryTimeout(
    impl: (callback: (...args: any[]) => void, ms?: number) => NodeJS.Timeout
  ) {
    __setTimeout = impl;
  },
};

/**
 * Creates a middleware that retries requests on specific error statuses.
 *
 * ```ts
 * const { text } = await ai.generate({
 *   model: googleAI.model('gemini-2.5-pro'),
 *   prompt: 'You are a helpful AI assistant named Walt, say hello',
 *   use: [
 *     retry({
 *       maxRetries: 2,
 *       initialDelayMs: 1000,
 *       backoffFactor: 2,
 *     }),
 *   ],
 * });
 * ```
 */
export const retry: GenerateMiddleware<typeof RetryOptionsSchema> =
  generateMiddleware(
    {
      name: 'retry',
      configSchema: RetryOptionsSchema,
    },
    (options?: RetryOptions) => {
      const {
        maxRetries = 3,
        statuses = DEFAULT_RETRY_STATUSES,
        initialDelayMs = 1000,
        maxDelayMs = 60000,
        backoffFactor = 2,
        noJitter = false,
        onError,
      } = options || {};

      return {
        model: async (req, ctx, next) => {
          let lastError: any;
          let currentDelay = initialDelayMs;
          for (let i = 0; i <= maxRetries; i++) {
            try {
              return await next(req, ctx);
            } catch (e) {
              lastError = e;
              const error = e as Error;
              if (i < maxRetries) {
                let shouldRetry = false;
                if (error instanceof GenkitError) {
                  if ((statuses as string[]).includes(error.status)) {
                    shouldRetry = true;
                  }
                } else {
                  shouldRetry = true;
                }

                if (shouldRetry) {
                  onError?.(error, i + 1);
                  let delay = currentDelay;
                  if (!noJitter) {
                    delay = delay + 1000 * Math.pow(2, i) * Math.random();
                  }
                  await new Promise((resolve) => __setTimeout(resolve, delay));
                  currentDelay = Math.min(
                    currentDelay * backoffFactor,
                    maxDelayMs
                  );
                  continue;
                }
              }
              throw error;
            }
          }
          throw lastError;
        },
      };
    }
  );
