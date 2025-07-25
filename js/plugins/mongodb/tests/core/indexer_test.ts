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

import { beforeEach, describe, expect, it, jest } from '@jest/globals';
import { Document } from 'genkit';
import { Collection, InsertManyResult, MongoClient } from 'mongodb';
import { BaseDefinition } from '../../src/common/types';
import { defineIndexer, mongoIndexerRef } from '../../src/core/indexer';

jest.mock('../../src/common/connection');
jest.mock('../../src/common/retry');
jest.mock('../../src/common/types');

const mockCollection = {
  insertMany: jest.fn(),
} as unknown as jest.Mocked<Collection>;

const mockMongoClient = {} as MongoClient;

const mockGenkit = {
  defineIndexer: jest.fn(),
  embed: jest.fn(),
} as any;

describe('indexer', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('mongoIndexerRef', () => {
    it('should return indexer reference', () => {
      const ref = mongoIndexerRef('test-indexer');

      expect(ref).toBeDefined();
      expect(ref.name).toBe('mongodb/test-indexer');
      expect(ref.info?.label).toBe('Mongo Indexer - test-indexer');
    });
  });

  describe('defineIndexer', () => {
    it('should define indexer when definition is provided', () => {
      const definition = {
        id: 'test-indexer',
        retry: {
          retryAttempts: 3,
          baseDelay: 100,
        },
      };

      defineIndexer(mockGenkit, mockMongoClient, definition);

      expect(mockGenkit.defineIndexer).toHaveBeenCalledWith(
        {
          name: 'mongodb/test-indexer',
          configSchema: expect.any(Object),
        },
        expect.any(Function)
      );
    });

    it('should not define indexer when definition is missing', () => {
      defineIndexer(mockGenkit, mockMongoClient, undefined);

      expect(mockGenkit.defineIndexer).not.toHaveBeenCalled();
    });

    it('should not define indexer when definition id is missing', () => {
      const definition = {
        retry: {
          retryAttempts: 3,
        },
      } as unknown as BaseDefinition;

      defineIndexer(mockGenkit, mockMongoClient, definition);

      expect(mockGenkit.defineIndexer).not.toHaveBeenCalled();
    });
  });

  describe('indexer function', () => {
    it('should process documents and insert into collection', async () => {
      const definition = {
        id: 'test-indexer',
      };

      const mockDocuments = [
        Document.fromText('test content', { source: 'test' }),
      ];

      mockGenkit.embed.mockResolvedValue([{ embedding: [0.1, 0.2, 0.3] }]);

      defineIndexer(mockGenkit, mockMongoClient, definition);
      const indexerFunction = mockGenkit.defineIndexer.mock.calls[0][1];

      const mockInsertResult = {
        insertedCount: 1,
        insertedIds: { 0: 'test-id' },
      } as unknown as InsertManyResult;

      mockCollection.insertMany.mockResolvedValue(mockInsertResult);

      const { getCollection } = require('../../src/common/connection');
      getCollection.mockReturnValue(mockCollection);

      const { validateIndexerOptions } = require('../../src/common/types');
      validateIndexerOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        embedder: { name: 'test-embedder' },
        dataField: 'data',
        metadataField: 'metadata',
        dataTypeField: 'dataType',
        embeddingField: 'embedding',
        batchSize: 100,
        skipData: false,
      });

      const { retryWithDelay } = require('../../src/common/retry');
      retryWithDelay.mockImplementation(async (fn) => {
        return await fn();
      });

      const options = {
        dbName: 'testdb',
        collectionName: 'testcollection',
        embedder: { name: 'test-embedder' },
      };

      await indexerFunction(mockDocuments, options);

      expect(mockGenkit.embed).toHaveBeenCalledWith({
        embedder: { name: 'test-embedder' },
        options: undefined,
        content: mockDocuments[0],
      });

      expect(mockCollection.insertMany).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({
            embedding: [0.1, 0.2, 0.3],
            dataType: 'text',
            metadata: { source: 'test' },
            createdAt: expect.any(Date),
            data: 'test content',
          }),
        ]),
        { ordered: false }
      );
    });

    it('should handle errors during indexing', async () => {
      const definition = {
        id: 'test-indexer',
      };

      const mockDocuments = [
        Document.fromText('test content', { source: 'test' }),
      ];

      const { getCollection } = require('../../src/common/connection');
      getCollection.mockImplementation(() => {
        throw new Error('Collection error');
      });

      const { validateIndexerOptions } = require('../../src/common/types');
      validateIndexerOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        embedder: { name: 'test-embedder' },
      });

      const { retryWithDelay } = require('../../src/common/retry');
      retryWithDelay.mockImplementation(async (fn) => {
        return await fn();
      });

      defineIndexer(mockGenkit, mockMongoClient, definition);
      const indexerFunction = mockGenkit.defineIndexer.mock.calls[0][1];

      const options = {
        dbName: 'testdb',
        collectionName: 'testcollection',
        embedder: { name: 'test-embedder' },
      };

      await expect(indexerFunction(mockDocuments, options)).rejects.toThrow(
        'Mongo indexing failed: Collection error'
      );
    });

    it('should skip data field when skipData is true', async () => {
      const definition = {
        id: 'test-indexer',
      };

      const mockDocuments = [
        Document.fromText('test content', { source: 'test' }),
      ];

      mockGenkit.embed.mockResolvedValue([{ embedding: [0.1, 0.2, 0.3] }]);

      defineIndexer(mockGenkit, mockMongoClient, definition);
      const indexerFunction = mockGenkit.defineIndexer.mock.calls[0][1];

      const mockInsertResult = {
        insertedCount: 1,
        insertedIds: { 0: 'test-id' },
      } as unknown as InsertManyResult;

      mockCollection.insertMany.mockResolvedValue(mockInsertResult);

      const { getCollection } = require('../../src/common/connection');
      getCollection.mockReturnValue(mockCollection);

      const { validateIndexerOptions } = require('../../src/common/types');
      validateIndexerOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        embedder: { name: 'test-embedder' },
        dataField: 'data',
        metadataField: 'metadata',
        dataTypeField: 'dataType',
        embeddingField: 'embedding',
        batchSize: 100,
        skipData: true,
      });

      const options = {
        dbName: 'testdb',
        collectionName: 'testcollection',
        embedder: { name: 'test-embedder' },
        skipData: true,
      };

      await indexerFunction(mockDocuments, options);

      expect(mockCollection.insertMany).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({
            embedding: [0.1, 0.2, 0.3],
            dataType: 'text',
            metadata: { source: 'test' },
            createdAt: expect.any(Date),
          }),
        ]),
        { ordered: false }
      );

      const insertedDocs = mockCollection.insertMany.mock.calls[0][0];
      expect(insertedDocs[0]).not.toHaveProperty('data');
    });

    it('should handle non-Error exceptions during indexing', async () => {
      const definition = {
        id: 'test-indexer',
      };

      const mockDocuments = [
        Document.fromText('test content', { source: 'test' }),
      ];

      const { getCollection } = require('../../src/common/connection');
      getCollection.mockImplementation(() => {
        throw 'String error';
      });

      const { validateIndexerOptions } = require('../../src/common/types');
      validateIndexerOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        embedder: { name: 'test-embedder' },
      });

      const { retryWithDelay } = require('../../src/common/retry');
      retryWithDelay.mockImplementation(async (fn) => {
        return await fn();
      });

      defineIndexer(mockGenkit, mockMongoClient, definition);
      const indexerFunction = mockGenkit.defineIndexer.mock.calls[0][1];

      const options = {
        dbName: 'testdb',
        collectionName: 'testcollection',
        embedder: { name: 'test-embedder' },
      };

      await expect(indexerFunction(mockDocuments, options)).rejects.toThrow(
        'Mongo indexing failed: Unknown error'
      );
    });
  });
});
