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

import { Action, defineAction } from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import { lookupAction } from '@genkit-ai/core/registry';
import { SPAN_TYPE_ATTR, runInNewSpan } from '@genkit-ai/core/tracing';
import * as z from 'zod';

export const ATTR_PREFIX = 'genkit';
export const SPAN_STATE_ATTR = ATTR_PREFIX + ':state';

export const BaseDataPointSchema = z.object({
  input: z.unknown(),
  output: z.unknown().optional(),
  context: z.array(z.unknown()).optional(),
  reference: z.unknown().optional(),
  testCaseId: z.string().optional(),
  traceIds: z.array(z.string()).optional(),
});

export const ScoreSchema = z.object({
  score: z.union([z.number(), z.string(), z.boolean()]).optional(),
  // TODO: use StatusSchema
  error: z.string().optional(),
  details: z
    .object({
      reasoning: z.string().optional(),
    })
    .passthrough()
    .optional(),
});

// Update genkit-tools/src/utils/evals.ts if you change this value
export const EVALUATOR_METADATA_KEY_DISPLAY_NAME = 'evaluatorDisplayName';
export const EVALUATOR_METADATA_KEY_DEFINITION = 'evaluatorDefinition';
export const EVALUATOR_METADATA_KEY_IS_BILLED = 'evaluatorIsBilled';

export type Score = z.infer<typeof ScoreSchema>;
export type BaseDataPoint = z.infer<typeof BaseDataPointSchema>;
export type Dataset<
  DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
> = Array<z.infer<DataPoint>>;

export const EvalResponseSchema = z.object({
  sampleIndex: z.number().optional(),
  testCaseId: z.string().optional(),
  traceId: z.string().optional(),
  spanId: z.string().optional(),
  evaluation: ScoreSchema,
});
export type EvalResponse = z.infer<typeof EvalResponseSchema>;

export const EvalResponsesSchema = z.array(EvalResponseSchema);
export type EvalResponses = z.infer<typeof EvalResponsesSchema>;

type EvaluatorFn<
  DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> = (
  input: z.infer<DataPoint>,
  evaluatorOptions?: z.infer<CustomOptions>
) => Promise<EvalResponse>;

export type EvaluatorAction<
  DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> = Action<typeof EvalRequestSchema, typeof EvalResponsesSchema> & {
  __dataPointType?: DataPoint;
  __configSchema?: CustomOptions;
};

function withMetadata<
  DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  evaluator: Action<typeof EvalRequestSchema, typeof EvalResponsesSchema>,
  dataPointType?: DataPoint,
  configSchema?: CustomOptions
): EvaluatorAction<DataPoint, CustomOptions> {
  const withMeta = evaluator as EvaluatorAction<DataPoint, CustomOptions>;
  withMeta.__dataPointType = dataPointType;
  withMeta.__configSchema = configSchema;
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
    displayName: string;
    definition: string;
    dataPointType?: DataPoint;
    configSchema?: EvaluatorOptions;
    isBilled?: boolean;
  },
  runner: EvaluatorFn<DataPoint, EvaluatorOptions>
) {
  const metadata = {};
  metadata[EVALUATOR_METADATA_KEY_IS_BILLED] =
    options.isBilled == undefined ? true : options.isBilled;
  metadata[EVALUATOR_METADATA_KEY_DISPLAY_NAME] = options.displayName;
  metadata[EVALUATOR_METADATA_KEY_DEFINITION] = options.definition;
  const evaluator = defineAction(
    {
      actionType: 'evaluator',
      name: options.name,
      inputSchema: EvalRequestSchema.extend({
        dataset: options.dataPointType
          ? z.array(options.dataPointType)
          : z.array(BaseDataPointSchema),
        options: options.configSchema ?? z.unknown(),
        evalRunId: z.string(),
      }),
      outputSchema: EvalResponsesSchema,
      metadata: metadata,
    },
    async (i) => {
      let evalResponses: EvalResponses = [];
      for (let index = 0; index < i.dataset.length; index++) {
        const datapoint = i.dataset[index];
        try {
          await runInNewSpan(
            {
              metadata: {
                name: `Test Case ${datapoint.testCaseId}`,
                metadata: { 'evaluator:evalRunId': i.evalRunId },
              },
              labels: {
                [SPAN_TYPE_ATTR]: 'evaluator',
              },
            },
            async (metadata, otSpan) => {
              const spanId = otSpan.spanContext().spanId;
              const traceId = otSpan.spanContext().traceId;
              try {
                metadata.input = {
                  input: datapoint.input,
                  output: datapoint.output,
                  context: datapoint.context,
                };
                const testCaseOutput = await runner(datapoint, i.options);
                testCaseOutput.sampleIndex = index;
                testCaseOutput.spanId = spanId;
                testCaseOutput.traceId = traceId;
                metadata.output = testCaseOutput;
                evalResponses.push(testCaseOutput);
                return testCaseOutput;
              } catch (e) {
                evalResponses.push({
                  sampleIndex: index,
                  spanId,
                  traceId,
                  testCaseId: datapoint.testCaseId,
                  evaluation: {
                    error: `Evaluation of test case ${datapoint.testCaseId} failed: \n${(e as Error).stack}`,
                  },
                });
                throw e;
              }
            }
          );
        } catch (e) {
          logger.error(
            `Evaluation of test case ${datapoint.testCaseId} failed: \n${(e as Error).stack}`
          );
          continue;
        }
      }
      return evalResponses;
    }
  );
  const ewm = withMetadata(
    evaluator as any as Action<
      typeof EvalRequestSchema,
      typeof EvalResponsesSchema
    >,
    options.dataPointType,
    options.configSchema
  );
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
}): Promise<EvalResponses> {
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
  })) as EvalResponses;
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
