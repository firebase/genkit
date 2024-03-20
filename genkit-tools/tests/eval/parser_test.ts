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

import { describe, it, expect } from '@jest/globals';
import {
  EvalMetricSchema,
  EvalResult,
  enrichResultsWithScoring,
} from '../../src/eval';

describe('parser', () => {
  const evalRunResults: EvalResult[] = [
    {
      testCaseId: 'case1',
      input: 'Who is spongebobs best friend?',
      output: 'Patrick',
      context: [
        "Spongebob's best friend is Patrick.",
        'Spongebob has a friend named Patrick.',
        'Spongebob has a friend named Sandy.',
      ],
      metrics: [],
      traceIds: ['trace2'],
    },
    {
      testCaseId: 'case2',
      input: 'How many friends does Spongebob have?',
      output: '2',
      context: [
        "Spongebob's best friend is Patrick.",
        'Spongebob has a friend named Patrick.',
        'Spongebob has a friend named Sandy.',
      ],
      metrics: [],
      traceIds: ['trace2'],
    },
  ];

  const evaluatorOutput = {
    '/evaluator/ragas/faithfulness': [
      {
        sample: {
          input: '"Who is spongebobs best friend?"',
          output: '"Patrick"',
          context: [
            "Spongebob's best friend is Patrick.",
            'Spongebob has a friend named Patrick.',
            'Spongebob has a friend named Sandy.',
          ],
          testCaseId: 'case1',
        },
        score: {
          FAITHFULNESS: 1,
        },
      },
      {
        sample: {
          input: '"How many friends does Spongebob have?"',
          output: '"2"',
          context: [
            "Spongebob's best friend is Patrick.",
            'Spongebob has a friend named Patrick.',
            'Spongebob has a friend named Sandy.',
          ],
          testCaseId: 'case2',
        },
        score: {
          FAITHFULNESS: 1,
        },
      },
    ],
    '/evaluator/ragas/context_relevancy': [
      {
        sample: {
          input: '"Who is spongebobs best friend"',
          output: '"Patrick"',
          context: [
            "Spongebob's best friend is Patrick.",
            'Spongebob has a friend named Patrick.',
            'Spongebob has a friend named Sandy.',
          ],
          testCaseId: 'case1',
        },
        score: {
          CONTEXT_RELEVANCY: 1,
        },
      },
      {
        sample: {
          input: '"How many friends does Spongebob have?"',
          output: '"2"',
          context: [
            "Spongebob's best friend is Patrick.",
            'Spongebob has a friend named Patrick.',
            'Spongebob has a friend named Sandy.',
          ],
          testCaseId: 'case2',
        },
        score: {
          CONTEXT_RELEVANCY: 1,
        },
      },
    ],
  };

  describe('enrichResultsWithScoring', () => {
    it('Adds scoring data to eval results', () => {
      const results = enrichResultsWithScoring(evaluatorOutput, evalRunResults);
      expect(results).toHaveLength(2);
      results.forEach((result) => {
        expect(result.metrics).toMatchObject([
          EvalMetricSchema.parse({
            evaluator: '/evaluator/ragas/faithfulness',
            score: 1,
          }),
          EvalMetricSchema.parse({
            evaluator: '/evaluator/ragas/context_relevancy',
            score: 1,
          }),
        ]);
        expect(result.traceIds).toHaveLength(1);
      });
    });
  });
});
