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

import { Action, Genkit, z } from 'genkit';
import { GoogleAuth } from 'google-auth-library';
import { EvaluatorFactory } from './evaluator_factory.js';

/**
 * Checks AI Safety policies. See API documentation for more information.
 * TODO: add documentation link.
 */
export enum ChecksEvaluationMetricType {
  // TODO: Change to match checks policies. 
  SAFETY = 'SAFETY',
  HARASSMENT = 'HARASSMENT',
}

/**
 * Evaluation metric config. Use `metricSpec` to define the behavior of the metric.
 * The value of `metricSpec` will be included in the request to the API. See the API documentation
 * for details on the possible values of `metricSpec` for each metric.
 * https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/evaluation#parameter-list
 */
export type ChecksEvaluationMetricConfig = {
  type: ChecksEvaluationMetricType;
  metricSpec: any;
};

export type ChecksEvaluationMetric =
  | ChecksEvaluationMetricType
  | ChecksEvaluationMetricConfig;

export function checksEvaluators(
  ai: Genkit,
  auth: GoogleAuth,
  metrics: ChecksEvaluationMetric[],
  projectId: string,
  location: string
): Action[] {
  const factory = new EvaluatorFactory(auth, location, projectId);
  return metrics.map((metric) => {
    const metricType = isConfig(metric) ? metric.type : metric;
    const metricSpec = isConfig(metric) ? metric.metricSpec : {};

    switch (metricType) {
      case ChecksEvaluationMetricType.SAFETY: {
        return createSafetyEvaluator(ai, factory, metricSpec);
      }
      case ChecksEvaluationMetricType.HARASSMENT: {
        return createHarassmentEvaluator(ai, factory, metricSpec)
      }
    }
  });
}

function isConfig(
  config: ChecksEvaluationMetric
): config is ChecksEvaluationMetricConfig {
  return (config as ChecksEvaluationMetricConfig).type !== undefined;
}


//TODO: this is the schema:
// {
//   policyResults: [
//     {
//       policyType: 'HARASSMENT',
//       score: 0.31868133,
//       violationResult: 'NON_VIOLATIVE'
//     }
//   ]
// }

const HarassmentResponseSchema = z.object({
  policyResults: z.array(
    z.object({
      policyType: z.string(),
      score: z.number(),
      violationResult: z.string()
    })
  )
});

function createHarassmentEvaluator(
  ai: Genkit,
  factory: EvaluatorFactory,
  metricSpec: any
): Action {
  return factory.create(
    ai,
    {
      metric: ChecksEvaluationMetricType.HARASSMENT,
      displayName: 'Harassment',
      definition: 'Assesses the text constittues harassment.',
      responseSchema: HarassmentResponseSchema,
      checksEval: true
    },
    (datapoint) => {
      return {
        input: {
          text_input: {
            content: datapoint.output as string
          },
        },
        policies: {
          policy_type: "HARASSMENT",
        }
      };
    },
    (response) => {
      return {
        score: response.policyResults[0].score,
        details: {
          reasoning: response.policyResults[0].violationResult
        }
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
  ai: Genkit,
  factory: EvaluatorFactory,
  metricSpec: any
): Action {
  return factory.create(
    ai,
    {
      metric: ChecksEvaluationMetricType.SAFETY,
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
    (response) => {
      return {
        score: response.safetyResult.score,
        details: {
          reasoning: response.safetyResult.explanation,
        },
      };
    }
  );
}
