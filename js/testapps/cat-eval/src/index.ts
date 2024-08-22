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

import { configureGenkit } from '@genkit/core';
import { devLocalVectorstore } from '@genkit/dev-local-vectorstore';
import { dotprompt } from '@genkit/dotprompt';
import { genkitEval, GenkitMetric } from '@genkit/evaluator';
import { firebase } from '@genkit/firebase';
import { gemini15Pro, googleAI } from '@genkit/googleai';
import { textEmbeddingGecko, vertexAI } from '@genkit/vertexai';

// Turn off safety checks for evaluation so that the LLM as an evaluator can
// respond appropriately to potentially harmful content without error.
export const PERMISSIVE_SAFETY_SETTINGS: any = {
  safetySettings: [
    {
      category: 'HARM_CATEGORY_HATE_SPEECH',
      threshold: 'BLOCK_NONE',
    },
    {
      category: 'HARM_CATEGORY_DANGEROUS_CONTENT',
      threshold: 'BLOCK_NONE',
    },
    {
      category: 'HARM_CATEGORY_HARASSMENT',
      threshold: 'BLOCK_NONE',
    },
    {
      category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
      threshold: 'BLOCK_NONE',
    },
  ],
};

configureGenkit({
  plugins: [
    dotprompt(),
    firebase(),
    googleAI(),
    genkitEval({
      judge: gemini15Pro,
      judgeConfig: PERMISSIVE_SAFETY_SETTINGS,
      metrics: [GenkitMetric.MALICIOUSNESS],
      embedder: textEmbeddingGecko,
    }),
    vertexAI({
      location: 'us-central1',
    }),
    devLocalVectorstore([
      {
        indexName: 'pdfQA',
        embedder: textEmbeddingGecko,
      },
    ]),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});

export * from './pdf_rag.js';
export * from './setup.js';
