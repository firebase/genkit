import { configureGenkit } from '@genkit-ai/core';
import { defineFlow, startFlowsServer } from '@genkit-ai/flow';
import { GoogleAuth } from 'google-auth-library';
import * as z from 'zod';
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

import { ModelReference } from '@genkit-ai/ai/model';
import { Document, index, retrieve } from '@genkit-ai/ai/retriever';
import {
  vertexAI,
  vertexAiIndexerRef,
  vertexAiRetrieverRef,
} from '@genkit-ai/vertexai';
import { GoogleAuthOptions } from 'google-auth-library';

configureGenkit({
  plugins: [
    vertexAI({
      projectId: 'fir-vector-invertase-03',
      location: 'us-central1',
      googleAuth: {
        scopes: ['https://www.googleapis.com/auth/cloud-platform'],
      },
      vectorSearchOptions: {
        projectNumber: '67051307990',
        publicEndpoint:
          'https://1394123153.us-central1-67051307990.vdb.vertexai.goog',
        indexEndpointId: '2682724808889729024',
        indexId: '8639016791063920640',
        documentRetriever: async (docIds) => {
          return [];
        },
        documentIndexer: async (docs) => {
          return;
        },
        documentIdField: 'id',
        deployedIndexId: 'genkit_test_1719476368682',
      },
    }),
  ],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});

export interface PluginOptions {
  /** The Google Cloud project id to call. */
  projectId?: string;
  /** The Google Cloud region to call. */
  location: string;
  /** Provide custom authentication configuration for connecting to Vertex AI. */
  googleAuth?: GoogleAuthOptions;
  /** Configure Vertex AI evaluators */
  // evaluation?: {
  //   metrics: VertexAIEvaluationMetric[];
  // };
  modelGardenModels?: ModelReference<any>[];
  vectorSearchOptions?: {
    projectNumber: string;
    deployedIndexId: string;
    indexEndpointId: string;
    documentRetriever: (docIds: string[]) => Promise<Document[]>;
    documentIndexer: (docs: Document[]) => Promise<void>;
    documentIdField: string;
    indexId: string;
    publicEndpoint: string;
  };
}

export const indexFlow = defineFlow(
  {
    name: 'indexFlow',
    inputSchema: z.string(),
    outputSchema: z.any(),
  },
  async (subject) => {
    const auth = new GoogleAuth({
      scopes: ['https://www.googleapis.com/auth/cloud-platform'],
    });

    const randomId = Math.floor(Math.random() * 1000000);

    const datapoint = {
      datapointId: randomId.toString(),
      // array of 1s of length 768
      featureVector: Array.from({ length: 768 }, () => 1),
    };

    await index({
      indexer: vertexAiIndexerRef({
        indexId: '8639016791063920640',
        displayName: 'test_index',
      }),
      documents: [datapoint].map((d) => ({
        content: [
          {
            text: subject,
          },
        ],
        metadata: {
          id: d.datapointId,
        },
      })),
    });

    return {
      result: 'success',
    };
  }
);

export const queryFlow = defineFlow(
  {
    name: 'queryFlow',
    inputSchema: z.string(),
    outputSchema: z.any(),
  },
  async (subject) => {
    const res = await retrieve({
      retriever: vertexAiRetrieverRef({
        indexId: '8639016791063920640',
        displayName: 'test_index',
      }),
      query: {
        content: [
          {
            text: subject,
          },
        ],
      },
    });

    return {
      result: res,
    };
  }
);

startFlowsServer();
