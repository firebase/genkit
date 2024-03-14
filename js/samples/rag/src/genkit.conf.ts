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

import { getProjectId } from '@genkit-ai/common';
import { configureGenkit } from '@genkit-ai/common/config';
import { googleGenAI } from '@genkit-ai/plugin-google-genai';
import { firebase } from '@genkit-ai/plugin-firebase';
import { pinecone } from '@genkit-ai/plugin-pinecone';
import { geminiPro, vertexAI } from '@genkit-ai/plugin-vertex-ai';
import { chroma } from '@genkit-ai/plugin-chroma';
import { RagasMetric, ragas } from '@genkit-ai/plugin-ragas';
import {
  googleVertexAI,
  textEmbeddingGecko001,
} from '@genkit-ai/providers/google-vertexai';
import { gpt4, openAI } from '@genkit-ai/plugin-openai';
import { devLocalVectorstore } from '@genkit-ai/plugin-dev-local-vectorstore';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    googleGenAI(),
    googleVertexAI(),
    openAI(),
    ragas({ judge: gpt4, metrics: [RagasMetric.FAITHFULNESS] }),
    vertexAI({ projectId: getProjectId(), location: 'us-central1' }),
    pinecone([
      {
        indexId: 'tom-and-jerry',
        embedder: textEmbeddingGecko001,
        embedderOptions: { temperature: 0 },
      },
      {
        indexId: 'pdf-chat',
        embedder: textEmbeddingGecko001,
        embedderOptions: { temperature: 0 },
      },
    ]),
    chroma([
      {
        collectionName: 'spongebob_collection',
        embedder: textEmbeddingGecko001,
        embedderOptions: { temperature: 0 },
      },
    ]),
    devLocalVectorstore([
      {
        indexName: 'spongebob-facts',
        embedder: textEmbeddingGecko001,
        embedderOptions: { temperature: 0 },
      },
      {
        indexName: 'pdfQA',
        embedder: textEmbeddingGecko001,
        embedderOptions: { temperature: 0 },
      },
    ]),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
