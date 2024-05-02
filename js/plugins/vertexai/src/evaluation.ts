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

import { BaseDataPoint } from '@genkit-ai/ai/evaluator';
import { Action } from '@genkit-ai/core';
import { GoogleAuth } from 'google-auth-library';
import { JSONClient } from 'google-auth-library/build/src/auth/googleauth';
import z from 'zod';
import { EvaluatorFactory } from './evaluator_factory';

/**
 * Vertex AI Evaluation metrics. See API documentation for more information.
 * https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/evaluation#parameter-list
 */
export enum VertexAIEvaluationMetricType {
  // Update genkit/docs/plugins/vertex-ai.md when modifying the list of enums
  SAFETY = 'SAFETY',
  GROUNDEDNESS = 'GROUNDEDNESS',
  BLEU = 'BLEU',
  ROUGE = 'ROUGE',
}

/**
 * Evaluation metric config. Use `metricSpec` to define the behavior of the metric.
 * The value of `metricSpec` will be included in the request to the API. See the API documentation
 * for details on the possible values of `metricSpec` for each metric.
 * https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/evaluation#parameter-list
 */
export type VertexAIEvaluationMetricConfig = {
  type: VertexAIEvaluationMetricType;
  metricSpec: any;
};

export type VertexAIEvaluationMetric =
  | VertexAIEvaluationMetricType
  | VertexAIEvaluationMetricConfig;

export function vertexEvaluators(
  auth: GoogleAuth<JSONClient>,
  metrics: VertexAIEvaluationMetric[],
  projectId: string,
  location: string
): Action[] {
  const factory = new EvaluatorFactory(auth, location, projectId);
  return metrics.map((metric) => {
    const metricType = isConfig(metric) ? metric.type : metric;
    const metricSpec = isConfig(metric) ? metric.metricSpec : {};

    switch (metricType) {
      case VertexAIEvaluationMetricType.BLEU: {
        return createBleuEvaluator(factory, metricSpec);
      }
      case VertexAIEvaluationMetricType.ROUGE: {
        return createRougeEvaluator(factory, metricSpec);
      }
      case VertexAIEvaluationMetricType.SAFETY: {
        return createSafetyEvaluator(factory, metricSpec);
      }
      case VertexAIEvaluationMetricType.GROUNDEDNESS: {
        return createGroundednessEvaluator(factory, metricSpec);
      }
    }
  });
}

function isConfig(
  config: VertexAIEvaluationMetric
): config is VertexAIEvaluationMetricConfig {
  return (config as VertexAIEvaluationMetricConfig).type !== undefined;
}

const BleuResponseSchema = z.object({
  bleuResults: z.object({
    bleuMetricValues: z.array(z.object({ score: z.number() })),
  }),
});

// TODO: Add support for batch inputs
function createBleuEvaluator(
  factory: EvaluatorFactory,
  metricSpec: any
): Action {
  return factory.create(
    {
      metric: VertexAIEvaluationMetricType.BLEU,
      displayName: 'BLEU',
      definition:
        'Computes the BLEU score by comparing the output against the ground truth',
      responseSchema: BleuResponseSchema,
    },
    (datapoint) => {
      if (!datapoint.reference) {
        throw new Error('Reference is required');
      }

      return {
        bleuInput: {
          metricSpec,
          instances: [
            {
              prediction: datapoint.output as string,
              reference: datapoint.reference,
            },
          ],
        },
      };
    },
    (response, datapoint) => {
      return {
        testCaseId: datapoint.testCaseId,
        evaluation: {
          score: response.bleuResults.bleuMetricValues[0].score,
        },
      };
    }
  );
}

const RougeResponseSchema = z.object({
  rougeResults: z.object({
    rougeMetricValues: z.array(z.object({ score: z.number() })),
  }),
});

// TODO: Add support for batch inputs
function createRougeEvaluator(
  factory: EvaluatorFactory,
  metricSpec: any
): Action {
  return factory.create(
    {
      metric: VertexAIEvaluationMetricType.ROUGE,
      displayName: 'ROUGE',
      definition:
        'Computes the ROUGE score by comparing the output against the ground truth',
      responseSchema: RougeResponseSchema,
    },
    (datapoint) => {
      if (!datapoint.reference) {
        throw new Error('Reference is required');
      }

      return {
        rougeInput: {
          metricSpec,
          instances: {
            prediction: datapoint.output as string,
            reference: datapoint.reference,
          },
        },
      };
    },
    (response, datapoint) => {
      return {
        testCaseId: datapoint.testCaseId,
        evaluation: {
          score: response.rougeResults.rougeMetricValues[0].score,
        },
      };
    }
  );
}

const SafetyResponseSchema = z.object({
  safetyResult: z.object({
    score: z.number(),
    explanation: z.string(),
    confidence: z.number(),
  }),
});

function createSafetyEvaluator(
  factory: EvaluatorFactory,
  metricSpec: any
): Action {
  return factory.create(
    {
      metric: VertexAIEvaluationMetricType.SAFETY,
      displayName: 'Safety',
      definition: 'Assesses the level of safety of an output',
      responseSchema: SafetyResponseSchema,
    },
    (datapoint) => {
      return {
        safetyInput: {
          metricSpec,
          instance: {
            prediction: datapoint.output as string,
          },
        },
      };
    },
    (response, datapoint: BaseDataPoint) => {
      return {
        testCaseId: datapoint.testCaseId,
        evaluation: {
          score: response.safetyResult?.score,
          details: {
            reasoning: response.safetyResult?.explanation,
          },
        },
      };
    }
  );
}

const GroundednessResponseSchema = z.object({
  groundednessResult: z.object({
    score: z.number(),
    explanation: z.string(),
    confidence: z.number(),
  }),
});

function createGroundednessEvaluator(
  factory: EvaluatorFactory,
  metricSpec: any
): Action {
  return factory.create(
    {
      metric: VertexAIEvaluationMetricType.GROUNDEDNESS,
      displayName: 'Groundedness',
      definition:
        'Assesses the ability to provide or reference information included only in the context',
      responseSchema: GroundednessResponseSchema,
    },
    (datapoint) => {
      return {
        groundednessInput: {
          metricSpec,
          instance: {
            prediction: datapoint.output as string,
            context: datapoint.context?.join('. '),
          },
        },
      };
    },
    (response, datapoint: BaseDataPoint) => {
      return {
        testCaseId: datapoint.testCaseId,
        evaluation: {
          score: response.groundednessResult?.score,
          details: {
            reasoning: response.groundednessResult?.explanation,
          },
        },
      };
    }
  );
}
