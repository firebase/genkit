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

import { googleAI } from '@genkit-ai/googleai';
import { Document, z } from 'genkit';
import { mongoIndexerRef, mongoRetrieverRef } from 'genkitx-mongodb';
import {
  MONGODB_COLLECTION_NAME,
  MONGODB_DB_NAME,
} from '../../common/config.js';
import { ai } from '../../common/genkit.js';
import {
  AnswerOutputSchema,
  MenuItem,
  MenuItemSchema,
  QuestionInputSchema,
} from '../../common/types.js';
import { menuPrompt } from './menu-prompts.js';

const embedder = googleAI.embedder('text-embedding-004');

export const menuIndexerFlow = ai.defineFlow(
  {
    name: 'Menu - Indexer Flow',
    inputSchema: z.array(MenuItemSchema),
    outputSchema: AnswerOutputSchema,
  },
  async (menuItems) => {
    const documents = menuItems.map((menuItem) => {
      const text = `${menuItem.description}`;
      return Document.fromText(text, menuItem);
    });

    await ai.index({
      indexer: mongoIndexerRef('indexer'),
      documents,
      options: {
        dbName: MONGODB_DB_NAME,
        collectionName: MONGODB_COLLECTION_NAME,
        embeddingField: 'embedding',
        batchSize: 5,
        embedder,
        skipData: true,
        dataTypeField: 'menuItemType',
        metadataField: 'menuItemMetadata',
      },
    });
    return { answer: `Indexed ${menuItems.length} menu items` };
  }
);

export const menuRetrieveVectorFlow = ai.defineFlow(
  {
    name: 'Menu - Retrieve Vector Flow',
    inputSchema: QuestionInputSchema,
    outputSchema: AnswerOutputSchema,
  },
  async (input) => {
    const docs = await ai.retrieve({
      retriever: mongoRetrieverRef('retriever'),
      query: input.question,
      options: {
        dbName: MONGODB_DB_NAME,
        collectionName: MONGODB_COLLECTION_NAME,
        embedder,
        vectorSearch: {
          index: 'item_vector_index',
          path: 'embedding',
          exact: false,
          numCandidates: 10,
          limit: 3,
        },
        dataTypeField: 'menuItemType',
        metadataField: 'menuItemMetadata',
      },
    });

    const menuData: Array<MenuItem> = docs.map(
      (doc) => (doc.metadata || {}) as MenuItem
    );

    const response = await menuPrompt({
      menuData: menuData,
      question: input.question,
    });
    return { answer: response.text };
  }
);

export const menuRetrieveTextFlow = ai.defineFlow(
  {
    name: 'Menu - Retrieve Text Flow',
    inputSchema: QuestionInputSchema,
    outputSchema: AnswerOutputSchema,
  },
  async (input) => {
    const docs = await ai.retrieve({
      retriever: mongoRetrieverRef('retriever'),
      query: input.question,
      options: {
        dbName: MONGODB_DB_NAME,
        collectionName: MONGODB_COLLECTION_NAME,
        search: {
          index: 'item_search_index',
          text: {
            path: 'menuItemMetadata.title',
            fuzzy: {
              maxEdits: 2,
              prefixLength: 0,
              maxExpansions: 50,
            },
          },
        },
        dataTypeField: 'menuItemType',
        metadataField: 'menuItemMetadata',
        pipelines: [{ $limit: 3 }],
      },
    });

    const menuData: Array<MenuItem> = docs.map(
      (doc) => (doc.metadata || {}) as MenuItem
    );

    const response = await menuPrompt({
      menuData: menuData,
      question: input.question,
    });
    return { answer: response.text };
  }
);

export const menuRetrieveHybridFlow = ai.defineFlow(
  {
    name: 'Menu - Retrieve Hybrid Flow',
    inputSchema: QuestionInputSchema,
    outputSchema: AnswerOutputSchema,
  },
  async (input) => {
    const docs = await ai.retrieve({
      retriever: mongoRetrieverRef('retriever'),
      query: input.question,
      options: {
        dbName: MONGODB_DB_NAME,
        collectionName: MONGODB_COLLECTION_NAME,
        embedder,
        hybridSearch: {
          search: {
            index: 'item_search_index',
            text: {
              path: 'menuItemMetadata.title',
              fuzzy: {
                maxEdits: 2,
                prefixLength: 0,
                maxExpansions: 50,
              },
            },
          },
          vectorSearch: {
            index: 'item_vector_index',
            path: 'embedding',
            exact: false,
            numCandidates: 10,
            limit: 3,
          },
        },
        dataTypeField: 'menuItemType',
        metadataField: 'menuItemMetadata',
        pipelines: [{ $limit: 3 }],
      },
    });

    const menuData: Array<MenuItem> = docs.map(
      (doc) => (doc.metadata || {}) as MenuItem
    );

    const response = await menuPrompt({
      menuData: menuData,
      question: input.question,
    });
    return { answer: response.text };
  }
);
