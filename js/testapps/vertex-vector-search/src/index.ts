import { configureGenkit } from '@genkit-ai/core';
import { defineFlow, startFlowsServer } from '@genkit-ai/flow';
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

import {
  Document,
  DocumentDataSchema,
  index,
  retrieve,
} from '@genkit-ai/ai/retriever';
import {
  Neighbor,
  vertexAI,
  vertexAiIndexerRef,
  vertexAiRetrieverRef,
} from '@genkit-ai/vertexai';

import { initializeApp } from 'firebase-admin/app';

initializeApp({
  projectId: 'fir-vector-invertase-03',
});

import { getFirestore } from 'firebase-admin/firestore';

const db = getFirestore();

// Define the Firestore client to handle the storage and retrieval of Document objects (as an example).

// In this case, since Firestore could be out of sync with the Vertex AI index, we only return successfully retrieved documents from firestore.
// It would be up to the user to decide how to handle syncronization between Firestore and the Vertex AI index.

const firestoreClient = {
  get: async (neighbors: Neighbor[]): Promise<Document[]> => {
    const docs: Document[] = [];

    for (const neighbor of neighbors) {
      const docRef = db
        .collection('documents')
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
  },

  add: async (docs: Document[]): Promise<string[]> => {
    const batch = db.batch();
    const ids: string[] = [];

    docs.forEach((doc) => {
      const docRef = db.collection('documents').doc();
      batch.set(docRef, { content: doc.content });
      ids.push(docRef.id);
    });

    await batch.commit();
    return ids;
  },
};

configureGenkit({
  plugins: [
    vertexAI({
      projectId: 'fir-vector-invertase-03',
      location: 'us-central1',
      googleAuth: {
        scopes: ['https://www.googleapis.com/auth/cloud-platform'],
      },
      // projectNumber: '67051307990',
      vectorSearchIndexOptions: [
        {
          // embedder: 'textEmbeddingGecko',
          // TODO rename this to publicEndpointHostname (?)
          publicEndpoint:
            'https://1394123153.us-central1-67051307990.vdb.vertexai.goog',
          // TODO: do we need this or can we get it from the SDK/REST API?
          indexEndpointId: '2682724808889729024',
          // TODO: do we need this or can we get it from the SDK/REST API?
          indexId: '3629325155567665152',
          // TODO: do we need this or can we get it from the SDK/REST API?
          deployedIndexId: 'testt_1719838497234',
          documentRetriever: firestoreClient.get,
          documentIndexer: firestoreClient.add,
        },
      ],
    }),
  ],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});

export const indexFlow = defineFlow(
  {
    name: 'indexFlow',
    inputSchema: z.array(z.string()),
    outputSchema: z.any(),
  },
  async (texts) => {
    const documents = texts.map((text) => Document.fromText(text));

    await index({
      indexer: vertexAiIndexerRef({
        indexId: '3629325155567665152',
        displayName: 'test_index',
      }),
      documents,
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
  async (query) => {
    const queryDocument = Document.fromText(query);

    const res = await retrieve({
      retriever: vertexAiRetrieverRef({
        indexId: '3629325155567665152',
        displayName: 'test_index',
      }),
      query: queryDocument,
    });

    return {
      result: res,
    };
  }
);

// export const logFakeDataStoreContents = defineFlow(
//   {
//     name: 'logFakeDataStoreContents',
//     inputSchema: z.any(),
//     outputSchema: z.any(),
//   },
//   async () => {
//     console.log(firestoreClient);
//     return fakeDocStore;
//   }
// );

// the code below does not work as the methods are not implemented....

// const matchClient = new MatchServiceClient({
//   projectId: 'fir-vector-invertase-03',
//   location: 'us-central1',
//   apiEndpoint: 'us-central1-aiplatform.googleapis.com',
//   auth: new GoogleAuth({
//     scopes: ['https://www.googleapis.com/auth/cloud-platform'],
//   }),
// });

// export const clientFlow = defineFlow(
//   {
//     name: 'clientFlow',
//     inputSchema: z.any(),
//     outputSchema: z.any(),
//   },
//   async () => {
//     const res = await matchClient.findNeighbors({
//       deployedIndexId: 'genkit_test_1719476368682',
//       indexEndpoint: `projects/67051307990/locations/us-central1/indexEndpoints/2682724808889729024`,
//       returnFullDatapoint: true,
//       queries: [
//         {
//           datapoint: {
//             featureVector: Array.from({ length: 768 }, () => 1),
//             datapointId: '0',
//           },
//           neighborCount: 2,
//         },
//       ],
//     });

//     if (!res) {
//       throw new Error('No response from match client');
//     }
//     if (!res[0]) {
//       throw new Error('No response from match client');
//     }

//     return JSON.stringify(res, null, 2);
//   }
// );
startFlowsServer();
