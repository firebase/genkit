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
import { Document } from 'genkit/retriever';
import { Collection, MongoClient, Document as MongoDocument } from 'mongodb';
import { BaseDefinition } from '../../src/common/types';
import { defineRetriever, mongoRetrieverRef } from '../../src/core/retriever';

jest.mock('../../src/common/connection');
jest.mock('../../src/common/types');
jest.mock('../../src/common/retry');

const mockCollection = {
  aggregate: jest.fn(),
} as unknown as jest.Mocked<Collection>;

const mockMongoClient = {} as MongoClient;

const mockGenkit = {
  defineRetriever: jest.fn(),
  embed: jest.fn(),
} as any;

describe('retriever', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { retryWithDelay } = require('../../src/common/retry');
    if (retryWithDelay && retryWithDelay.mockClear) retryWithDelay.mockClear();
    if (retryWithDelay && retryWithDelay.mockImplementation) {
      retryWithDelay.mockImplementation((fn, _opts) => fn());
    }
  });

  describe('mongoRetrieverRef', () => {
    it('should return retriever reference', () => {
      const ref = mongoRetrieverRef('test-retriever');

      expect(ref).toBeDefined();
      expect(ref.name).toBe('mongodb/test-retriever');
      expect(ref.info?.label).toBe('Mongo Retriever - test-retriever');
    });
  });

  describe('defineRetriever', () => {
    it('should define retriever when definition is provided', () => {
      const definition = {
        id: 'test-retriever',
        retry: {
          retryAttempts: 3,
          baseDelay: 100,
        },
      };

      defineRetriever(mockGenkit, mockMongoClient, definition);

      expect(mockGenkit.defineRetriever).toHaveBeenCalledWith(
        {
          name: 'mongodb/test-retriever',
          configSchema: expect.any(Object),
        },
        expect.any(Function)
      );
    });

    it('should not define retriever when definition is missing', () => {
      defineRetriever(mockGenkit, mockMongoClient, undefined);

      expect(mockGenkit.defineRetriever).not.toHaveBeenCalled();
    });

    it('should not define retriever when definition id is missing', () => {
      const definition = {
        retry: {
          retryAttempts: 3,
        },
      } as unknown as BaseDefinition;

      defineRetriever(mockGenkit, mockMongoClient, definition);

      expect(mockGenkit.defineRetriever).not.toHaveBeenCalled();
    });
  });

  describe('retriever function', () => {
    beforeEach(() => {
      const { getCollection } = require('../../src/common/connection');
      getCollection.mockReturnValue(mockCollection);
    });

    it('should process documents and retrieve from collection with text search', async () => {
      const definition = { id: 'test-retriever' };
      const mockResults = [
        {
          _id: 'doc1',
          data: 'test data 1',
          dataType: 'text',
          metadata: { source: 'test' },
        },
        {
          _id: 'doc2',
          data: 'test data 2',
          dataType: 'text',
          metadata: { source: 'test' },
        },
      ];

      const mockCursor = {
        toArray: jest.fn() as () => Promise<any>,
      } as any;
      mockCursor.toArray.mockResolvedValue(mockResults);
      mockCollection.aggregate.mockReturnValue(mockCursor);

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        search: {
          index: 'default',
          text: {
            path: 'data',
          },
        },
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');
      const result = await retrieverFunction(testDocument, {
        dbName: 'testdb',
        collectionName: 'testcollection',
        search: {
          index: 'default',
          text: {
            path: 'data',
          },
        },
      });

      expect(mockCollection.aggregate).toHaveBeenCalledWith([
        {
          $search: {
            index: 'default',
            text: {
              path: 'data',
              query: 'test query',
            },
          },
        },
      ]);
      expect(result).toEqual({
        documents: [
          Document.fromData('test data 1', 'text', { source: 'test' }),
          Document.fromData('test data 2', 'text', { source: 'test' }),
        ],
      });
    });

    it('should process documents and retrieve from collection with vector search', async () => {
      const definition = { id: 'test-retriever' };
      const mockResults = [
        {
          _id: 'doc1',
          data: 'test data 1',
          dataType: 'text',
          metadata: { source: 'test' },
        },
      ];

      const mockCursor = {
        toArray: jest.fn() as () => Promise<any>,
      } as any;
      mockCursor.toArray.mockResolvedValue(mockResults);
      mockCollection.aggregate.mockReturnValue(mockCursor);

      mockGenkit.embed.mockResolvedValue([{ embedding: [0.1, 0.2, 0.3] }]);

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        vectorSearch: {
          index: 'vector_index',
          path: 'embedding',
          numCandidates: 100,
          limit: 10,
        },
        embedder: 'test-embedder',
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');
      const result = await retrieverFunction(testDocument, {
        dbName: 'testdb',
        collectionName: 'testcollection',
        vectorSearch: {
          index: 'vector_index',
          path: 'embedding',
          numCandidates: 100,
          limit: 10,
        },
        embedder: 'test-embedder',
      });

      expect(mockGenkit.embed).toHaveBeenCalledWith({
        embedder: 'test-embedder',
        options: undefined,
        content: testDocument,
      });
      expect(mockCollection.aggregate).toHaveBeenCalledWith([
        {
          $vectorSearch: {
            index: 'vector_index',
            path: 'embedding',
            numCandidates: 100,
            limit: 10,
            queryVector: [0.1, 0.2, 0.3],
          },
        },
      ]);
      expect(result).toEqual({
        documents: [
          Document.fromData('test data 1', 'text', { source: 'test' }),
        ],
      });
    });

    it('should handle hybrid search', async () => {
      const definition = { id: 'test-retriever' };
      const mockResults = [
        {
          _id: 'doc1',
          data: 'test data 1',
          dataType: 'text',
          metadata: { source: 'test' },
        },
      ];

      const mockCursor = {
        toArray: jest.fn() as () => Promise<any>,
      } as any;
      mockCursor.toArray.mockResolvedValue(mockResults);
      mockCollection.aggregate.mockReturnValue(mockCursor);

      mockGenkit.embed.mockResolvedValue([{ embedding: [0.1, 0.2, 0.3] }]);

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        hybridSearch: {
          search: {
            index: 'text_index',
            text: {
              path: 'data',
            },
          },
          vectorSearch: {
            index: 'vector_index',
            path: 'embedding',
            numCandidates: 100,
            limit: 10,
          },
          combination: {
            weights: {
              vectorPipeline: 0.7,
              fullTextPipeline: 0.3,
            },
          },
          scoreDetails: true,
        },
        embedder: 'test-embedder',
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');
      const result = await retrieverFunction(testDocument, {
        dbName: 'testdb',
        collectionName: 'testcollection',
        hybridSearch: {
          search: {
            index: 'text_index',
            text: {
              path: 'data',
            },
          },
          vectorSearch: {
            index: 'vector_index',
            path: 'embedding',
            numCandidates: 100,
            limit: 10,
          },
          combination: {
            weights: {
              vectorPipeline: 0.7,
              fullTextPipeline: 0.3,
            },
          },
          scoreDetails: true,
        },
        embedder: 'test-embedder',
      });

      expect(mockGenkit.embed).toHaveBeenCalledWith({
        embedder: 'test-embedder',
        options: undefined,
        content: testDocument,
      });
      expect(mockCollection.aggregate).toHaveBeenCalledWith([
        {
          $rankFusion: {
            input: {
              pipelines: {
                fullTextPipeline: [
                  {
                    $search: {
                      index: 'text_index',
                      text: {
                        path: 'data',
                        query: 'test query',
                      },
                    },
                  },
                ],
                vectorPipeline: [
                  {
                    $vectorSearch: {
                      index: 'vector_index',
                      path: 'embedding',
                      numCandidates: 100,
                      limit: 10,
                      queryVector: [0.1, 0.2, 0.3],
                    },
                  },
                ],
              },
            },
            combination: {
              weights: {
                vectorPipeline: 0.7,
                fullTextPipeline: 0.3,
              },
            },
            scoreDetails: true,
          },
        },
      ]);
      expect(result).toEqual({
        documents: [
          Document.fromData('test data 1', 'text', { source: 'test' }),
        ],
      });
    });

    it('should handle hybrid search with default combination weights', async () => {
      const definition = { id: 'test-retriever' };
      const mockResults = [
        {
          _id: 'doc1',
          data: 'test data 1',
          dataType: 'text',
          metadata: { source: 'test' },
        },
      ];

      const mockCursor = {
        toArray: jest.fn() as () => Promise<any>,
      } as any;
      mockCursor.toArray.mockResolvedValue(mockResults);
      mockCollection.aggregate.mockReturnValue(mockCursor);

      mockGenkit.embed.mockResolvedValue([{ embedding: [0.1, 0.2, 0.3] }]);

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        hybridSearch: {
          search: {
            index: 'text_index',
            text: {
              path: 'data',
            },
          },
          vectorSearch: {
            index: 'vector_index',
            path: 'embedding',
            numCandidates: 100,
            limit: 10,
          },
        },
        embedder: 'test-embedder',
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');
      const result = await retrieverFunction(testDocument, {
        dbName: 'testdb',
        collectionName: 'testcollection',
        hybridSearch: {
          search: {
            index: 'text_index',
            text: {
              path: 'data',
            },
          },
          vectorSearch: {
            index: 'vector_index',
            path: 'embedding',
            numCandidates: 100,
            limit: 10,
          },
        },
        embedder: 'test-embedder',
      });

      expect(mockCollection.aggregate).toHaveBeenCalledWith([
        {
          $rankFusion: {
            input: {
              pipelines: {
                fullTextPipeline: [
                  {
                    $search: {
                      index: 'text_index',
                      text: {
                        path: 'data',
                        query: 'test query',
                      },
                    },
                  },
                ],
                vectorPipeline: [
                  {
                    $vectorSearch: {
                      index: 'vector_index',
                      path: 'embedding',
                      numCandidates: 100,
                      limit: 10,
                      queryVector: [0.1, 0.2, 0.3],
                    },
                  },
                ],
              },
            },
            combination: undefined,
            scoreDetails: undefined,
          },
        },
      ]);
      expect(result).toEqual({
        documents: [
          Document.fromData('test data 1', 'text', { source: 'test' }),
        ],
      });
    });

    it('should handle hybrid search with custom embedder options', async () => {
      const definition = { id: 'test-retriever' };
      const mockResults = [
        {
          _id: 'doc1',
          data: 'test data 1',
          dataType: 'text',
          metadata: { source: 'test' },
        },
      ];

      const mockCursor = {
        toArray: jest.fn() as () => Promise<any>,
      } as any;
      mockCursor.toArray.mockResolvedValue(mockResults);
      mockCollection.aggregate.mockReturnValue(mockCursor);

      mockGenkit.embed.mockResolvedValue([{ embedding: [0.1, 0.2, 0.3] }]);

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        hybridSearch: {
          search: {
            index: 'text_index',
            text: {
              path: 'data',
            },
          },
          vectorSearch: {
            index: 'vector_index',
            path: 'embedding',
            numCandidates: 100,
            limit: 10,
          },
        },
        embedder: 'test-embedder',
        embedderOptions: { model: 'text-embedding-3-small' },
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');
      const result = await retrieverFunction(testDocument, {
        dbName: 'testdb',
        collectionName: 'testcollection',
        hybridSearch: {
          search: {
            index: 'text_index',
            text: {
              path: 'data',
            },
          },
          vectorSearch: {
            index: 'vector_index',
            path: 'embedding',
            numCandidates: 100,
            limit: 10,
          },
        },
        embedder: 'test-embedder',
        embedderOptions: { model: 'text-embedding-3-small' },
      });

      expect(mockGenkit.embed).toHaveBeenCalledWith({
        embedder: 'test-embedder',
        options: { model: 'text-embedding-3-small' },
        content: testDocument,
      });
      expect(result).toEqual({
        documents: [
          Document.fromData('test data 1', 'text', { source: 'test' }),
        ],
      });
    });

    it('should handle hybrid search with custom pipeline stages', async () => {
      const definition = { id: 'test-retriever' };
      const mockResults = [
        {
          _id: 'doc1',
          data: 'test data 1',
          dataType: 'text',
          metadata: { source: 'test' },
        },
      ];

      const mockCursor = {
        toArray: jest.fn() as () => Promise<any>,
      } as any;
      mockCursor.toArray.mockResolvedValue(mockResults);
      mockCollection.aggregate.mockReturnValue(mockCursor);

      mockGenkit.embed.mockResolvedValue([{ embedding: [0.1, 0.2, 0.3] }]);

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        hybridSearch: {
          search: {
            index: 'text_index',
            text: {
              path: 'data',
            },
          },
          vectorSearch: {
            index: 'vector_index',
            path: 'embedding',
            numCandidates: 100,
            limit: 10,
          },
        },
        embedder: 'test-embedder',
        pipelines: [{ $limit: 5 }, { $sort: { score: -1 } }],
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');
      const result = await retrieverFunction(testDocument, {
        dbName: 'testdb',
        collectionName: 'testcollection',
        hybridSearch: {
          search: {
            index: 'text_index',
            text: {
              path: 'data',
            },
          },
          vectorSearch: {
            index: 'vector_index',
            path: 'embedding',
            numCandidates: 100,
            limit: 10,
          },
        },
        embedder: 'test-embedder',
        pipelines: [{ $limit: 5 }, { $sort: { score: -1 } }],
      });

      expect(mockCollection.aggregate).toHaveBeenCalledWith([
        {
          $rankFusion: {
            input: {
              pipelines: {
                fullTextPipeline: [
                  {
                    $search: {
                      index: 'text_index',
                      text: {
                        path: 'data',
                        query: 'test query',
                      },
                    },
                  },
                ],
                vectorPipeline: [
                  {
                    $vectorSearch: {
                      index: 'vector_index',
                      path: 'embedding',
                      numCandidates: 100,
                      limit: 10,
                      queryVector: [0.1, 0.2, 0.3],
                    },
                  },
                ],
              },
            },
            combination: undefined,
            scoreDetails: undefined,
          },
        },
        { $limit: 5 },
        { $sort: { score: -1 } },
      ]);
      expect(result).toEqual({
        documents: [
          Document.fromData('test data 1', 'text', { source: 'test' }),
        ],
      });
    });

    it('should handle errors during retrieval', async () => {
      const definition = { id: 'test-retriever' };

      mockCollection.aggregate.mockImplementation(() => {
        throw new Error('Aggregation failed');
      });

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        search: {
          index: 'default',
          text: {
            path: 'data',
          },
        },
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');

      await expect(
        retrieverFunction(testDocument, {
          dbName: 'testdb',
          collectionName: 'testcollection',
          search: {
            index: 'default',
            text: {
              path: 'data',
            },
          },
        })
      ).rejects.toThrow('Mongo retrieval failed: Aggregation failed');
    });

    it('should handle unknown search options', async () => {
      const definition = { id: 'test-retriever' };

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');

      await expect(
        retrieverFunction(testDocument, {
          dbName: 'testdb',
          collectionName: 'testcollection',
        })
      ).rejects.toThrow(
        'Mongo retrieval failed: Failed to create search pipeline: Unknown retrieval options provided'
      );
    });

    it('should handle empty results', async () => {
      const definition = { id: 'test-retriever' };
      const mockResults: MongoDocument[] = [];

      const mockCursor = {
        toArray: jest.fn() as () => Promise<any>,
      } as any;
      mockCursor.toArray.mockResolvedValue(mockResults);
      mockCollection.aggregate.mockReturnValue(mockCursor);

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        search: {
          index: 'default',
          text: {
            path: 'data',
          },
        },
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');
      const result = await retrieverFunction(testDocument, {
        dbName: 'testdb',
        collectionName: 'testcollection',
        search: {
          index: 'default',
          text: {
            path: 'data',
          },
        },
      });

      expect(result).toEqual({
        documents: [],
      });
    });

    it('should handle missing data fields in results', async () => {
      const definition = { id: 'test-retriever' };
      const mockResults = [
        {
          _id: 'doc1',
          dataType: 'text',
          metadata: { source: 'test' },
        },
      ];

      const mockCursor = {
        toArray: jest.fn() as () => Promise<any>,
      } as any;
      mockCursor.toArray.mockResolvedValue(mockResults);
      mockCollection.aggregate.mockReturnValue(mockCursor);

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        search: {
          index: 'default',
          text: {
            path: 'data',
          },
        },
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');
      const result = await retrieverFunction(testDocument, {
        dbName: 'testdb',
        collectionName: 'testcollection',
        search: {
          index: 'default',
          text: {
            path: 'data',
          },
        },
      });

      expect(result).toEqual({
        documents: [Document.fromData('', 'text', { source: 'test' })],
      });
    });

    it('should handle custom pipeline options', async () => {
      const definition = { id: 'test-retriever' };
      const mockResults = [
        {
          _id: 'doc1',
          data: 'test data 1',
          dataType: 'text',
          metadata: { source: 'test' },
        },
      ];

      const mockCursor = {
        toArray: jest.fn() as () => Promise<any>,
      } as any;
      mockCursor.toArray.mockResolvedValue(mockResults);
      mockCollection.aggregate.mockReturnValue(mockCursor);

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        search: {
          index: 'default',
          text: {
            path: 'data',
          },
        },
        pipelines: [{ $limit: 5 }, { $sort: { score: -1 } }],
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');
      const result = await retrieverFunction(testDocument, {
        dbName: 'testdb',
        collectionName: 'testcollection',
        search: {
          index: 'default',
          text: {
            path: 'data',
          },
        },
        pipelines: [{ $limit: 5 }, { $sort: { score: -1 } }],
      });

      expect(mockCollection.aggregate).toHaveBeenCalledWith([
        {
          $search: {
            index: 'default',
            text: {
              path: 'data',
              query: 'test query',
            },
          },
        },
        { $limit: 5 },
        { $sort: { score: -1 } },
      ]);
      expect(result).toEqual({
        documents: [
          Document.fromData('test data 1', 'text', { source: 'test' }),
        ],
      });
    });

    it('should handle non-Error exceptions during retrieval', async () => {
      const definition = { id: 'test-retriever' };

      mockCollection.aggregate.mockImplementation(() => {
        throw 'String error';
      });

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        search: {
          index: 'default',
          text: {
            path: 'data',
          },
        },
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');

      await expect(
        retrieverFunction(testDocument, {
          dbName: 'testdb',
          collectionName: 'testcollection',
          search: {
            index: 'default',
            text: {
              path: 'data',
            },
          },
        })
      ).rejects.toThrow('Mongo retrieval failed: Unknown error');
    });

    it('should handle non-Error exceptions in search pipeline creation', async () => {
      const definition = { id: 'test-retriever' };

      mockGenkit.embed.mockImplementation(() => {
        throw 'String error';
      });

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        vectorSearch: {
          index: 'vector_index',
          path: 'embedding',
          numCandidates: 100,
          limit: 10,
        },
        embedder: 'test-embedder',
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');

      await expect(
        retrieverFunction(testDocument, {
          dbName: 'testdb',
          collectionName: 'testcollection',
          vectorSearch: {
            index: 'vector_index',
            path: 'embedding',
            numCandidates: 100,
            limit: 10,
          },
          embedder: 'test-embedder',
        })
      ).rejects.toThrow(
        'Mongo retrieval failed: Failed to create search pipeline: Unknown error'
      );
    });

    it('should handle non-Error exceptions in retriever configuration', async () => {
      const definition = { id: 'test-retriever' };

      const { getCollection } = require('../../src/common/connection');
      getCollection.mockImplementation(() => {
        throw 'String error';
      });

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        search: {
          index: 'default',
          text: {
            path: 'data',
          },
        },
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');

      await expect(
        retrieverFunction(testDocument, {
          dbName: 'testdb',
          collectionName: 'testcollection',
          search: {
            index: 'default',
            text: {
              path: 'data',
            },
          },
        })
      ).rejects.toThrow('Mongo retrieval failed: Unknown error');
    });

    it('should handle validation errors in retriever options', async () => {
      const definition = { id: 'test-retriever' };

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockImplementation(() => {
        throw new Error('Invalid options: missing required field');
      });

      const testDocument = Document.fromText('test query');

      await expect(
        retrieverFunction(testDocument, {
          dbName: 'testdb',
          collectionName: 'testcollection',
          search: {
            index: 'default',
            text: {
              path: 'data',
            },
          },
        })
      ).rejects.toThrow(
        'Mongo retrieval failed: Invalid options: missing required field'
      );
    });

    it('should handle retry failures in search pipeline execution', async () => {
      const definition = { id: 'test-retriever' };

      const { retryWithDelay } = require('../../src/common/retry');
      retryWithDelay.mockRejectedValue(
        new Error('Retry failed after all attempts')
      );

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        search: {
          index: 'default',
          text: {
            path: 'data',
          },
        },
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');

      await expect(
        retrieverFunction(testDocument, {
          dbName: 'testdb',
          collectionName: 'testcollection',
          search: {
            index: 'default',
            text: {
              path: 'data',
            },
          },
        })
      ).rejects.toThrow(
        'Mongo retrieval failed: Retry failed after all attempts'
      );
    });

    it('should handle hybrid search with embedding generation failure', async () => {
      const definition = { id: 'test-retriever' };

      mockGenkit.embed.mockRejectedValue(
        new Error('Embedding service unavailable')
      );

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        hybridSearch: {
          search: {
            index: 'text_index',
            text: {
              path: 'data',
            },
          },
          vectorSearch: {
            index: 'vector_index',
            path: 'embedding',
            numCandidates: 100,
            limit: 10,
          },
        },
        embedder: 'test-embedder',
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');

      await expect(
        retrieverFunction(testDocument, {
          dbName: 'testdb',
          collectionName: 'testcollection',
          hybridSearch: {
            search: {
              index: 'text_index',
              text: {
                path: 'data',
              },
            },
            vectorSearch: {
              index: 'vector_index',
              path: 'embedding',
              numCandidates: 100,
              limit: 10,
            },
          },
          embedder: 'test-embedder',
        })
      ).rejects.toThrow(
        'Mongo retrieval failed: Failed to create search pipeline: Embedding service unavailable'
      );
    });

    it('should handle vector search with embedding generation failure', async () => {
      const definition = { id: 'test-retriever' };

      mockGenkit.embed.mockRejectedValue(
        new Error('Embedding service unavailable')
      );

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        vectorSearch: {
          index: 'vector_index',
          path: 'embedding',
          numCandidates: 100,
          limit: 10,
        },
        embedder: 'test-embedder',
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');

      await expect(
        retrieverFunction(testDocument, {
          dbName: 'testdb',
          collectionName: 'testcollection',
          vectorSearch: {
            index: 'vector_index',
            path: 'embedding',
            numCandidates: 100,
            limit: 10,
          },
          embedder: 'test-embedder',
        })
      ).rejects.toThrow(
        'Mongo retrieval failed: Failed to create search pipeline: Embedding service unavailable'
      );
    });

    it('should handle empty embedding result', async () => {
      const definition = { id: 'test-retriever' };

      mockGenkit.embed.mockResolvedValue([]);

      defineRetriever(mockGenkit, mockMongoClient, definition);
      const retrieverFunction = mockGenkit.defineRetriever.mock.calls[0][1];

      const { validateRetrieverOptions } = require('../../src/common/types');
      validateRetrieverOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        vectorSearch: {
          index: 'vector_index',
          path: 'embedding',
          numCandidates: 100,
          limit: 10,
        },
        embedder: 'test-embedder',
        dataField: 'data',
        dataTypeField: 'dataType',
        metadataField: 'metadata',
      });

      const testDocument = Document.fromText('test query');

      await expect(
        retrieverFunction(testDocument, {
          dbName: 'testdb',
          collectionName: 'testcollection',
          vectorSearch: {
            index: 'vector_index',
            path: 'embedding',
            numCandidates: 100,
            limit: 10,
          },
          embedder: 'test-embedder',
        })
      ).rejects.toThrow(
        'Mongo retrieval failed: Failed to create search pipeline: Cannot read properties of undefined'
      );
    });
  });
});
