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
import { EvaluatorFactory } from './evaluator_factory';

/**
 * Vertex AI Evaluation metrics. See API documentation for more information.
 * https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/evaluation#parameter-list
 */
export enum VertexAIEvaluationMetricType {
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

    console.log(
      `Creating evaluator for metric ${metricType} with metricSpec ${metricSpec}`
    );

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

function createSafetyEvaluator(
  factory: EvaluatorFactory,
  metricSpec: any
): Action {
  return factory.create(
    {
      metric: VertexAIEvaluationMetricType.SAFETY,
      displayName: 'Safety',
      definition: 'Assesses the level of safety of an output',
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
    (response: any, datapoint: BaseDataPoint) => {
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
    (response: any, datapoint: BaseDataPoint) => {
      return {
        testCaseId: datapoint.testCaseId,
        evaluation: {
          score: response.groundedNessResult?.score,
          details: {
            reasoning: response.groundedNessResult?.explanation,
          },
        },
      };
    }
  );
}
