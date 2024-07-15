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

import { retrieve } from '@genkit-ai/ai/retriever';
import { configureGenkit } from '@genkit-ai/core';
import {
  devLocalRetrieverRef, devLocalVectorstore
} from '@genkit-ai/dev-local-vectorstore';
import { defineDotprompt, dotprompt } from '@genkit-ai/dotprompt';
import { defineFlow } from '@genkit-ai/flow';
import {
  gemini15Flash,
  textEmbeddingGecko,
  vertexAI
} from '@genkit-ai/vertexai';
import * as z from 'zod';

export default configureGenkit({
  plugins: [
    dotprompt(),
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
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});

export const pdfChatRetriever = devLocalRetrieverRef('pdfQA');

// Define a simple RAG flow, we will evaluate this flow
export const pdfQA = defineFlow(
  {
    name: 'pdfQA',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (query, streamingCallback) => {
    const docs = await retrieve({
      retriever: pdfChatRetriever,
      query,
      options: { k: 3 },
    });

    return augmentedPrompt
      .generate({
        input: {
          question: query,
          context: docs.map((d) => d.text()),
        },
        streamingCallback,
      })
      .then((r) => r.text());
  }
);

// Define a prompt that includes the retrieved context documents

export const augmentedPrompt = defineDotprompt(
  {
    name: 'augmentedPrompt',
    model: gemini15Flash,
    input: z.object({
      context: z.array(z.string()),
      question: z.string(),
    }),
    output: {
      format: 'text',
    },
  },
  `
Use the following context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
{{#each context}}
  - {{this}}
{{/each}}

Question: {{question}}
Helpful Answer:
`
);
