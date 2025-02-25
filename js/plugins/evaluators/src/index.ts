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

import { Genkit, z } from 'genkit';
import {
  BaseEvalDataPoint,
  BaseEvalOptions,
  EvalResponse,
  EvalStatusEnum,
  Score,
  StatusOverrideFn,
  evaluatorRef,
} from 'genkit/evaluator';
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';
import {
  answerRelevancyScore,
  faithfulnessScore,
  maliciousnessScore,
} from './metrics/index.js';
import { GenkitMetric, GenkitMetricConfig } from './types.js';
export { GenkitMetric, GenkitMetricConfig };

const PLUGIN_NAME = 'genkitEval';

export interface PluginOptions<
  ModelCustomOptions extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny,
> {
  metrics: Array<GenkitMetricConfig<ModelCustomOptions, EmbedderCustomOptions>>;
}

/**
 * Reference to the Genkit evaluator for a specified metric
 */
export const genkitEvalRef = (metric: GenkitMetric) =>
  evaluatorRef({
    name: `${PLUGIN_NAME}/${metric.toLocaleLowerCase()}`,
    configSchema: z.undefined(),
    info: {
      label: `Genkit RAG Evaluator for ${metric}`,
      metrics: [metric],
    },
  });

/**
 * Genkit evaluation plugin that provides the RAG evaluators
 */
export function genkitEval<
  ModelCustomOptions extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny,
>(
  params: PluginOptions<ModelCustomOptions, EmbedderCustomOptions>
): GenkitPlugin {
  return genkitPlugin(`${PLUGIN_NAME}`, async (ai: Genkit) => {
    genkitEvaluators(ai, params);
  });
}

export default genkitEval;

function fillScores(
  dataPoint: BaseEvalDataPoint,
  score: Score,
  statusOverrideFn?: StatusOverrideFn
): EvalResponse {
  const status = statusOverrideFn
    ? statusOverrideFn(score)
    : EvalStatusEnum.UNKNOWN;
  const evaluation = { ...score, status };
  return { testCaseId: dataPoint.testCaseId, evaluation };
}

/**
 * Configures a Genkit evaluator
 */
export function genkitEvaluators<
  ModelCustomOptions extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny,
>(
  ai: Genkit,
  params: PluginOptions<ModelCustomOptions, EmbedderCustomOptions>
) {
  let { metrics } = params;
  if (metrics.length === 0) {
    throw new Error('No metrics configured in genkitEval plugin');
  }
  return metrics.map((metric) => {
    switch (metric.type) {
      case GenkitMetric.ANSWER_RELEVANCY: {
        return ai.defineEvaluator(
          {
            name: `${PLUGIN_NAME}/${metric.type.toLocaleLowerCase()}`,
            displayName: 'Answer Relevancy',
            definition:
              'Assesses how pertinent the generated answer is to the given prompt',
          },
          async (datapoint: BaseEvalDataPoint, options: BaseEvalOptions) => {
            const answerRelevancy = await answerRelevancyScore(
              ai,
              metric.judge,
              datapoint,
              metric.embedder,
              metric.judgeConfig,
              metric.embedderOptions
            );
            return fillScores(
              datapoint,
              answerRelevancy,
              metric.statusOverrideFn ?? options?.statusOverrideFn
            );
          }
        );
      }
      case GenkitMetric.FAITHFULNESS: {
        return ai.defineEvaluator(
          {
            name: `${PLUGIN_NAME}/${metric.type.toLocaleLowerCase()}`,
            displayName: 'Faithfulness',
            definition:
              'Measures the factual consistency of the generated answer against the given context',
          },
          async (datapoint: BaseEvalDataPoint, options: BaseEvalOptions) => {
            const faithfulness = await faithfulnessScore(
              ai,
              metric.judge,
              datapoint,
              metric.judgeConfig
            );
            return fillScores(
              datapoint,
              faithfulness,
              metric.statusOverrideFn ?? options?.statusOverrideFn
            );
          }
        );
      }
      case GenkitMetric.MALICIOUSNESS: {
        return ai.defineEvaluator(
          {
            name: `${PLUGIN_NAME}/${metric.type.toLocaleLowerCase()}`,
            displayName: 'Maliciousness',
            definition:
              'Measures whether the generated output intends to deceive, harm, or exploit',
          },
          async (datapoint: BaseEvalDataPoint, options: BaseEvalOptions) => {
            const maliciousness = await maliciousnessScore(
              ai,
              metric.judge,
              datapoint,
              metric.judgeConfig
            );
            return fillScores(
              datapoint,
              maliciousness,
              metric.statusOverrideFn ?? options?.statusOverrideFn
            );
          }
        );
      }
    }
  });
}
