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

import { BaseDataPoint, defineEvaluator } from '@genkit-ai/ai/evaluator';
import { runInNewSpan } from '@genkit-ai/core/tracing';
import { GoogleAuth } from 'google-auth-library';
import { JSONClient } from 'google-auth-library/build/src/auth/googleauth';

/**
 * Vertex AI Evaluation metrics. See API documentation for more information.
 * https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/evaluation#parameter-list
 */
export enum VertexAIEvaluationMetric {
  SAFETY = 'SAFETY',
  GROUNDEDNESS = 'GROUNDEDNESS',
}

export function vertexEvaluators(
  auth: GoogleAuth<JSONClient>,
  metrics: VertexAIEvaluationMetric[],
  projectId: string,
  location: string
) {
  return metrics.map((metric) => {
    switch (metric) {
      case VertexAIEvaluationMetric.SAFETY: {
        return defineEvaluator(
          {
            name: `vertexai/${metric.toLocaleLowerCase()}`,
            displayName: 'Safety',
            definition: 'Assesses the level of safety of an output',
          },
          async (datapoint: BaseDataPoint) => {
            const response = await evaluateInstances(
              auth,
              location,
              projectId,
              {
                safetyInput: {
                  metricSpec: {},
                  instance: {
                    prediction: datapoint.output as string,
                  },
                },
              }
            );

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
      case VertexAIEvaluationMetric.GROUNDEDNESS: {
        return defineEvaluator(
          {
            name: `vertexai/${metric.toLocaleLowerCase()}`,
            displayName: 'Groundedness',
            definition:
              'Assesses the ability to provide or reference information included only in the context',
          },
          async (datapoint: BaseDataPoint) => {
            if (!datapoint.context || datapoint.context.length == 0) {
              throw new Error('Context was not provided');
            }
            const response = await evaluateInstances(
              auth,
              location,
              projectId,
              {
                groundednessInput: {
                  metricSpec: {},
                  instance: {
                    prediction: datapoint.output as string,
                    context: datapoint.context.join('. '),
                  },
                },
              }
            );
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
    }
  });
}

async function evaluateInstances(
  auth: GoogleAuth<JSONClient>,
  location: string,
  projectId: string,
  partialRequest: any
) {
  const locationName = `projects/${projectId}/locations/${location}`;
  return await runInNewSpan(
    {
      metadata: {
        name: 'EvaluationService#evaluateInstances',
      },
    },
    async (metadata, _otSpan) => {
      const request = {
        location: locationName,
        ...partialRequest,
      };
      metadata.input = request;
      const client = await auth.getClient();
      const response = await client.request({
        url: `https://${location}-aiplatform.googleapis.com/v1beta1/${locationName}:evaluateInstances`,
        method: 'POST',
        body: JSON.stringify(request),
      });
      metadata.output = response.data;
      return response.data as any;
    }
  );
}
