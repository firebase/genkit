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

//  Sample app for using the proposed Vertex AI plugin retriever and indexer with a local file (just as a demo).

import { Document, genkit, z } from 'genkit';
// important imports for this sample:
import {
  vertexAI,
  vertexAiIndexerRef,
  vertexAiRetrieverRef,
  type DocumentIndexer,
  type DocumentRetriever,
  type Neighbor,
} from '@genkit-ai/vertexai';

// // Environment variables set with dotenv for simplicity of sample
import {
  LOCAL_DIR,
  LOCATION,
  PROJECT_ID,
  VECTOR_SEARCH_DEPLOYED_INDEX_ID,
  VECTOR_SEARCH_INDEX_ENDPOINT_ID,
  VECTOR_SEARCH_INDEX_ID,
  VECTOR_SEARCH_PUBLIC_DOMAIN_NAME,
} from './config';

if (
  [
    LOCAL_DIR,
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

import * as fs from 'fs';
import * as path from 'path';

const localFilePath = path.posix.join(LOCAL_DIR, 'documents.json');

// make file if it doesn't exist
if (!fs.existsSync(localFilePath)) {
  fs.writeFileSync(localFilePath, '{}');
}

const generateRandomId = () => Math.random().toString(36).substring(7);

// These are just examples to demonstrate how to define a custom document indexer and retriever.
// Don't use these in production obviously, they simply store documents in a local JSON file.
const localDocumentIndexer: DocumentIndexer = async (documents: Document[]) => {
  try {
    const content = await fs.promises.readFile(localFilePath, 'utf-8');
    const currentLocalFile = JSON.parse(content);

    const docsWithIds = Object.fromEntries(
      documents.map((doc) => [
        generateRandomId(),
        { content: JSON.stringify(doc.content) },
      ])
    );

    const newLocalFile = { ...currentLocalFile, ...docsWithIds };

    try {
      await fs.promises.writeFile(
        localFilePath,
        JSON.stringify(newLocalFile, null, 2)
      );
      return Object.keys(docsWithIds);
    } catch (writeError) {
      console.error('Error writing file:', writeError);
      throw writeError;
    }
  } catch (readError) {
    console.error('Error reading file:', readError);
    throw readError;
  }
};

const localDocumentRetriever: DocumentRetriever = async (
  neighbors: Neighbor[]
) => {
  try {
    const content = await fs.promises.readFile(localFilePath, 'utf-8');
    const currentLocalFile = JSON.parse(content);
    const ids = neighbors
      .map((neighbor) => neighbor.datapoint?.datapointId)
      .filter(Boolean) as string[];

    const docs = ids
      .map((id) => {
        const doc = currentLocalFile[id];

        if (!doc || !doc.content) {
          console.error(`No content found for ID: ${id}`);
          return null;
        }

        try {
          const parsedContent = JSON.parse(doc.content);
          const text = parsedContent[0]?.text;

          if (text) {
            return Document.fromText(text);
          } else {
            console.error(`No text found in content for ID: ${id}`);
            return null;
          }
        } catch (error) {
          console.error(`Error parsing content for ID: ${id}`, error);
          return null;
        }
      })
      .filter(Boolean) as Document[];

    return docs;
  } catch (error) {
    console.error('Error reading file:', error);
    throw error;
  }
};

// Configure Genkit with Vertex AI plugin
const ai = genkit({
  plugins: [
    vertexAI({
      projectId: PROJECT_ID,
      location: LOCATION,
      googleAuth: {
        scopes: ['https://www.googleapis.com/auth/cloud-platform'],
      },
      vectorSearchOptions: [
        {
          publicDomainName: VECTOR_SEARCH_PUBLIC_DOMAIN_NAME,
          indexEndpointId: VECTOR_SEARCH_INDEX_ENDPOINT_ID,
          indexId: VECTOR_SEARCH_INDEX_ID,
          deployedIndexId: VECTOR_SEARCH_DEPLOYED_INDEX_ID,
          documentRetriever: localDocumentRetriever,
          documentIndexer: localDocumentIndexer,
        },
      ],
    }),
  ],
  flowServer: true,
});

// // Define indexing flow
export const indexFlow = ai.defineFlow(
  {
    name: 'indexFlow',
    inputSchema: z.object({
      texts: z.array(z.string()),
    }),
    outputSchema: z.any(),
  },
  async ({ texts }) => {
    const documents = texts.map((text) => Document.fromText(text));
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
          distance: doc.metadata?.distance,
        }))
        .sort((a, b) => b.distance - a.distance),
      length: res.length,
      time: endTime - startTime,
    };
  }
);
