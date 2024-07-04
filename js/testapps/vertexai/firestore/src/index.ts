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

//  Sample app for using the proposed Vertex AI plugin retriever and indexer with Firestore.

//  NOTE: This particular uses Firestore as the document store, but the plugin is unopinionated about the document store.

import {
  Document,
  DocumentDataSchema,
  index,
  retrieve,
} from '@genkit-ai/ai/retriever';
import { configureGenkit } from '@genkit-ai/core';
import { defineFlow, startFlowsServer } from '@genkit-ai/flow';
// important imports for this sample:
import {
  DocumentIndexer,
  DocumentRetriever,
  Neighbor,
  vertexAI,
  vertexAiIndexerRef,
  vertexAiRetrieverRef,
} from '@genkit-ai/vertexai';
import { initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import * as z from 'zod';

// Environment variables set with dotenv for simplicity of sample
import {
  FIRESTORE_COLLECTION,
  LOCATION,
  PROJECT_ID,
  VECTOR_SEARCH_DEPLOYED_INDEX_ID,
  VECTOR_SEARCH_INDEX_ENDPOINT_ID,
  VECTOR_SEARCH_INDEX_ID,
  VECTOR_SEARCH_PUBLIC_ENDPOINT,
} from './config';

if (
  [
    FIRESTORE_COLLECTION,
    LOCATION,
    PROJECT_ID,
    VECTOR_SEARCH_DEPLOYED_INDEX_ID,
    VECTOR_SEARCH_INDEX_ENDPOINT_ID,
    VECTOR_SEARCH_INDEX_ID,
    VECTOR_SEARCH_PUBLIC_ENDPOINT,
  ].some((envVar) => !envVar)
) {
  throw new Error(
    'Missing environment variables. Please check your .env file.'
  );
}

// Initialize Firebase app
initializeApp({ projectId: PROJECT_ID });

const db = getFirestore();

// Firestore Document Retriever
const firestoreRetriever: DocumentRetriever = async (
  neighbors: Neighbor[]
): Promise<Document[]> => {
  const docs: Document[] = [];
  for (const neighbor of neighbors) {
    const docRef = db
      .collection(FIRESTORE_COLLECTION)
      .doc(neighbor.datapoint?.datapointId!);
    const docSnapshot = await docRef.get();

    // If this retriever fails to retrieve a document from a given id, it will not be included in the results.
    // We could have included a placeholder document with an error message, but for simplicity we are just ignoring it.
    // We could change it so DocumentRetriever returns a Promise.allSettled instead. The current behavior keeps types simpler though.
    if (docSnapshot.exists) {
      const docData = { ...docSnapshot.data(), metadata: { ...neighbor } };
      const parsedDocData = DocumentDataSchema.safeParse(docData);
      if (parsedDocData.success) {
        docs.push(new Document(parsedDocData.data));
      }
    }
  }
  return docs;
};

// Firestore Document Indexer
const firestoreIndexer: DocumentIndexer = async (
  docs: Document[]
): Promise<string[]> => {
  const batch = db.batch();
  const ids: string[] = [];
  docs.forEach((doc) => {
    const docRef = db.collection(FIRESTORE_COLLECTION).doc();
    batch.set(docRef, { content: doc.content });
    ids.push(docRef.id);
  });
  await batch.commit();
  return ids;
};

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
          publicEndpoint: VECTOR_SEARCH_PUBLIC_ENDPOINT,
          indexEndpointId: VECTOR_SEARCH_INDEX_ENDPOINT_ID,
          indexId: VECTOR_SEARCH_INDEX_ID,
          deployedIndexId: VECTOR_SEARCH_DEPLOYED_INDEX_ID,
          documentRetriever: firestoreRetriever,
          documentIndexer: firestoreIndexer,
        },
      ],
    }),
  ],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});

// Define indexing flow
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
        displayName: 'test_index',
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
          source: z.string(),
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
        displayName: 'test_index',
      }),
      query: queryDocument,
      options: { client: 'firestore', k },
    });
    const endTime = performance.now();
    return {
      result: res
        .map((doc) => ({
          text: doc.content[0].text!,
          source: 'firestore',
          distance: doc.metadata?.distance,
        }))
        .sort((a, b) => b.distance - a.distance),
      length: res.length,
      time: endTime - startTime,
    };
  }
);

startFlowsServer();
