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

import { getProjectId } from '@genkit-ai/core';
import { configureGenkit } from '@genkit-ai/core/config';
import { chroma } from '@genkit-ai/plugin-chroma';
import { devLocalVectorstore } from '@genkit-ai/plugin-dev-local-vectorstore';
import { firebase } from '@genkit-ai/plugin-firebase';
import { googleGenAI } from '@genkit-ai/plugin-google-genai';
import { openAI } from '@genkit-ai/plugin-openai';
import { pinecone } from '@genkit-ai/plugin-pinecone';
import { ragas, RagasMetric } from '@genkit-ai/plugin-ragas';
import {
  geminiPro,
  textEmbeddingGecko,
  vertexAI,
} from '@genkit-ai/plugin-vertex-ai';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    googleGenAI(),
    openAI(),
    ragas({
      judge: geminiPro,
      metrics: [RagasMetric.FAITHFULNESS, RagasMetric.CONTEXT_UTILIZATION],
    }),
    vertexAI({ projectId: getProjectId(), location: 'us-central1' }),
    pinecone([
      {
        indexId: 'tom-and-jerry',
        embedder: textEmbeddingGecko,
      },
      {
        indexId: 'pdf-chat',
        embedder: textEmbeddingGecko,
      },
    ]),
    chroma([
      {
        collectionName: 'spongebob_collection',
        embedder: textEmbeddingGecko,
      },
    ]),
    devLocalVectorstore([
      {
        indexName: 'spongebob-facts',
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
