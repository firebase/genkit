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

import { chroma } from '@genkit-ai/chromadb';
import { configureGenkit } from '@genkit-ai/core';
import { devLocalVectorstore } from '@genkit-ai/dev-local-vectorstore';
import { firebase } from '@genkit-ai/firebase';
import { googleAI } from '@genkit-ai/googleai';
import { openAI } from '@genkit-ai/openai';
import { pinecone } from '@genkit-ai/pinecone';
import { ragas, RagasMetric } from '@genkit-ai/ragas';
import { geminiPro, textEmbeddingGecko, vertexAI } from '@genkit-ai/vertexai';

export default configureGenkit({
  plugins: [
    firebase(),
    googleAI(),
    openAI(),
    ragas({
      judge: geminiPro,
      metrics: [RagasMetric.FAITHFULNESS, RagasMetric.MALICIOUSNESS],
    }),
    vertexAI(),
    pinecone([
      {
        indexId: 'cat-facts',
        embedder: textEmbeddingGecko,
      },
      {
        indexId: 'pdf-chat',
        embedder: textEmbeddingGecko,
      },
    ]),
    chroma([
      {
        collectionName: 'dogfacts_collection',
        embedder: textEmbeddingGecko,
      },
    ]),
    devLocalVectorstore([
      {
        indexName: 'dog-facts',
        embedder: textEmbeddingGecko,
      },
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
