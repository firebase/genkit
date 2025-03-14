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

import { initializeApp } from 'firebase-admin/app';
import { Document, genkit, z } from 'genkit';
// important imports for this sample:

import { textEmbedding004, vertexAI } from '@genkit-ai/vertexai';

import {
  DocumentIndexer,
  DocumentRetriever,
  getFirestoreDocumentIndexer,
  getFirestoreDocumentRetriever,
  vertexAiIndexerRef,
  vertexAiRetrieverRef,
  vertexAIVectorSearch,
} from '@genkit-ai/vertexai/vectorsearch';

// // Environment variables set with dotenv for simplicity of sample
import { getFirestore } from 'firebase-admin/firestore';
import {
  FIRESTORE_COLLECTION,
  LOCATION,
  PROJECT_ID,
  VECTOR_SEARCH_DEPLOYED_INDEX_ID,
  VECTOR_SEARCH_INDEX_ENDPOINT_ID,
  VECTOR_SEARCH_INDEX_ID,
  VECTOR_SEARCH_PUBLIC_DOMAIN_NAME,
} from './config';

if (
  [
    FIRESTORE_COLLECTION,
    LOCATION,
    PROJECT_ID,
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

// // Initialize Firebase app
initializeApp({ projectId: PROJECT_ID });

const db = getFirestore();

// Use our helper functions here, or define your own document retriever and document indexer
const firestoreDocumentRetriever: DocumentRetriever =
  getFirestoreDocumentRetriever(db, FIRESTORE_COLLECTION);

const firestoreDocumentIndexer: DocumentIndexer = getFirestoreDocumentIndexer(
  db,
  FIRESTORE_COLLECTION
);

// Configure Genkit with Vertex AI plugin
const ai = genkit({
  plugins: [
    vertexAI({
      projectId: PROJECT_ID,
      location: LOCATION,
      googleAuth: {
        scopes: ['https://www.googleapis.com/auth/cloud-platform'],
      },
    }),
    vertexAIVectorSearch({
      projectId: PROJECT_ID,
      location: LOCATION,
      vectorSearchOptions: [
        {
          publicDomainName: VECTOR_SEARCH_PUBLIC_DOMAIN_NAME,
          indexEndpointId: VECTOR_SEARCH_INDEX_ENDPOINT_ID,
          indexId: VECTOR_SEARCH_INDEX_ID,
          deployedIndexId: VECTOR_SEARCH_DEPLOYED_INDEX_ID,
          documentRetriever: firestoreDocumentRetriever,
          documentIndexer: firestoreDocumentIndexer,
          embedder: textEmbedding004,
        },
      ],
    }),
  ],
});

// Define indexing flow
export const indexFlow = ai.defineFlow(
  {
    name: 'indexFlow',
    inputSchema: z.object({
      datapoints: z.array(
        z.object({
          text: z.string(),
          restricts: z.optional(
            z.array(
              z.object({
                namespace: z.string(),
                allowList: z.array(z.string()),
                denyList: z.array(z.string()),
              })
            )
          ),
          numericRestricts: z.optional(
            z.array(
              z.object({
                valueInt: z.union([z.number(), z.string()]).optional(),
                valueFloat: z.number().optional(),
                valueDouble: z.number().optional(),
                namespace: z.string(),
              })
            )
          ),
        })
      ),
    }),
    outputSchema: z.any(),
  },
  async ({ datapoints }) => {
    const documents: Document[] = datapoints.map((dp) => {
      const metadata = {
        restricts: structuredClone(dp.restricts),
        numericRestricts: structuredClone(dp.numericRestricts),
      };
      return Document.fromText(dp.text, metadata);
    });
    await ai.index({
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
export const queryFlow = ai.defineFlow(
  {
    name: 'queryFlow',
    inputSchema: z.object({
      query: z.string(),
      k: z.number(),
      restricts: z.optional(
        z.array(
          z.object({
            namespace: z.string(),
            allowList: z.array(z.string()),
            denyList: z.array(z.string()),
          })
        )
      ),
      numericRestricts: z.optional(
        z.array(
          z.object({
            valueInt: z.union([z.number(), z.string()]).optional(),
            valueFloat: z.number().optional(),
            valueDouble: z.number().optional(),
            namespace: z.string(),
            op: z.enum([
              'OPERATOR_UNSPECIFIED',
              'LESS',
              'LESS_EQUAL',
              'EQUAL',
              'GREATER_EQUAL',
              'GREATER',
              'NOT_EQUAL',
            ]),
          })
        )
      ),
    }),
    outputSchema: z.object({
      result: z.array(
        z.object({
          text: z.string(),
          metadata: z.string(),
          distance: z.number(),
        })
      ),
      length: z.number(),
      time: z.number(),
    }),
  },
  async ({ query, k, restricts, numericRestricts }) => {
    const startTime = performance.now();
    const metadata = {
      restricts: structuredClone(restricts),
      numericRestricts: structuredClone(numericRestricts),
    };
    const queryDocument = Document.fromText(query, metadata);
    const res = await ai.retrieve({
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
          metadata: JSON.stringify(doc.metadata),
          distance: doc.metadata?.distance,
        }))
        .sort((a, b) => b.distance - a.distance),
      length: res.length,
      time: endTime - startTime,
    };
  }
);
