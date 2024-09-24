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

import { devLocalVectorstore } from '@genkit-ai/dev-local-vectorstore';
import { genkitEval, GenkitMetric } from '@genkit-ai/evaluator';
import { firebase } from '@genkit-ai/firebase';
import { googleAI } from '@genkit-ai/googleai';
import {
  claude3Sonnet,
  geminiPro,
  llama31,
  textEmbeddingGecko,
  vertexAI,
} from '@genkit-ai/vertexai';
import { dotprompt, genkit } from 'genkit';
import { chroma } from 'genkitx-chromadb';
import { langchain } from 'genkitx-langchain';
import { pinecone } from 'genkitx-pinecone';
import { GoogleAuth, IdTokenClient } from 'google-auth-library';

const auth = new GoogleAuth();
let authClient: IdTokenClient | undefined = undefined;

/** Helper method to cache {@link IdTokenClient} instance */
async function getCloudRunAuthClient(aud: string) {
  if (!authClient) {
    authClient = await auth.getIdTokenClient(aud);
  }
  return authClient;
}

export const ai = genkit({
  plugins: [
    dotprompt(),
    firebase(),
    googleAI({ apiVersion: ['v1'] }),
    genkitEval({
      judge: geminiPro,
      judgeConfig: {
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
      } as any,
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
      modelGarden: {
        models: [claude3Sonnet, llama31],
      },
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
        createCollectionIfMissing: true,
        clientParams: async () => {
          // Replace this with your Cloud Run Instance URL
          const host = 'https://<my-cloud-run-url>.run.app';
          const client = await getCloudRunAuthClient(host);
          const idToken = await client.idTokenProvider.fetchIdToken(host);
          return {
            path: host,
            fetchOptions: {
              headers: {
                Authorization: 'Bearer ' + idToken,
              },
            },
          };
        },
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
  defaultModel: {
    name: geminiPro,
    config: {
      temperature: 0.6,
    },
  },
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});

export * from './pdf_rag.js';
export * from './simple_rag.js';
