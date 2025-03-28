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

import { Action, defineAction, z } from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import { Registry } from '@genkit-ai/core/registry';
import { toJsonSchema } from '@genkit-ai/core/schema';
import { SPAN_TYPE_ATTR, runInNewSpan } from '@genkit-ai/core/tracing';
import { randomUUID } from 'crypto';

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

// DataPoint that is to be used for actions. This needs testCaseId to be present.
export const BaseEvalDataPointSchema = BaseDataPointSchema.extend({
  testCaseId: z.string(),
});
export type BaseEvalDataPoint = z.infer<typeof BaseEvalDataPointSchema>;

const EvalStatusEnumSchema = z.enum(['UNKNOWN', 'PASS', 'FAIL']);

/** Enum that indicates if an evaluation has passed or failed */
export enum EvalStatusEnum {
  UNKNOWN = 'UNKNOWN',
  PASS = 'PASS',
  FAIL = 'FAIL',
}

export const ScoreSchema = z.object({
  id: z
    .string()
    .describe(
      'Optional ID to differentiate different scores if applying in a single evaluation'
    )
    .optional(),
  score: z.union([z.number(), z.string(), z.boolean()]).optional(),
  status: EvalStatusEnumSchema.optional(),
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
  testCaseId: z.string(),
  traceId: z.string().optional(),
  spanId: z.string().optional(),
  evaluation: z.union([ScoreSchema, z.array(ScoreSchema)]),
});
export type EvalResponse = z.infer<typeof EvalResponseSchema>;

export const EvalResponsesSchema = z.array(EvalResponseSchema);
export type EvalResponses = z.infer<typeof EvalResponsesSchema>;

export type EvaluatorFn<
  EvalDataPoint extends
    typeof BaseEvalDataPointSchema = typeof BaseEvalDataPointSchema,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> = (
  input: z.infer<EvalDataPoint>,
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
  evalRunId: z.string(),
  options: z.unknown(),
});

export interface EvaluatorParams<
  DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> {
  evaluator: EvaluatorArgument<DataPoint, CustomOptions>;
  dataset: Dataset<DataPoint>;
  evalRunId?: string;
  options?: z.infer<CustomOptions>;
}

/**
 * Creates evaluator action for the provided {@link EvaluatorFn} implementation.
 */
export function defineEvaluator<
  DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
  EvalDataPoint extends
    typeof BaseEvalDataPointSchema = typeof BaseEvalDataPointSchema,
  EvaluatorOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  options: {
    name: string;
    displayName: string;
    definition: string;
    dataPointType?: DataPoint;
    configSchema?: EvaluatorOptions;
    isBilled?: boolean;
  },
  runner: EvaluatorFn<EvalDataPoint, EvaluatorOptions>
) {
  const evalMetadata = {};
  evalMetadata[EVALUATOR_METADATA_KEY_IS_BILLED] =
    options.isBilled == undefined ? true : options.isBilled;
  evalMetadata[EVALUATOR_METADATA_KEY_DISPLAY_NAME] = options.displayName;
  evalMetadata[EVALUATOR_METADATA_KEY_DEFINITION] = options.definition;
  if (options.configSchema) {
    evalMetadata['customOptions'] = toJsonSchema({
      schema: options.configSchema,
    });
  }
  const evaluator = defineAction(
    registry,
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
      metadata: {
        type: 'evaluator',
        evaluator: evalMetadata,
      },
    },
    async (i) => {
      let evalResponses: EvalResponses = [];
      for (let index = 0; index < i.dataset.length; index++) {
        const datapoint: BaseEvalDataPoint = {
          ...i.dataset[index],
          testCaseId: i.dataset[index].testCaseId ?? randomUUID(),
        };
        try {
          await runInNewSpan(
            registry,
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
                    status: EvalStatusEnum.FAIL,
                  },
                });
                // Throw to mark the span as failed.
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
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  params: EvaluatorParams<DataPoint, CustomOptions>
): Promise<EvalResponses> {
  let evaluator: EvaluatorAction<DataPoint, CustomOptions>;
  if (typeof params.evaluator === 'string') {
    evaluator = await registry.lookupAction(`/evaluator/${params.evaluator}`);
  } else if (Object.hasOwnProperty.call(params.evaluator, 'info')) {
    evaluator = await registry.lookupAction(
      `/evaluator/${params.evaluator.name}`
    );
  } else {
    evaluator = params.evaluator as EvaluatorAction<DataPoint, CustomOptions>;
  }
  if (!evaluator) {
    throw new Error('Unable to utilize the provided evaluator');
  }
  return (await evaluator({
    dataset: params.dataset,
    options: params.options,
    evalRunId: params.evalRunId ?? randomUUID(),
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
