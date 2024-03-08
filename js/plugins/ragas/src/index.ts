import { EmbedderReference } from '@google-genkit/ai/embedders';
import {
  Dataset,
  defineEvaluator,
  evaluatorRef,
} from '@google-genkit/ai/evaluators';
import { ModelReference } from '@google-genkit/ai/model';
import { PluginProvider, genkitPlugin } from '@google-genkit/common/config';
import * as z from 'zod';
import {
  answerRelevancyScore,
  contextPrecisionScore,
  faithfulnessScore,
} from './metrics';
import {
  RagasDataPoint,
  RagasDataPointSchema,
  RagasDataPointZodType,
  RagasMetric,
} from './types';
export { RagasDataPoint, RagasDataPointZodType, RagasMetric };

export interface PluginOptions<
  ModelCustomOptions extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
> {
  metrics?: Array<RagasMetric>;
  judge: ModelReference<ModelCustomOptions>;
  embedder?: EmbedderReference<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}

/**
 * Reference to the RAGAS evaluator for a specified metric
 */
export const ragasRef = (metric: RagasMetric) =>
  evaluatorRef({
    name: `ragas/${metric.toLocaleLowerCase()}`,
    configSchema: z.undefined(),
    info: {
      names: ['ragas'],
      label: `RAGAS Evaluator for ${metric}`,
      metrics: [metric],
    },
  });

/**
 * RAGAS plugin that provides the RAGAS evaluator
 */
export function ragas<
  ModelCustomOptions extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(
  params: PluginOptions<ModelCustomOptions, EmbedderCustomOptions>
): PluginProvider {
  const plugin = genkitPlugin(
    'ragas',
    async (
      params: PluginOptions<ModelCustomOptions, EmbedderCustomOptions>
    ) => ({
      evaluators: [...ragasEvaluators(params)],
    })
  );
  return plugin(params);
}

export default ragas;

function hasMetric(arr: RagasMetric[] | undefined, metric: RagasMetric) {
  return arr?.some((m) => m === metric);
}

function fillScores(
  dataset: Dataset<RagasDataPointZodType>,
  metric: RagasMetric,
  scores?: number[]
) {
  return dataset.map((v, i) => {
    let score = {};
    score[metric] = !!scores ? scores[i] : 0;
    return {
      sample: v,
      score,
    };
  });
}

/**
 * Configures a RAGAS evaluator
 */
export function ragasEvaluators<
  ModelCustomOptions extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: PluginOptions<ModelCustomOptions, EmbedderCustomOptions>) {
  let { metrics, judge, embedder, embedderOptions } = params;
  if (!metrics) {
    metrics = [RagasMetric.CONTEXT_PRECISION, RagasMetric.FAITHFULNESS];
  } else if (!embedder && hasMetric(metrics, RagasMetric.ANSWER_RELEVANCY)) {
    throw new Error('Embedder must be specified if computing answer relvancy');
  }
  return metrics.map((metric) => {
    return defineEvaluator(
      {
        provider: 'ragas',
        evaluatorId: `ragas/${metric.toLocaleLowerCase()}`,
        dataPointType: RagasDataPointSchema,
        customOptionsType: z.undefined(),
      },
      async (dataset) => {
        let faithfulness, contextPrecision, answerRelevancy;
        switch (metric) {
          case RagasMetric.CONTEXT_PRECISION: {
            contextPrecision = await contextPrecisionScore(judge, dataset);
            console.log('contextPrecision', contextPrecision);
            return fillScores(
              dataset,
              RagasMetric.CONTEXT_PRECISION,
              contextPrecision
            );
          }
          case RagasMetric.ANSWER_RELEVANCY: {
            answerRelevancy = await answerRelevancyScore(
              judge,
              dataset,
              embedder!,
              embedderOptions
            );
            return fillScores(
              dataset,
              RagasMetric.ANSWER_RELEVANCY,
              answerRelevancy
            );
          }
          case RagasMetric.FAITHFULNESS: {
            faithfulness = await faithfulnessScore(judge, dataset);
            return fillScores(dataset, RagasMetric.FAITHFULNESS, faithfulness);
          }
        }
      }
    );
  });
}
