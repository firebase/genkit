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
import { geminiPro, googleAI } from '@genkit-ai/googleai';
import { ollama } from '@genkit-ai/ollama';
import { pinecone } from '@genkit-ai/pinecone';
import { RagasMetric, ragas } from '@genkit-ai/ragas';
import { textEmbeddingGecko, vertexAI } from '@genkit-ai/vertexai';

export default configureGenkit({
  // settings
  enableTracingAndMetrics: true,
  flowStateStore: 'firebase',
  logLevel: 'debug',
  traceStore: 'firebase',

  // load at least one plugin representing each action type
  plugins: [
    // runtime
    firebase(),

    // model providers
    googleAI({
      apiVersion: 'v1beta', // enables Gemini 1.5
    }),
    ollama({
      models: [{ name: 'llama2' }],
      serverAddress: 'http://127.0.0.1:11434', // default local address
    }),
    vertexAI(),

    // vector stores
    chroma([
      {
        collectionName: 'chroma-collection',
        embedder: textEmbeddingGecko,
        embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
      },
    ]),
    devLocalVectorstore([
      {
        indexName: 'naive-index',
        embedder: textEmbeddingGecko,
        embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
      },
    ]),
    pinecone([
      {
        indexId: 'pinecone-index',
        embedder: textEmbeddingGecko,
        embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
      },
    ]),

    // evaluation
    ragas({
      judge: geminiPro,
      embedder: textEmbeddingGecko,
      metrics: [
        RagasMetric.ANSWER_RELEVANCY,
        RagasMetric.FAITHFULNESS,
        RagasMetric.MALICIOUSNESS,
      ],
    }),
  ],
});
