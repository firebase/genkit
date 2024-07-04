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

// main.ts
import {
  Document,
  DocumentDataSchema,
  index,
  retrieve,
} from '@genkit-ai/ai/retriever';
import { configureGenkit } from '@genkit-ai/core';
import { defineFlow, startFlowsServer } from '@genkit-ai/flow';
import {
  DocumentIndexer,
  DocumentRetriever,
  Neighbor,
  vertexAI,
  vertexAiIndexerRef,
  vertexAiRetrieverRef,
} from '@genkit-ai/vertexai';
import { BigQuery } from '@google-cloud/bigquery';
import { initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import * as z from 'zod';

import {
  DATASET_ID,
  FIREBASE_COLLECTION,
  LOCATION,
  PROJECT_ID,
  TABLE_ID,
  VECTOR_SEARCH_DEPLOYED_INDEX_ID,
  VECTOR_SEARCH_INDEX_ENDPOINT_ID,
  VECTOR_SEARCH_INDEX_ID,
  VECTOR_SEARCH_PUBLIC_ENDPOINT,
} from './config';

// Initialize Firebase app
initializeApp({ projectId: PROJECT_ID });

const db = getFirestore();

const bigQuery = new BigQuery({
  projectId: PROJECT_ID,
  location: LOCATION,
});

const generateId = (): string => {
  return Math.random().toString(36).substring(2, 15);
};

// Firestore Document Retriever
const firestoreRetriever = async (
  neighbors: Neighbor[]
): Promise<Document[]> => {
  const docs: Document[] = [];
  for (const neighbor of neighbors) {
    const docRef = db
      .collection(FIREBASE_COLLECTION)
      .doc(neighbor.datapoint?.datapointId!);
    const docSnapshot = await docRef.get();

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
const firestoreIndexer = async (docs: Document[]): Promise<string[]> => {
  const batch = db.batch();
  const ids: string[] = [];
  docs.forEach((doc) => {
    const docRef = db.collection(FIREBASE_COLLECTION).doc();
    batch.set(docRef, { content: doc.content });
    ids.push(docRef.id);
  });
  await batch.commit();
  return ids;
};

// BigQuery Document Retriever
const bigQueryRetriever = async (
  neighbors: Neighbor[]
): Promise<Document[]> => {
  const docs: Document[] = [];
  for (const neighbor of neighbors) {
    const query = `
      SELECT * FROM \`${DATASET_ID}.${TABLE_ID}\`
      WHERE id = @id
      LIMIT 1
    `;
    const options = {
      query,
      params: { id: neighbor.datapoint?.datapointId },
    };
    const [rows] = await bigQuery.query(options);
    for (const row of rows) {
      const docData = {
        content: JSON.parse(row.content),
        metadata: { ...neighbor },
      };
      const parsedDocData = DocumentDataSchema.safeParse(docData);
      if (parsedDocData.success) {
        docs.push(new Document(parsedDocData.data));
      }
    }
  }
  return docs;
};

// BigQuery Document Indexer
const bigQueryIndexer = async (docs: Document[]): Promise<string[]> => {
  const ids: string[] = [];
  const rows = docs.map((doc) => {
    const id = generateId();
    ids.push(id);
    return { id, content: JSON.stringify(doc.content) };
  });
  await bigQuery.dataset(DATASET_ID).table(TABLE_ID).insert(rows);
  return ids;
};

// Combined Document Retriever
const combinedRetriever: DocumentRetriever<{
  k?: number;
  source: 'firestore' | 'bigquery' | 'both';
}> = async (neighbors, options): Promise<Document[]> => {
  switch (options?.source) {
    case 'firestore':
      return firestoreRetriever(neighbors);
    case 'bigquery':
      return bigQueryRetriever(neighbors);
    case 'both':
      const firestoreResults = await firestoreRetriever(neighbors);
      const bigQueryResults = await bigQueryRetriever(neighbors);
      const firestoreResultsWithSource = firestoreResults.map((doc) => {
        doc.metadata = { ...doc.metadata, source: 'firestore' };
        return doc;
      });
      const bigQueryResultsWithSource = bigQueryResults.map((doc) => {
        doc.metadata = { ...doc.metadata, source: 'bigquery' };
        return doc;
      });
      return [...firestoreResultsWithSource, ...bigQueryResultsWithSource];
    default:
      throw new Error(
        'Invalid source, choose ONE of firestore, bigquery or both'
      );
  }
};

// Combined Document Indexer
const combinedIndexer: DocumentIndexer<{
  target: 'firestore' | 'bigquery';
}> = async (docs: Document[], options): Promise<string[]> => {
  switch (options?.target) {
    case 'firestore':
      return firestoreIndexer(docs);
    case 'bigquery':
      return bigQueryIndexer(docs);
    default:
      throw new Error('Invalid target, choose ONE of firestore or bigquery');
  }
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
          documentRetriever: combinedRetriever,
          documentIndexer: combinedIndexer,
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
      target: z.enum(['firestore', 'bigquery']),
    }),
    outputSchema: z.any(),
  },
  async ({ texts, target }) => {
    const documents = texts.map((text) => Document.fromText(text));
    await index({
      indexer: vertexAiIndexerRef({
        indexId: VECTOR_SEARCH_INDEX_ID,
        displayName: 'test_index',
      }),
      options: { target },
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
      source: z.enum(['firestore', 'bigquery', 'both']),
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
  async ({ query, k, source }) => {
    const startTime = performance.now();
    const queryDocument = Document.fromText(query);
    const res = await retrieve({
      retriever: vertexAiRetrieverRef({
        indexId: VECTOR_SEARCH_INDEX_ID,
        displayName: 'test_index',
      }),
      query: queryDocument,
      options: { source, k },
    });
    const endTime = performance.now();
    return {
      result: res
        .map((doc) => ({
          text: doc.content[0].text!,
          source: doc.metadata?.source ?? source,
          distance: doc.metadata?.distance,
        }))
        .sort((a, b) => b.distance - a.distance),
      length: res.length,
      time: endTime - startTime,
    };
  }
);

startFlowsServer();
