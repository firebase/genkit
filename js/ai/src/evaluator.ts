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

import { action, Action } from '@genkit-ai/core';
import * as registry from '@genkit-ai/core/registry';
import { lookupAction } from '@genkit-ai/core/registry';
import { setCustomMetadataAttributes } from '@genkit-ai/core/tracing';
import * as z from 'zod';

export const BaseDataPointSchema = z.object({
  input: z.unknown(),
  output: z.unknown().optional(),
  context: z.array(z.unknown()).optional(),
  testCaseId: z.string().optional(),
});

export const ScoreSchema = z.object({
  score: z.number().optional(),
  // TODO: use StatusSchema
  error: z.string().optional(),
  details: z
    .object({
      reasoning: z.string().optional(),
    })
    .passthrough()
    .optional(),
});

export type Score = z.infer<typeof ScoreSchema>;

export type Dataset<
  DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
> = Array<z.infer<DataPoint>>;

export const EvaluatorResponseSchema = z.array(
  z.object({
    sampleIndex: z.number(),
    testCaseId: z.string().optional(),
    evaluation: ScoreSchema,
  })
);

export type EvaluatorResponse = z.infer<typeof EvaluatorResponseSchema>;

type EvaluatorFn<
  DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> = (
  input: Dataset<DataPoint>,
  evaluatorOptions?: z.infer<CustomOptions>
) => Promise<EvaluatorResponse>;

export type EvaluatorAction<
  DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> = Action<typeof EvalRequestSchema, typeof EvaluatorResponseSchema> & {
  __dataPointType?: DataPoint;
  __customOptionsType?: CustomOptions;
};

function withMetadata<
  DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  evaluator: Action<typeof EvalRequestSchema, typeof EvaluatorResponseSchema>,
  dataPointType?: DataPoint,
  customOptionsType?: CustomOptions
): EvaluatorAction<DataPoint, CustomOptions> {
  const withMeta = evaluator as EvaluatorAction<DataPoint, CustomOptions>;
  withMeta.__dataPointType = dataPointType;
  withMeta.__customOptionsType = customOptionsType;
  return withMeta;
}

const EvalRequestSchema = z.object({
  dataset: z.array(BaseDataPointSchema),
  options: z.unknown(),
});

/**
 * Creates evaluator action for the provided {@link EvaluatorFn} implementation.
 */
export function defineEvaluator<
  DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
  EvaluatorOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  options: {
    name: string;
    dataPointType?: DataPoint;
    customOptionsType?: EvaluatorOptions;
  },
  runner: EvaluatorFn<DataPoint, EvaluatorOptions>
) {
  const evaluator = action(
    {
      name: options.name,
      inputSchema: EvalRequestSchema.extend({
        dataset: options.dataPointType
          ? z.array(options.dataPointType)
          : z.array(BaseDataPointSchema),
        options: options.customOptionsType ?? z.unknown(),
      }),
      outputSchema: EvaluatorResponseSchema,
    },
    (i) => {
      setCustomMetadataAttributes({ subtype: 'evaluator' });
      return runner(i.dataset, i.options);
    }
  );
  const ewm = withMetadata(
    evaluator as any as Action<
      typeof EvalRequestSchema,
      typeof EvaluatorResponseSchema
    >,
    options.dataPointType,
    options.customOptionsType
  );
  registry.registerAction('evaluator', evaluator.__action.name, evaluator);
  return ewm;
}

export type EvaluatorArgument<
  DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> =
  | string
  | EvaluatorAction<DataPoint, CustomOptions>
  | EvaluatorReference<CustomOptions>;

/**
 * A veneer for interacting with evaluators.
 */
export async function evaluate<
  DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
  EvaluatorOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(params: {
  evaluator: EvaluatorArgument<DataPoint, EvaluatorOptions>;
  dataset: Dataset<DataPoint>;
  options?: z.infer<EvaluatorOptions>;
}): Promise<EvaluatorResponse> {
  let evaluator: EvaluatorAction<DataPoint, EvaluatorOptions>;
  if (typeof params.evaluator === 'string') {
    evaluator = await lookupAction(`/evaluator/${params.evaluator}`);
  } else if (Object.hasOwnProperty.call(params.evaluator, 'info')) {
    evaluator = await lookupAction(`/evaluator/${params.evaluator.name}`);
  } else {
    evaluator = params.evaluator as EvaluatorAction<
      DataPoint,
      EvaluatorOptions
    >;
  }
  if (!evaluator) {
    throw new Error('Unable to utilize the provided evaluator');
  }
  return (await evaluator({
    dataset: params.dataset,
    options: params.options,
  })) as EvaluatorResponse;
}

export const EvaluatorInfoSchema = z.object({
  /** Friendly label for this evaluator */
  label: z.string().optional(),
  metrics: z.array(z.string()),
});
export type EvaluatorInfo = z.infer<typeof EvaluatorInfoSchema>;

export interface EvaluatorReference<CustomOptions extends z.ZodTypeAny> {
  name: string;
  configSchema?: CustomOptions;
  info?: EvaluatorInfo;
}

/**
 * Helper method to configure a {@link EvaluatorReference} to a plugin.
 */
export function evaluatorRef<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
>(
  options: EvaluatorReference<CustomOptionsSchema>
): EvaluatorReference<CustomOptionsSchema> {
  return { ...options };
}
