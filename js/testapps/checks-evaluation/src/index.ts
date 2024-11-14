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
import { checks, ChecksEvaluationMetricType } from '@genkit-ai/checks';
import { genkit } from 'genkit';

export const ai = genkit({
  plugins: [
    checks({
      // Project to charge quota to.
      // Note: If your credentials have a quota project associated with them.
      //       That value will take precedence over this.
      projectId: 'your-project-id',
      evaluation: {
        metrics: [
          // Policies configured with the default threshold.
          ChecksEvaluationMetricType.DANGEROUS_CONTENT,
          ChecksEvaluationMetricType.HARASSMENT,
          ChecksEvaluationMetricType.HATE_SPEECH,
          ChecksEvaluationMetricType.MEDICAL_INFO,
          ChecksEvaluationMetricType.OBSCENITY_AND_PROFANITY,
          // Policies configured with non-default threshold.
          {
            type: ChecksEvaluationMetricType.PII_SOLICITING_RECITING,
            threshold: 0.6,
          },
          {
            type: ChecksEvaluationMetricType.SEXUALLY_EXPLICIT,
            threshold: 0.3,
          },
          {
            type: ChecksEvaluationMetricType.VIOLENCE_AND_GORE,
            threshold: 0.55,
          },
        ],
      },
    }),
  ],
});
