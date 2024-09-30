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

import { ValueType } from '@opentelemetry/api';
import { GENKIT_VERSION, z } from 'genkit';
import {internalMetricNamespaceWrap, MetricCounter} from '@genkit-ai/google-cloud/metrics';
import { logger } from 'genkit/logging';


/** Explicit user sentiment of response. */
export enum FirebaseUserFeedbackEnum {
  /** The user reacted positively to the response. */
  POSITIVE = 'positive',
  /** The user reacted negatively to the response. */
  NEGATIVE = 'negative',
}

/** Implicit user acceptance of response. */
export enum FirebaseUserAcceptanceEnum {
  /** The user took the desired action. */
  ACCEPTED = 'accepted',
  /** The user did not take the desired action. */
  REJECTED = 'rejected',
}

/** Explicit user feedback on response. */
export const FirebaseUserFeedbackSchema = z.object({
  /** User sentiment of response. */
  value: z.nativeEnum(FirebaseUserFeedbackEnum),
  /** Optional free text feedback to supplement score. */
  text: z.optional(z.string()),
});

/** Implicit user acceptance of response. */
export const FirebaseUserAcceptanceSchema = z.object({
  /** Whether the user took the desired action based on the response. */
  value: z.nativeEnum(FirebaseUserAcceptanceEnum),
});

/** Schema for providing user engagement metadata. One or both of feedback and acceptance should be provided. */
export const FirebaseUserEngagementSchema = z.object({
  /** Flow or feature name. */
  name: z.string(),
  /**
   * The trace ID of the execution for which we've received user engagement data.
   */
  traceId: z.string(),
  /** The root span ID of the execution for which we've received user engagement data. */
  spanId: z.string(),
  /** Explicit user feedback on response. */
  feedback: z.optional(FirebaseUserFeedbackSchema),
  /** Implicit user acceptance of response. */
  acceptance: z.optional(FirebaseUserAcceptanceSchema),
});

/** Associates user engagement metadata with the specified flow execution. */
export async function collectUserEngagement(
  userEngagement: z.infer<typeof FirebaseUserEngagementSchema>
) {
  if (userEngagement.feedback) {
    console.log('COLLECTING USER FEEDBACK');

    // TODO: include trace id somehow?
    const dimensions = {
      feedback_value: userEngagement.feedback.value,
    };
    if (userEngagement.feedback.text) {
      dimensions['feedback_text'] = userEngagement.feedback.text;
    }
    logger.logStructured(`Feedback[/${userEngagement.name}]`, dimensions);

    // const dimensions = {
    //   value: userEngagement.feedback.value,
    //   name: userEngagement.name,
    //   source: 'ts',
    //   sourceVersion: GENKIT_VERSION
    // }
    // feedbackCounter.add(1, dimensions);
  }

  if (userEngagement.acceptance) {
    console.log('COLLECTING USER ACCEPTANCE');

    // TODO: include trace id somehow?
    const dimensions = {
      acceptance_value: userEngagement.acceptance.value,
    };
    logger.logStructured(`Acceptance[/${userEngagement.name}]`, dimensions);

    // TODO
    // const dimensions = {
    //   value: userEngagement.acceptance.value,
    //   name: userEngagement.name,
    //   source: 'ts',
    //   sourceVersion: GENKIT_VERSION
    // }
    // acceptanceCounter.add(1, dimensions);
  }

  console.log(`COLLECTED: ${JSON.stringify(userEngagement)}`);
}

// /**
//  * Wraps the declared metrics in a Genkit-specific, internal namespace.
//  */
// const _N = internalMetricNamespaceWrap.bind(null, 'engagement');
//
// // TODO: Move counters into CLoud plugin, tick when it sees a feedback span
// const feedbackCounter = new MetricCounter(_N('feedback'), {
//   description: 'Counts feedback received for Genkit features.',
//   valueType: ValueType.INT,
// });
//
// const acceptanceCounter = new MetricCounter(_N('acceptance'), {
//   description: 'Counts feedback received for Genkit features.',
//   valueType: ValueType.INT,
// });
