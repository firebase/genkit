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

//  Sample app for using the proposed Vertex AI plugin retriever and indexer with a local file (just as a demo).

import { configureGenkit } from '@genkit-ai/core';
import { defineFlow, startFlowsServer } from '@genkit-ai/flow';
// important imports for this sample:
import { Document } from '@genkit-ai/ai/retriever';
import { vertexAI } from '@genkit-ai/vertexai';
// // Environment variables set with dotenv for simplicity of sample
import { rerank } from '@genkit-ai/ai/reranker';
import { z } from 'zod';
import { LOCATION, PROJECT_ID } from './config';

// Configure Genkit with Vertex AI plugin
configureGenkit({
  plugins: [
    vertexAI({
      projectId: PROJECT_ID,
      location: LOCATION,
      googleAuth: {
        scopes: ['https://www.googleapis.com/auth/cloud-platform'],
      },
      rerankOptions: [
        {
          model: 'vertexai/semantic-ranker-512',
        },
      ],
    }),
  ],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});
const FAKE_DOCUMENT_CONTENT = [
  'pythagorean theorem',
  'e=mc^2',
  'pi',
  'dinosaurs',
  "euler's identity",
  'prime numbers',
  'fourier transform',
  'ABC conjecture',
  'riemann hypothesis',
  'triangles',
  "schrodinger's cat",
  'quantum mechanics',
  'the avengers',
  "harry potter and the philosopher's stone",
  'movies',
];

export const rerankFlow = defineFlow(
  {
    name: 'rerankFlow',
    inputSchema: z.object({ query: z.string() }),
    outputSchema: z.array(
      z.object({
        text: z.string(),
        score: z.number(),
      })
    ),
  },
  async ({ query }) => {
    const documents = FAKE_DOCUMENT_CONTENT.map((text) =>
      Document.fromText(text)
    );
    const reranker = 'vertexai/reranker';

    const rerankedDocuments = await rerank({
      reranker,
      query: Document.fromText(query),
      documents,
    });

    return rerankedDocuments.map((doc) => ({
      text: doc.text(),
      score: doc.metadata.score,
    }));
  }
);

startFlowsServer();
