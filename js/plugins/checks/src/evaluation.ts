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
      case ChecksEvaluationMetricType.DANGEROUS_CONTENT: {
        return createDangerousContentEvaluator(ai, factory, metricSpec)
      }
      case ChecksEvaluationMetricType.PII_SOLICITING_RECITING: {
        return createPiiSolicitingEvaluator(ai, factory, metricSpec)
      }
      case ChecksEvaluationMetricType.HARASSMENT: {
        return createHarassmentEvaluator(ai, factory, metricSpec)
      }
      case ChecksEvaluationMetricType.SEXUALLY_EXPLICIT: {
        return createSexuallyExplicitEvaluator(ai, factory, metricSpec)
      }
      case ChecksEvaluationMetricType.HATE_SPEECH: {
        return createHateSpeachEvaluator(ai, factory, metricSpec)
      }
      case ChecksEvaluationMetricType.MEDICAL_INFO: {
        return createMedicalInfoEvaluator(ai, factory, metricSpec)
      }
      case ChecksEvaluationMetricType.VIOLENCE_AND_GORE: {
        return createViolenceAndGoreEvaluator(ai, factory, metricSpec)
      }
      case ChecksEvaluationMetricType.OBSCENITY_AND_PROFANITY: {
        return createObscenityAndProfanityEvaluator(ai, factory, metricSpec)
      }
    }
  });
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
      violationResult: z.string()
    })
  )
});

function createDangerousContentEvaluator(
  ai: Genkit,
  factory: EvaluatorFactory,
  metricSpec: any
): Action {
  return factory.create(
    ai,
    {
      metric: ChecksEvaluationMetricType.DANGEROUS_CONTENT,
      displayName: 'Dangerous Content',
      definition: 'Assesses the text constittues dangerous content.',
      responseSchema: ResponseSchema,
    },
    (datapoint) => {
      return {
        input: {
          text_input: {
            content: datapoint.output as string
          },
        },
        policies: {
          policy_type: "DANGEROUS_CONTENT",
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

function createPiiSolicitingEvaluator(
  ai: Genkit,
  factory: EvaluatorFactory,
  metricSpec: any
): Action {
  return factory.create(
    ai,
    {
      metric: ChecksEvaluationMetricType.PII_SOLICITING_RECITING,
      displayName: 'PII soliciting reciting',
      definition: 'Assesses the text constittues PII solicitation.',
      responseSchema: ResponseSchema,
    },
    (datapoint) => {
      return {
        input: {
          text_input: {
            content: datapoint.output as string
          },
        },
        policies: {
          policy_type: "PII_SOLICITING_RECITING",
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
      responseSchema: ResponseSchema,
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

function createSexuallyExplicitEvaluator(
  ai: Genkit,
  factory: EvaluatorFactory,
  metricSpec: any
): Action {
  return factory.create(
    ai,
    {
      metric: ChecksEvaluationMetricType.SEXUALLY_EXPLICIT,
      displayName: 'Sexually explicit',
      definition: 'Assesses the text is sexually explicit.',
      responseSchema: ResponseSchema,
    },
    (datapoint) => {
      return {
        input: {
          text_input: {
            content: datapoint.output as string
          },
        },
        policies: {
          policy_type: "SEXUALLY_EXPLICIT",
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

function createHateSpeachEvaluator(
  ai: Genkit,
  factory: EvaluatorFactory,
  metricSpec: any
): Action {
  return factory.create(
    ai,
    {
      metric: ChecksEvaluationMetricType.HATE_SPEECH,
      displayName: 'Sexually explicit',
      definition: 'Assesses the text is sexually explicit.',
      responseSchema: ResponseSchema,
    },
    (datapoint) => {
      return {
        input: {
          text_input: {
            content: datapoint.output as string
          },
        },
        policies: {
          policy_type: "HATE_SPEECH",
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

function createMedicalInfoEvaluator(
  ai: Genkit,
  factory: EvaluatorFactory,
  metricSpec: any
): Action {
  return factory.create(
    ai,
    {
      metric: ChecksEvaluationMetricType.MEDICAL_INFO,
      displayName: 'Sexually explicit',
      definition: 'Assesses the text is sexually explicit.',
      responseSchema: ResponseSchema,
    },
    (datapoint) => {
      return {
        input: {
          text_input: {
            content: datapoint.output as string
          },
        },
        policies: {
          policy_type: "MEDICAL_INFO",
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

function createViolenceAndGoreEvaluator(
  ai: Genkit,
  factory: EvaluatorFactory,
  metricSpec: any
): Action {
  return factory.create(
    ai,
    {
      metric: ChecksEvaluationMetricType.VIOLENCE_AND_GORE,
      displayName: 'Sexually explicit',
      definition: 'Assesses the text is sexually explicit.',
      responseSchema: ResponseSchema,
    },
    (datapoint) => {
      return {
        input: {
          text_input: {
            content: datapoint.output as string
          },
        },
        policies: {
          policy_type: "VIOLENCE_AND_GORE",
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

function createObscenityAndProfanityEvaluator(
  ai: Genkit,
  factory: EvaluatorFactory,
  metricSpec: any
): Action {
  return factory.create(
    ai,
    {
      metric: ChecksEvaluationMetricType.OBSCENITY_AND_PROFANITY,
      displayName: 'Sexually explicit',
      definition: 'Assesses the text is sexually explicit.',
      responseSchema: ResponseSchema,
    },
    (datapoint) => {
      return {
        input: {
          text_input: {
            content: datapoint.output as string
          },
        },
        policies: {
          policy_type: "OBSCENITY_AND_PROFANITY",
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


