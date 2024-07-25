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

//  Sample app for using the proposed Vertex AI plugin retriever and indexer with BigQuery.

import { configureGenkit } from '@genkit-ai/core';
import { defineFlow, startFlowsServer } from '@genkit-ai/flow';
// important imports for this sample:
import {
  getBigQueryDocumentIndexer,
  getBigQueryDocumentRetriever,
  vertexAI,
  vertexAiIndexerRef,
  vertexAiRetrieverRef,
  type DocumentIndexer,
  type DocumentRetriever,
} from '@genkit-ai/vertexai';
import { z } from 'zod';

// // Environment variables set with dotenv for simplicity of sample
import { Document, index, retrieve } from '@genkit-ai/ai/retriever';
import {
  BIGQUERY_DATASET,
  BIGQUERY_TABLE,
  LOCATION,
  PROJECT_ID,
  VECTOR_SEARCH_DEPLOYED_INDEX_ID,
  VECTOR_SEARCH_INDEX_ENDPOINT_ID,
  VECTOR_SEARCH_INDEX_ID,
  VECTOR_SEARCH_PUBLIC_DOMAIN_NAME,
} from './config';

if (
  [
    LOCATION,
    PROJECT_ID,
    BIGQUERY_TABLE,
    BIGQUERY_DATASET,
    VECTOR_SEARCH_DEPLOYED_INDEX_ID,
    VECTOR_SEARCH_INDEX_ENDPOINT_ID,
    VECTOR_SEARCH_INDEX_ID,
    VECTOR_SEARCH_PUBLIC_DOMAIN_NAME,
  ].some((envVar) => !envVar)
) {
  throw new Error(
    'Missing environment variables. Please check your .env file.'
  );
}

import { BigQuery } from '@google-cloud/bigquery';

const bq = new BigQuery({
  projectId: PROJECT_ID,
});

const bigQueryDocumentRetriever: DocumentRetriever =
  getBigQueryDocumentRetriever(bq, BIGQUERY_TABLE, BIGQUERY_DATASET);

const bigQueryDocumentIndexer: DocumentIndexer = getBigQueryDocumentIndexer(
  bq,
  BIGQUERY_TABLE,
  BIGQUERY_DATASET
);

// Configure Genkit with Vertex AI plugin
configureGenkit({
  plugins: [
    vertexAI({
      projectId: PROJECT_ID,
      location: LOCATION,
      googleAuth: {
        scopes: ['https://www.googleapis.com/auth/cloud-platform'],
      },
      vectorSearchIndexOptions: [
        {
          publicDomainName: VECTOR_SEARCH_PUBLIC_DOMAIN_NAME,
          indexEndpointId: VECTOR_SEARCH_INDEX_ENDPOINT_ID,
          indexId: VECTOR_SEARCH_INDEX_ID,
          deployedIndexId: VECTOR_SEARCH_DEPLOYED_INDEX_ID,
          documentRetriever: bigQueryDocumentRetriever,
          documentIndexer: bigQueryDocumentIndexer,
        },
      ],
    }),
  ],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});

// // Define indexing flow
export const indexFlow = defineFlow(
  {
    name: 'indexFlow',
    inputSchema: z.object({
      texts: z.array(z.string()),
    }),
    outputSchema: z.any(),
  },
  async ({ texts }) => {
    const documents = texts.map((text) => Document.fromText(text));
    await index({
      indexer: vertexAiIndexerRef({
        indexId: VECTOR_SEARCH_INDEX_ID,
        displayName: 'firestore_index',
      }),
      documents,
    });
    return { result: 'success' };
  }
);

// Define query flow
export const queryFlow = defineFlow(
  {
    name: 'queryFlow',
    inputSchema: z.object({
      query: z.string(),
      k: z.number(),
    }),
    outputSchema: z.object({
      result: z.array(
        z.object({
          text: z.string(),
          distance: z.number(),
        })
      ),
      length: z.number(),
      time: z.number(),
    }),
  },
  async ({ query, k }) => {
    const startTime = performance.now();
    const queryDocument = Document.fromText(query);
    const res = await retrieve({
      retriever: vertexAiRetrieverRef({
        indexId: VECTOR_SEARCH_INDEX_ID,
        displayName: 'firestore_index',
      }),
      query: queryDocument,
      options: { k },
    });
    const endTime = performance.now();
    return {
      result: res
        .map((doc) => ({
          text: doc.content[0].text!,
          distance: doc.metadata?.distance,
        }))
        .sort((a, b) => b.distance - a.distance),
      length: res.length,
      time: endTime - startTime,
    };
  }
);

startFlowsServer();
