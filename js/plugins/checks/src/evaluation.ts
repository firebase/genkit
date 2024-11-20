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

import { EvaluatorAction, Genkit, z } from 'genkit';
import { BaseEvalDataPoint } from 'genkit/evaluator';
import { runInNewSpan } from 'genkit/tracing';
import { GoogleAuth } from 'google-auth-library';
import { ChecksEvaluationMetric, ChecksEvaluationMetricConfig, ChecksEvaluationMetricType, isConfig } from './metrics';


export function checksEvaluators(
  ai: Genkit,
  auth: GoogleAuth,
  metrics: ChecksEvaluationMetric[],
  projectId: string
): EvaluatorAction[] {
  const policy_configs: ChecksEvaluationMetricConfig[] = metrics.map(
    (metric) => {
      const metricType = isConfig(metric) ? metric.type : metric;
      const threshold = isConfig(metric) ? metric.threshold : undefined;

      return {
        type: metricType,
        threshold,
      };
    }
  );

  const evaluators = policy_configs.map((policy_config) => {
    return createPolicyEvaluator(projectId, auth, ai, policy_config);
  });

  return evaluators;
}



const ResponseSchema = z.object({
  policyResults: z.array(
    z.object({
      policyType: z.string(),
      score: z.number(),
      violationResult: z.string(),
    })
  ),
});

function createPolicyEvaluator(
  projectId: string,
  auth: GoogleAuth,
  ai: Genkit,
  policy_config: ChecksEvaluationMetricConfig
): EvaluatorAction {
  const policyType = policy_config.type as string;

  return ai.defineEvaluator(
    {
      name: `checks/${policyType.toLowerCase()}`,
      displayName: policyType,
      definition: `Evaluates text against the Checks ${policyType} policy.`,
    },
    async (datapoint: BaseEvalDataPoint) => {
      const partialRequest = {
        input: {
          text_input: {
            content: datapoint.output as string,
          },
        },
        policies: {
          policy_type: policy_config.type,
          threshold: policy_config.threshold,
        },
      };

      const response = await checksEvalInstance(
        projectId,
        auth,
        partialRequest,
        ResponseSchema
      );

      return {
        evaluation: {
          score: response.policyResults[0].score,
          details: {
            reasoning: response.policyResults[0].violationResult,
          },
        },
        testCaseId: datapoint.testCaseId,
      };
    }
  );
}

async function checksEvalInstance<ResponseType extends z.ZodTypeAny>(
  projectId: string,
  auth: GoogleAuth,
  partialRequest: any,
  responseSchema: ResponseType
): Promise<z.infer<ResponseType>> {
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

      metadata.input = request;
      const client = await auth.getClient();
      const url =
        'https://checks.googleapis.com/v1alpha/aisafety:classifyContent';

      const response = await client.request({
        url,
        method: 'POST',
        body: JSON.stringify(request),
        headers: {
          'x-goog-user-project': projectId,
          'Content-Type': 'application/json',
        },
      });
      metadata.output = response.data;

      try {
        return responseSchema.parse(response.data);
      } catch (e) {
        throw new Error(`Error parsing ${url} API response: ${e}`);
      }
    }
  );
}
