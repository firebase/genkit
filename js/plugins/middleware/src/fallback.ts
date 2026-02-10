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
  ModelReferenceSchema,
  generateMiddleware,
  modelRef,
  z,
  type GenerateMiddleware,
  type ModelReference,
  type StatusName,
} from 'genkit';

const DEFAULT_FALLBACK_STATUSES: StatusName[] = [
  'UNAVAILABLE',
  'DEADLINE_EXCEEDED',
  'RESOURCE_EXHAUSTED',
  'ABORTED',
  'INTERNAL',
  'NOT_FOUND',
  'UNIMPLEMENTED',
];

export const FallbackOptionsSchema = z
  .object({
    /**
     * An array of models to try in order.
     */
    models: z.array(z.union([z.string(), ModelReferenceSchema])),
    /**
     * An array of `StatusName` values that should trigger a fallback.
     * @default ['UNAVAILABLE', 'DEADLINE_EXCEEDED', 'RESOURCE_EXHAUSTED', 'ABORTED', 'INTERNAL', 'NOT_FOUND', 'UNIMPLEMENTED']
     */
    statuses: z.array(z.string()).optional(),
  })
  .passthrough();

export interface FallbackOptions extends z.infer<typeof FallbackOptionsSchema> {
  /**
   * A callback to be executed on each fallback attempt.
   */
  onError?: (error: Error) => void;
}

/**
 * Creates a middleware that falls back to a different model on specific error statuses.
 *
 * ```ts
 * const { text } = await ai.generate({
 *   model: googleAI.model('gemini-2.5-pro'),
 *   prompt: 'You are a helpful AI assistant named Walt, say hello',
 *   use: [
 *     fallback({
 *       models: [googleAI.model('gemini-2.5-flash')],
 *       statuses: ['RESOURCE_EXHAUSTED'],
 *     }),
 *   ],
 * });
 * ```
 */
export const fallback: GenerateMiddleware<typeof FallbackOptionsSchema> =
  generateMiddleware(
    {
      name: 'fallback',
      configSchema: FallbackOptionsSchema,
    },
    (options?: FallbackOptions) => {
      const {
        models = [],
        statuses = DEFAULT_FALLBACK_STATUSES,
        onError,
      } = options || {};

      return {
        generate: async (req, ctx, next) => {
          try {
            return await next(req, ctx);
          } catch (e) {
            if (
              e instanceof GenkitError &&
              statuses.includes(e.status as StatusName)
            ) {
              onError?.(e);
              let lastError: any = e;
              for (const model of models) {
                const normalizedModel = normalizeModel(model);
                try {
                  return await next(
                    {
                      ...req,
                      model: normalizedModel.name,
                      config: normalizedModel.config ?? req.config,
                    },
                    ctx
                  );
                } catch (e2) {
                  lastError = e2;
                  if (
                    e2 instanceof GenkitError &&
                    statuses.includes(e2.status as StatusName)
                  ) {
                    onError?.(e2);
                    continue;
                  }
                  throw e2;
                }
              }
              throw lastError;
            }
            throw e;
          }
        },
      };
    }
  );

function normalizeModel(
  model: string | z.infer<typeof ModelReferenceSchema>
): ModelReference<any> {
  if (typeof model === 'string') {
    return modelRef({ name: model });
  }
  return modelRef({ name: model.name, config: model.config });
}
