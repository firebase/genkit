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

/**
 * Currently supported Checks AI Safety policies.
 */
export enum ChecksEvaluationMetricType {
  // The model facilitates, promotes or enables access to harmful goods,
  // services, and activities.
  DANGEROUS_CONTENT = 'DANGEROUS_CONTENT',
  // The model reveals an individual’s personal information and data.
  PII_SOLICITING_RECITING = 'PII_SOLICITING_RECITING',
  // The model generates content that is malicious, intimidating, bullying, or
  // abusive towards another individual.
  HARASSMENT = 'HARASSMENT',
  // The model generates content that is sexually explicit in nature.
  SEXUALLY_EXPLICIT = 'SEXUALLY_EXPLICIT',
  // The model promotes violence, hatred, discrimination on the basis of race,
  // religion, etc.
  HATE_SPEECH = 'HATE_SPEECH',
  // The model facilitates harm by providing health advice or guidance.
  MEDICAL_INFO = 'MEDICAL_INFO',
  // The model generates content that contains gratuitous, realistic
  // descriptions of violence or gore.
  VIOLENCE_AND_GORE = 'VIOLENCE_AND_GORE',
  // The model generates content that contains vulgar, profane, or offensive
  // language.
  OBSCENITY_AND_PROFANITY = 'OBSCENITY_AND_PROFANITY',
}

/**
 * Checks evaluation metric config. Use `threshold` to override the default violation threshold.
 * The value of `metricSpec` will be included in the request to the API. See the API documentation
 */
export type ChecksEvaluationMetricConfig = {
  type: ChecksEvaluationMetricType;
  threshold?: number;
};

export type ChecksEvaluationMetric =
  | ChecksEvaluationMetricType
  | ChecksEvaluationMetricConfig;

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

  // Individual evaluators, one per configured metric.
  const evaluators = policy_configs.map((policy_config) => {
    return createPolicyEvaluator(projectId, auth, ai, [policy_config], policy_config.type as string);
  });

  // Single evaluator instnace with all configured policies.
  evaluators.push(createPolicyEvaluator(projectId, auth, ai, policy_configs, "all_policies"))

  return evaluators;
}

function isConfig(
  config: ChecksEvaluationMetric
): config is ChecksEvaluationMetricConfig {
  return (config as ChecksEvaluationMetricConfig).type !== undefined;
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
  policy_config: ChecksEvaluationMetricConfig[],
  name: string,
): EvaluatorAction {

  return ai.defineEvaluator(
    {
      name: `checks/${name.toLowerCase()}`,
      displayName: name,
      definition: `Evaluates text against the Checks ${name} policy.`,
    },
    async (datapoint: BaseEvalDataPoint) => {
      const partialRequest = {
        input: {
          text_input: {
            content: datapoint.output as string,
          },
        },
        policies: policy_config.map(config => {
          return {
            policy_type: config.type,
            threshold: config.threshold,
          }
        }),
      };

      const response = await checksEvalInstance(
        projectId,
        auth,
        partialRequest,
        ResponseSchema
      );

      const evaluationResults = response.policyResults.map(result => {
        return {
          id: result.policyType,
          score: result.score,
          details: {
            reasoning: `Status ${result.violationResult}`,
          },
        }
      });

      return {
        evaluation: evaluationResults,
        testCaseId: datapoint.testCaseId
      }
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
