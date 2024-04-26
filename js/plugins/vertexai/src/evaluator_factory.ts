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
import { Action } from '@genkit-ai/core';
import { runInNewSpan } from '@genkit-ai/core/tracing';
import { GoogleAuth } from 'google-auth-library';
import { JSONClient } from 'google-auth-library/build/src/auth/googleauth';
import { VertexAIEvaluationMetricType } from './evaluation';

export class EvaluatorFactory {
  constructor(
    private readonly auth: GoogleAuth<JSONClient>,
    private readonly location: string,
    private readonly projectId: string
  ) {}

  create(
    config: {
      metric: VertexAIEvaluationMetricType;
      displayName: string;
      definition: string;
    },
    toRequest: (datapoint: BaseDataPoint) => any,
    responseHandler: (response: any, datapoint: BaseDataPoint) => any
  ): Action {
    return defineEvaluator(
      {
        name: `vertexai/${config.metric.toLocaleLowerCase()}`,
        displayName: config.displayName,
        definition: config.displayName,
      },
      async (datapoint: BaseDataPoint) => {
        const response = await this.evaluateInstances(toRequest(datapoint));

        return responseHandler(response, datapoint);
      }
    );
  }

  async evaluateInstances(partialRequest: any) {
    const locationName = `projects/${this.projectId}/locations/${this.location}`;
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
        const client = await this.auth.getClient();
        const response = await client.request({
          url: `https://${this.location}-aiplatform.googleapis.com/v1beta1/${locationName}:evaluateInstances`,
          method: 'POST',
          body: JSON.stringify(request),
        });
        metadata.output = response.data;
        return response.data as any;
      }
    );
  }
}
