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
import { genkitEval, GenkitMetric } from '@genkit-ai/evaluator';
import { firebase } from '@genkit-ai/firebase';
import { googleAI } from '@genkit-ai/googleai';
import {
  claude3Sonnet,
  geminiPro,
  textEmbeddingGecko,
  vertexAI,
} from '@genkit-ai/vertexai';
import { chroma } from 'genkitx-chromadb';
import { langchain } from 'genkitx-langchain';
import { pinecone } from 'genkitx-pinecone';

export default configureGenkit({
  plugins: [
    firebase(),
    googleAI(),
    genkitEval({
      judge: geminiPro,
      metrics: [GenkitMetric.FAITHFULNESS, GenkitMetric.MALICIOUSNESS],
    }),
    langchain({
      evaluators: {
        criteria: ['coherence'],
        labeledCriteria: ['correctness'],
        judge: geminiPro,
      },
    }),
    vertexAI({
      location: 'us-central1',
      modelGardenModels: [claude3Sonnet],
    }),
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
