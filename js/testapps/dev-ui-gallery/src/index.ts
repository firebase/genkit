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
import { dotprompt } from '@genkit-ai/dotprompt';
import { genkitEval, GenkitMetric } from '@genkit-ai/evaluator';
import { firebase } from '@genkit-ai/firebase';
import { geminiPro, googleAI } from '@genkit-ai/googleai';
import {
  claude3Haiku,
  claude3Opus,
  claude3Sonnet,
  textEmbeddingGecko,
  vertexAI,
  VertexAIEvaluationMetricType,
} from '@genkit-ai/vertexai';
import { chroma } from 'genkitx-chromadb';
import { ollama } from 'genkitx-ollama';
import { pinecone } from 'genkitx-pinecone';

// Turn off safety checks for evaluation so that the LLM as an evaluator can
// respond appropriately to potentially harmful content without error.
export const PERMISSIVE_SAFETY_SETTINGS: any = {
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
};

export default configureGenkit({
  // settings
  flowStateStore: 'firebase',
  logLevel: 'debug',
  traceStore: 'firebase',

  // load at least one plugin representing each action type
  plugins: [
    // runtime
    firebase(),

    // model providers
    googleAI({
      apiVersion: ['v1', 'v1beta'],
    }),
    ollama({
      models: [
        { name: 'llama2' },
        { name: 'llama3' },
        {
          name: 'gemma',
          type: 'generate',
        },
      ],
      serverAddress: 'http://127.0.0.1:11434', // default local address
    }),
    vertexAI({
      location: 'us-central1',
      modelGardenModels: [claude3Haiku, claude3Sonnet, claude3Opus],
      evaluation: {
        metrics: [
          VertexAIEvaluationMetricType.BLEU,
          VertexAIEvaluationMetricType.GROUNDEDNESS,
          VertexAIEvaluationMetricType.SAFETY,
          {
            type: VertexAIEvaluationMetricType.ROUGE,
            metricSpec: {
              rougeType: 'rougeLsum',
              useStemmer: true,
              splitSummaries: 'true',
            },
          },
        ],
      },
    }),

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
    genkitEval({
      judge: geminiPro,
      judgeConfig: PERMISSIVE_SAFETY_SETTINGS,
      embedder: textEmbeddingGecko,
      metrics: [
        GenkitMetric.ANSWER_RELEVANCY,
        GenkitMetric.FAITHFULNESS,
        GenkitMetric.MALICIOUSNESS,
      ],
    }),

    // prompt files
    dotprompt({ dir: './prompts' }),
  ],
});

export * from './main/flows-durable.js';
export * from './main/flows-firebase-functions.js';
export * from './main/flows.js';
export * from './main/prompts.js';
export * from './main/tools.js';
