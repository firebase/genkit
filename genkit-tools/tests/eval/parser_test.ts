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

import { describe, expect, it } from '@jest/globals';
import {
  EvalMetricSchema,
  EvalResult,
  enrichResultsWithScoring,
} from '../../src/eval';
import { EvaluatorResponse } from '../../src/types/evaluators';

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

  const evaluatorOutput: Record<string, EvaluatorResponse> = {
    '/evaluator/ragas/faithfulness': [
      {
        testCaseId: 'case1',
        sampleIndex: 0,
        evaluation: {
          score: 1,
          details: {
            reasoning: 'It looks good to me!',
          },
        },
      },
      {
        testCaseId: 'case2',
        sampleIndex: 1,
        evaluation: {
          score: 1,
          details: {
            reasoning: 'I thought the LLM did a very nice job',
          },
        },
      },
    ],
    '/evaluator/ragas/context_relevancy': [
      {
        testCaseId: 'case1',
        sampleIndex: 0,
        evaluation: {
          score: 1,
          details: {
            reasoning: 'Context was utilized.',
          },
        },
      },
      {
        testCaseId: 'case2',
        sampleIndex: 0,
        evaluation: {
          score: 1,
          details: {
            reasoning: 'Context was utilized.',
          },
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
