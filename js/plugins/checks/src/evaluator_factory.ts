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

import { Action, Genkit, GENKIT_CLIENT_HEADER, z } from 'genkit';
import { BaseEvalDataPoint, Score } from 'genkit/evaluator';
import { runInNewSpan } from 'genkit/tracing';
import { GoogleAuth } from 'google-auth-library';
import { ChecksEvaluationMetricType } from './evaluation.js';

export class EvaluatorFactory {
  constructor(
    private readonly auth: GoogleAuth,
    private readonly location: string,
    private readonly projectId: string
  ) { }

  create<ResponseType extends z.ZodTypeAny>(
    ai: Genkit,
    config: {
      metric: ChecksEvaluationMetricType;
      displayName: string;
      definition: string;
      responseSchema: ResponseType;
    },
    toRequest: (datapoint: BaseEvalDataPoint) => any,
    responseHandler: (response: z.infer<ResponseType>) => Score
  ): Action {
    return ai.defineEvaluator(
      {
        name: `checks/${config.metric.toLocaleLowerCase()}`,
        displayName: config.displayName,
        definition: config.definition,
      },
      async (datapoint: BaseEvalDataPoint) => {
        const responseSchema = config.responseSchema;
        let response;

        response = await this.checksEvalInstance(
          toRequest(datapoint),
          responseSchema
        );


        return {
          evaluation: responseHandler(response),
          testCaseId: datapoint.testCaseId,
        };
      }
    );
  }


  async checksEvalInstance<ResponseType extends z.ZodTypeAny>(
    partialRequest: any,
    responseSchema: ResponseType
  ): Promise<z.infer<ResponseType>> {

    console.log('HSH::partialRequest: ', partialRequest)
    return await runInNewSpan(
      {
        metadata: {
          name: 'EvaluationService#evaluateInstances',
        },
      },
      async (metadata, _otSpan) => {
        const request = {
          ...partialRequest,
        };

        console.log("HSH::request: ", request)

        /**
          gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/checks
          
          curl -X POST https://checks.googleapis.com/v1alpha/aisafety:classifyContent \
               -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
               -H "X-Goog-User-Project: checks-api-370419" \
               -H "Content-Type: application/json" \
               -d '{ \
                     "input": { \
                       "text_input": { \
                         "content": "I hate you and all people on earth" \
                       } \
                     }, \
                     "policies": { "policy_type": "HARASSMENT" } \
                   }'\
         */

        metadata.input = request;
        const client = await this.auth.getClient();
        const url = "https://checks.googleapis.com/v1alpha/aisafety:classifyContent"

        const response = await client.request({
          url,
          method: "POST",
          body: JSON.stringify(request),
          headers: {
            "X-Goog-User-Project": "checks-api-370419",
            "Content-Type": "application/json",
          }
        })
        metadata.output = response.data;

        console.log("HSH::response: ", response)
        console.log("HSH::response.data: ", response.data)

        // console.log("HSH::response: ", response)
        // console.log("HSH::metadata: ", metadata)

        try {
          return responseSchema.parse(response.data);
        } catch (e) {
          throw new Error(`Error parsing ${url} API response: ${e}`);
        }
      }
    );
  }
}
