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

import { EmbedderReference } from '@genkit-ai/ai/embedder';
import {
  BaseDataPoint,
  defineEvaluator,
  EvalResponse,
  evaluatorRef,
  Score,
} from '@genkit-ai/ai/evaluator';
import { ModelReference } from '@genkit-ai/ai/model';
import { genkitPlugin, PluginProvider } from '@genkit-ai/core';
import * as z from 'zod';
import {
  answerRelevancyScore,
  faithfulnessScore,
  maliciousnessScore,
} from './metrics';
import { GenkitMetric } from './types';
export { GenkitMetric };

const PLUGIN_NAME = 'genkitEval';

export interface PluginOptions<
  ModelCustomOptions extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny,
> {
  metrics?: Array<GenkitMetric>;
  judge: ModelReference<ModelCustomOptions>;
  judgeConfig?: z.infer<ModelCustomOptions>;
  embedder?: EmbedderReference<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
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
): PluginProvider {
  const plugin = genkitPlugin(
    `${PLUGIN_NAME}`,
    async (
      params: PluginOptions<ModelCustomOptions, EmbedderCustomOptions>
    ) => ({
      evaluators: [...genkitEvaluators(params)],
    })
  );
  return plugin(params);
}

export default genkitEval;

function hasMetric(arr: GenkitMetric[] | undefined, metric: GenkitMetric) {
  return arr?.some((m) => m === metric);
}

function fillScores(dataPoint: BaseDataPoint, score: Score): EvalResponse {
  return {
    testCaseId: dataPoint.testCaseId,
    evaluation: score,
  };
}

/**
 * Configures a Genkit evaluator
 */
export function genkitEvaluators<
  ModelCustomOptions extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny,
>(params: PluginOptions<ModelCustomOptions, EmbedderCustomOptions>) {
  let { metrics, judge, judgeConfig, embedder, embedderOptions } = params;
  if (!metrics) {
    metrics = [GenkitMetric.MALICIOUSNESS, GenkitMetric.FAITHFULNESS];
  } else if (!embedder && hasMetric(metrics, GenkitMetric.ANSWER_RELEVANCY)) {
    throw new Error('Embedder must be specified if computing answer relvancy');
  }
  return metrics.map((metric) => {
    switch (metric) {
      case GenkitMetric.ANSWER_RELEVANCY: {
        return defineEvaluator(
          {
            name: `${PLUGIN_NAME}/${metric.toLocaleLowerCase()}`,
            displayName: 'Answer Relevancy',
            definition:
              'Assesses how pertinent the generated answer is to the given prompt',
          },
          async (datapoint: BaseDataPoint) => {
            const answerRelevancy = await answerRelevancyScore(
              judge,
              datapoint,
              embedder!,
              judgeConfig,
              embedderOptions
            );
            return fillScores(datapoint, answerRelevancy);
          }
        );
      }
      case GenkitMetric.FAITHFULNESS: {
        return defineEvaluator(
          {
            name: `${PLUGIN_NAME}/${metric.toLocaleLowerCase()}`,
            displayName: 'Faithfulness',
            definition:
              'Measures the factual consistency of the generated answer against the given context',
          },
          async (datapoint: BaseDataPoint) => {
            const faithfulness = await faithfulnessScore(
              judge,
              datapoint,
              judgeConfig
            );
            return fillScores(datapoint, faithfulness);
          }
        );
      }
      case GenkitMetric.MALICIOUSNESS: {
        return defineEvaluator(
          {
            name: `${PLUGIN_NAME}/${metric.toLocaleLowerCase()}`,
            displayName: 'Maliciousness',
            definition:
              'Measures whether the generated output intends to deceive, harm, or exploit',
          },
          async (datapoint: BaseDataPoint) => {
            const maliciousness = await maliciousnessScore(
              judge,
              datapoint,
              judgeConfig
            );
            return fillScores(datapoint, maliciousness);
          }
        );
      }
    }
  });
}
