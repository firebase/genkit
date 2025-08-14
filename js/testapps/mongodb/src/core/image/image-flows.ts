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

import { multimodalEmbedding001 } from '@genkit-ai/vertexai';
import { Document } from 'genkit';
import { mongoIndexerRef, mongoRetrieverRef } from 'genkitx-mongodb';
import {
  MONGODB_DB_NAME,
  MONGODB_IMAGE_COLLECTION_NAME,
} from '../../common/config.js';
import { ai } from '../../common/genkit.js';
import {
  ImageIndexInputSchema,
  ImageIndexOutputSchema,
  ImageRetrieveInputSchema,
  ImageRetrieveOutputSchema,
} from '../../common/types.js';
import { getBase64Data } from '../../common/utils.js';

const dbName = MONGODB_DB_NAME;
const collectionName = MONGODB_IMAGE_COLLECTION_NAME;
const embedder = multimodalEmbedding001;

export const imageIndexerFlow = ai.defineFlow(
  {
    name: 'Image - Indexer Flow',
    inputSchema: ImageIndexInputSchema,
    outputSchema: ImageIndexOutputSchema,
  },
  async (input) => {
    for (const { name, description } of input) {
      const imageData = await getBase64Data('image', name + '.jpg');

      const documents = [
        Document.fromMedia(imageData, 'image/jpeg', { name, description }),
      ];

      await ai.index({
        indexer: mongoIndexerRef('indexer'),
        documents,
        options: {
          dbName,
          collectionName,
          embeddingField: 'embedding',
          batchSize: 50,
          embedder,
          skipData: true,
          dataTypeField: 'imageType',
          metadataField: 'imageMetadata',
        },
      });
    }

    return {
      answer: `Indexed ${input.length} images`,
    };
  }
);

export const imageRetrieverFlow = ai.defineFlow(
  {
    name: 'Image - Retrieve Flow',
    inputSchema: ImageRetrieveInputSchema,
    outputSchema: ImageRetrieveOutputSchema,
  },
  async (input) => {
    const { name } = input;

    const imageData = await getBase64Data('image', name + '.jpg');
    const document = Document.fromMedia(imageData, 'image/jpeg');

    const docs = await ai.retrieve({
      retriever: mongoRetrieverRef('retriever'),
      query: document,
      options: {
        dbName,
        collectionName,
        embedder,
        vectorSearch: {
          index: 'image_vector_index',
          path: 'embedding',
          exact: false,
          numCandidates: 10,
          limit: 2,
        },
        dataTypeField: 'imageType',
        metadataField: 'imageMetadata',
      },
    });

    return docs.map((doc) => ({
      name: doc.metadata?.name,
      description: doc.metadata?.description,
    }));
  }
);
