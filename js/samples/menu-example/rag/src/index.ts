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

import { configureGenkit } from '@genkit-ai/core';
import { devLocalVectorstore } from '@genkit-ai/dev-local-vectorstore';
import { defineFlow, runFlow } from '@genkit-ai/flow';
import { textEmbeddingGecko, vertexAI } from '@genkit-ai/vertexai';
import * as z from 'zod';
import { indexMenu } from './indexer';

configureGenkit({
  plugins: [
    vertexAI(),
    devLocalVectorstore([
      {
        indexName: 'menuQA',
        embedder: textEmbeddingGecko,
      },
    ]),
  ],
  enableTracingAndMetrics: true,
  flowStateStore: 'firebase',
  logLevel: 'debug',
  traceStore: 'firebase',
});

const menus = ['./docs/GenkitGrubPub.pdf'];

// genkit flow:run setup
// genkit flow:run setup '[\"your_awesome_pdf.pdf\", \"your_other_awesome_pdf.pdf\""]'
export const setup = defineFlow(
  {
    name: 'setup',
    inputSchema: z.array(z.string()).optional(),
  },
  async (documentArr?: string[]) => {
    if (!documentArr) {
      documentArr = menus;
    } else {
      documentArr.concat(menus);
    }

    await Promise.all(
      documentArr.map(async (document) => {
        console.log(`Indexed ${document}`);
        return runFlow(indexMenu, document);
      })
    );
  }
);

export * from './indexer.js';
export * from './menuQA.js';
