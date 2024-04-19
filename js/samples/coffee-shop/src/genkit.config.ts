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

// plugins
import { chroma } from '@genkit-ai/chromadb';
import { devLocalVectorstore } from '@genkit-ai/dev-local-vectorstore';
import { firebase } from '@genkit-ai/firebase';
import { geminiPro, googleAI } from '@genkit-ai/googleai';
import { ollama } from '@genkit-ai/ollama';
import { openAI } from '@genkit-ai/openai';
import { pinecone } from '@genkit-ai/pinecone';
import { RagasMetric, ragas } from '@genkit-ai/ragas';
import { textEmbeddingGecko, vertexAI } from '@genkit-ai/vertexai';

// Not all plugins configured below are used by the flow, but we load
// "everything" for UI development and testing.
export default configureGenkit({
  plugins: [
    // plugins
    googleAI(),
    openAI(),
    vertexAI(),
    ragas({ judge: geminiPro, metrics: [RagasMetric.FAITHFULNESS] }),

    // providers - will be moved to plugins eventually
    chroma([
      {
        collectionName: 'chroma-collection',
        embedder: textEmbeddingGecko,
        embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
      },
    ]),
    firebase(),
    devLocalVectorstore([
      {
        indexName: 'naive-index',
        embedder: textEmbeddingGecko,
        embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
      },
    ]),
    ollama({
      models: [{ name: 'llama2' }],
      serverAddress: 'http://127.0.0.1:11434', // default local address
    }),
    pinecone([
      {
        indexId: 'pinecone-index',
        embedder: textEmbeddingGecko,
        embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
      },
    ]),
  ],
  enableTracingAndMetrics: true,
  flowStateStore: 'firebase',
  logLevel: 'debug',
  traceStore: 'firebase',
});
