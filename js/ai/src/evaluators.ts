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

import { action, Action } from '@genkit-ai/common';
import * as registry from '@genkit-ai/common/registry';
import { lookupAction } from '@genkit-ai/common/registry';
import { setCustomMetadataAttributes } from '@genkit-ai/common/tracing';
import * as z from 'zod';

export const BaseDataPointSchema = z.object({
  input: z.unknown(),
  output: z.unknown().optional(),
  context: z.unknown().optional(),
  testCaseId: z.string(),
});
type BaseDataPointZodType = typeof BaseDataPointSchema;

export type Dataset<DataPoint extends z.ZodTypeAny = BaseDataPointZodType> =
  Array<z.infer<DataPoint>>;

export interface EvalResult<DataPoint extends z.ZodTypeAny> {
  sample: z.infer<DataPoint>;
  score: Record<string, number | null>;
}

type EvaluatorFn<
  DataPoint extends z.ZodTypeAny = BaseDataPointZodType,
  CustomOptions extends z.ZodTypeAny = z.ZodAny
> = (
  input: Dataset<DataPoint>,
  evaluatorOptions?: z.infer<CustomOptions>
) => Promise<Array<EvalResult<DataPoint>>>;

export type EvaluatorAction<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodAny,
  DataPoint extends z.ZodTypeAny = BaseDataPointZodType,
  CustomOptions extends z.ZodTypeAny = z.ZodAny
> = Action<I, O> & {
  __dataPointType: DataPoint;
  __customOptionsType: CustomOptions;
};

function withMetadata<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  DataPoint extends z.ZodTypeAny = BaseDataPointZodType,
  CustomOptions extends z.ZodTypeAny = z.ZodAny
>(
  evaluator: Action<I, O>,
  dataPointType: DataPoint,
  customOptionsType: CustomOptions
): EvaluatorAction<I, O, DataPoint, CustomOptions> {
  const withMeta = evaluator as EvaluatorAction<I, O, DataPoint, CustomOptions>;
  withMeta.__dataPointType = dataPointType;
  withMeta.__customOptionsType = customOptionsType;
  return withMeta;
}

/**
 * Creates evaluator action for the provided {@link EvaluatorFn} implementation.
 */
export function defineEvaluator<
  DataPoint extends z.ZodTypeAny = BaseDataPointZodType,
  EvaluatorOptions extends z.ZodTypeAny = z.ZodAny
>(
  options: {
    provider: string;
    evaluatorId: string;
    dataPointType: DataPoint;
    customOptionsType: EvaluatorOptions;
  },
  runner: EvaluatorFn<DataPoint, EvaluatorOptions>
) {
  const evaluator = action(
    {
      name: options.evaluatorId,
      input: z.object({
        dataset: z.array(options.dataPointType),
        options: options.customOptionsType,
      }),
      output: z.array(
        z.object({
          sample: options.dataPointType,
          score: z.record(z.string(), z.number().nullable()),
        })
      ),
    },
    (i) => {
      setCustomMetadataAttributes({ subtype: 'evaluator' });
      return runner(i.dataset, i.options);
    }
  );
  const ewm = withMetadata(
    evaluator,
    options.dataPointType,
    options.customOptionsType
  );
  registry.registerAction('evaluator', evaluator.__action.name, evaluator);
  return ewm;
}

/**
 * A veneer for interacting with evaluators.
 */
export async function evaluate<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  DataPoint extends z.ZodTypeAny = BaseDataPointZodType,
  EvaluatorOptions extends z.ZodTypeAny = z.ZodAny
>(params: {
  evaluator:
    | EvaluatorAction<I, O, DataPoint, EvaluatorOptions>
    | EvaluatorReference<EvaluatorOptions>;
  dataset: Dataset<DataPoint>;
  options?: z.infer<EvaluatorOptions>;
}): Promise<Array<Record<string, number>>> {
  let evaluator: EvaluatorAction<I, O, DataPoint, EvaluatorOptions>;
  if (Object.hasOwnProperty.call(params.evaluator, 'info')) {
    evaluator = await lookupAction(`/evaluator/${params.evaluator.name}`);
  } else {
    evaluator = params.evaluator as EvaluatorAction<
      I,
      O,
      DataPoint,
      EvaluatorOptions
    >;
  }
  if (!evaluator) {
    throw new Error('Unable to utilize the provided evaluator');
  }
  return await evaluator({
    dataset: params.dataset,
    options: params.options,
  });
}

export const EvaluatorInfoSchema = z.object({
  /** Acceptable names for this evaluator */
  names: z.array(z.string()).optional(),
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
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny
>(
  options: EvaluatorReference<CustomOptionsSchema>
): EvaluatorReference<CustomOptionsSchema> {
  return { ...options };
}
