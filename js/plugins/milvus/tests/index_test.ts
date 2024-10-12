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
import { textEmbeddingGecko } from '@genkit-ai/vertexai';
import assert from 'node:assert';
import { describe, it } from 'node:test';

import {
  createMilvusCollection,
  deleteMilvusCollection,
  hasMilvusCollection,
  insertMilvusData,
  milvus,
  milvusIndexerRef,
  milvusRetrieverRef,
  searchMilvusData,
} from '../src/index';

/** Milvus vector database connection params */
const clientParams = {
  address: '',
  token: '',
};
const COLLECTION_NAME = 'collection_01';

const mockEntries = [
  {
    vector: [0.1, 0.2, 0.3, 0.4],
    document: 'This is a test document',
    metadata: {
      text: 'This is a test document',
      pos: 1,
    },
  },
  {
    vector: [0.5, 0.6, 0.7, 0.8],
    document: 'This is another test document',
    metadata: {
      text: 'This is another test document',
      pos: 2,
    },
  },
];

const config = configureGenkit({
  plugins: [
    milvus([
      {
        collectionName: COLLECTION_NAME,
        clientParams,
        embedder: textEmbeddingGecko,
        embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
      },
    ]),
  ],
});

describe('Test Genkit Milvus Plugin', () => {
  it('should create a retriever', async () => {
    const retriever = milvusRetrieverRef({
      collectionName: COLLECTION_NAME,
    });
    assert(retriever.name === `milvus/${COLLECTION_NAME}`);
  });

  it('should create an indexer', async () => {
    const indexer = milvusIndexerRef({
      collectionName: COLLECTION_NAME,
    });
    assert(indexer.name === `milvus/${COLLECTION_NAME}`);
  });

  if (clientParams.address) {
    it('should create a collection', async () => {
      const isCollectionExists = await hasMilvusCollection({
        collectionName: COLLECTION_NAME,
        clientParams,
      });
      if (isCollectionExists) {
        console.log('Collection already exists');
        assert(true);
        return;
      }
      const result = await createMilvusCollection({
        collectionName: COLLECTION_NAME,
        dimension: 4,
        clientParams,
      });
      assert(result.error_code === 'Success');
    });

    it('should insert data', async () => {
      const result = await insertMilvusData({
        collectionName: COLLECTION_NAME,
        entries: mockEntries,
        clientParams,
      });
      assert(result.insert_cnt === `${mockEntries.length}`);
    });

    it('should search data', async () => {
      const result = await searchMilvusData({
        collectionName: COLLECTION_NAME,
        query: mockEntries[0].vector,
        clientParams,
      });
      assert(
        result.status.error_code === 'Success' && result.results.length >= 0
      );
    });

    it('should delete a collection', async () => {
      const result = await deleteMilvusCollection({
        collectionName: COLLECTION_NAME,
        clientParams,
      });
      assert(result.error_code === 'Success');
    });
  }
});
