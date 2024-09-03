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

import {
  Dataset,
  EvalResponse,
  EvalResponseSchema,
  evaluate,
} from '@genkit-ai/ai/evaluator';
import { configureGenkit } from '@genkit-ai/core';
import { GenkitMetric, genkitEval, genkitEvalRef } from '@genkit-ai/evaluator';
import { firebase } from '@genkit-ai/firebase';
import { defineFlow } from '@genkit-ai/flow';
import { geminiPro, textEmbeddingGecko, vertexAI } from '@genkit-ai/vertexai';
import * as z from 'zod';

export default configureGenkit({
  plugins: [
    firebase(),
    vertexAI(),
    genkitEval({
      judge: geminiPro,
      metrics: [
        GenkitMetric.FAITHFULNESS,
        GenkitMetric.ANSWER_RELEVANCY,
        GenkitMetric.MALICIOUSNESS,
      ],
      embedder: textEmbeddingGecko,
    }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  logLevel: 'debug',
});

// Run this flow to execute the evaluator on the test dataset.

const samples: Dataset = require('../data/dogfacts.json');

export const dogFactsEvalFlow = defineFlow(
  {
    name: 'dogFactsEval',
    inputSchema: z.void(),
    outputSchema: z.array(EvalResponseSchema),
  },
  async (): Promise<Array<EvalResponse>> => {
    return await evaluate({
      evaluator: genkitEvalRef(GenkitMetric.FAITHFULNESS),
      dataset: samples,
    });
  }
);
