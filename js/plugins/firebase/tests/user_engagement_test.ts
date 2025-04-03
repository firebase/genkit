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

import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { SPAN_TYPE_ATTR, appendSpan } from 'genkit/tracing';
import {
  FirebaseUserAcceptanceEnum,
  FirebaseUserEngagementSchema,
  FirebaseUserFeedbackEnum,
  collectUserEngagement,
} from '../src/user-engagement';

jest.mock('genkit/tracing');

describe('User Engagement', () => {
  const labels = { [SPAN_TYPE_ATTR]: 'userEngagement' };
  const baseInput = {
    name: 'flow_name',
    traceId: 'trace1',
    spanId: 'span1',
  };

  beforeEach(async () => {
    jest.resetAllMocks();
  });

  it('handles user feedback', async () => {
    await collectUserEngagement(
      FirebaseUserEngagementSchema.parse({
        ...baseInput,
        feedback: {
          value: FirebaseUserFeedbackEnum.POSITIVE,
          text: 'great feature!',
        },
      })
    );

    expect(appendSpan as jest.Mock).toHaveBeenCalledWith(
      'trace1',
      'span1',
      {
        name: 'user-feedback',
        path: '/{flow_name}',
        metadata: {
          feedbackValue: FirebaseUserFeedbackEnum.POSITIVE,
          subtype: 'userFeedback',
          textFeedback: 'great feature!',
        },
      },
      labels
    );
  });

  it('handles user acceptance', async () => {
    await collectUserEngagement(
      FirebaseUserEngagementSchema.parse({
        ...baseInput,
        acceptance: {
          value: FirebaseUserAcceptanceEnum.REJECTED,
        },
      })
    );

    expect(appendSpan as jest.Mock).toHaveBeenCalledWith(
      'trace1',
      'span1',
      {
        name: 'user-acceptance',
        path: '/{flow_name}',
        metadata: {
          acceptanceValue: FirebaseUserAcceptanceEnum.REJECTED,
          subtype: 'userAcceptance',
        },
      },
      labels
    );
  });

  it('handles multiple engagement types', async () => {
    await collectUserEngagement(
      FirebaseUserEngagementSchema.parse({
        ...baseInput,
        acceptance: {
          value: FirebaseUserAcceptanceEnum.REJECTED,
        },
        feedback: {
          value: FirebaseUserFeedbackEnum.NEGATIVE,
        },
      })
    );

    expect(appendSpan as jest.Mock).toHaveBeenCalledTimes(2);
  });

  it('skips empty input', async () => {
    await collectUserEngagement(FirebaseUserEngagementSchema.parse(baseInput));

    expect(appendSpan as jest.Mock).not.toHaveBeenCalled();
  });
});
