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
import { Collection, MongoClient } from 'mongodb';
import { BaseDefinition } from '../../src/common/types';
import {
  defineSearchIndexTools,
  mongoSearchIndexToolsRefArray,
} from '../../src/tools/search-indexes';

jest.mock('../../src/common/connection');
jest.mock('../../src/common/types');
jest.mock('../../src/common/retry');

const mockCollection = {
  createSearchIndex: jest.fn(),
  listSearchIndexes: jest.fn(),
  dropSearchIndex: jest.fn(),
  collectionName: 'testcollection',
} as unknown as jest.Mocked<Collection>;

const mockMongoClient = {} as MongoClient;

const mockGenkit = {
  defineTool: jest.fn(),
} as any;

describe('Search Index tools', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { retryWithDelay } = require('../../src/common/retry');
    if (retryWithDelay && retryWithDelay.mockClear) retryWithDelay.mockClear();
    if (retryWithDelay && retryWithDelay.mockImplementation) {
      retryWithDelay.mockImplementation((fn, _opts) => fn());
    }
  });

  describe('mongoSearchIndexToolsRefArray', () => {
    it('should return array of tool names', () => {
      const toolNames = mongoSearchIndexToolsRefArray('test-search-index');

      expect(Array.isArray(toolNames)).toBe(true);
      expect(toolNames).toEqual([
        'mongodb/test-search-index/create',
        'mongodb/test-search-index/list',
        'mongodb/test-search-index/drop',
      ]);
    });
  });

  describe('defineSearchIndexTools', () => {
    it('should define search index tools when definition is provided', () => {
      const definition = {
        id: 'test-search-index',
      };

      defineSearchIndexTools(mockGenkit, mockMongoClient, definition);

      expect(mockGenkit.defineTool).toHaveBeenCalledTimes(3);
    });

    it('should not define tools when definition is missing', () => {
      defineSearchIndexTools(mockGenkit, mockMongoClient, undefined);

      expect(mockGenkit.defineTool).not.toHaveBeenCalled();
    });

    it('should not define tools when definition id is missing', () => {
      const definition = {
        retry: {
          retryAttempts: 3,
        },
      } as unknown as BaseDefinition;

      defineSearchIndexTools(mockGenkit, mockMongoClient, definition);

      expect(mockGenkit.defineTool).not.toHaveBeenCalled();
    });
  });

  describe('Search Index tool functions', () => {
    beforeEach(() => {
      const { getCollection } = require('../../src/common/connection');
      getCollection.mockReturnValue(mockCollection);
    });

    describe('create search index tool', () => {
      it('should create search index successfully', async () => {
        const definition = { id: 'test-search-index' };
        const mockIndexName = 'test_index';

        mockCollection.createSearchIndex.mockResolvedValue(mockIndexName);

        defineSearchIndexTools(mockGenkit, mockMongoClient, definition);
        const createTool = mockGenkit.defineTool.mock.calls.find(
          (call) => call[0].name === 'mongodb/test-search-index/create'
        )?.[1];

        const {
          validateSearchIndexCreateOptions,
        } = require('../../src/common/types');
        validateSearchIndexCreateOptions.mockReturnValue({
          dbName: 'testdb',
          collectionName: 'testcollection',
          indexName: 'test_index',
          schema: { mappings: { dynamic: true } },
        });

        const result = await createTool({
          dbName: 'testdb',
          collectionName: 'testcollection',
          indexName: 'test_index',
          schema: { mappings: { dynamic: true } },
        });

        expect(mockCollection.createSearchIndex).toHaveBeenCalledWith({
          mappings: { dynamic: true },
        });
        expect(result).toEqual({
          indexName: mockIndexName,
          success: true,
          message:
            'Search index creation operation started successfully: test_index',
        });
      });

      it('should handle create search index errors', async () => {
        const definition = { id: 'test-search-index' };

        mockCollection.createSearchIndex.mockRejectedValue(
          new Error('Create index failed')
        );

        defineSearchIndexTools(mockGenkit, mockMongoClient, definition);
        const createTool = mockGenkit.defineTool.mock.calls.find(
          (call) => call[0].name === 'mongodb/test-search-index/create'
        )?.[1];

        const {
          validateSearchIndexCreateOptions,
        } = require('../../src/common/types');
        validateSearchIndexCreateOptions.mockReturnValue({
          dbName: 'testdb',
          collectionName: 'testcollection',
          indexName: 'test_index',
          schema: { mappings: { dynamic: true } },
        });

        const result = await createTool({
          dbName: 'testdb',
          collectionName: 'testcollection',
          indexName: 'test_index',
          schema: { mappings: { dynamic: true } },
        });

        expect(result).toEqual({
          indexName: '',
          success: false,
          message: 'Failed to create search index: Create index failed',
        });
      });
    });

    describe('list search indexes tool', () => {
      it('should list search indexes successfully', async () => {
        const definition = { id: 'test-search-index' };
        const mockIndexes = [
          { name: 'index1', definition: { mappings: { dynamic: true } } },
          { name: 'index2', definition: { mappings: { dynamic: false } } },
        ];

        const mockCursor = {
          toArray: jest.fn() as () => Promise<any>,
        } as any;
        mockCursor.toArray.mockResolvedValue(mockIndexes);
        mockCollection.listSearchIndexes.mockReturnValue(mockCursor);

        defineSearchIndexTools(mockGenkit, mockMongoClient, definition);
        const listTool = mockGenkit.defineTool.mock.calls.find(
          (call) => call[0].name === 'mongodb/test-search-index/list'
        )?.[1];

        const {
          validateSearchIndexListOptions,
        } = require('../../src/common/types');
        validateSearchIndexListOptions.mockReturnValue({
          dbName: 'testdb',
          collectionName: 'testcollection',
        });

        const result = await listTool({
          dbName: 'testdb',
          collectionName: 'testcollection',
        });

        expect(mockCollection.listSearchIndexes).toHaveBeenCalled();
        expect(mockCursor.toArray).toHaveBeenCalled();
        expect(result).toEqual({
          indexes: mockIndexes,
          success: true,
          message: 'Found 2 indexes on collection testcollection',
        });
      });

      it('should handle list search indexes errors', async () => {
        const definition = { id: 'test-search-index' };

        const mockCursor = {
          toArray: jest.fn() as () => Promise<any>,
        } as any;
        mockCursor.toArray.mockRejectedValue(new Error('List indexes failed'));
        mockCollection.listSearchIndexes.mockReturnValue(mockCursor);

        defineSearchIndexTools(mockGenkit, mockMongoClient, definition);
        const listTool = mockGenkit.defineTool.mock.calls.find(
          (call) => call[0].name === 'mongodb/test-search-index/list'
        )?.[1];

        const {
          validateSearchIndexListOptions,
        } = require('../../src/common/types');
        validateSearchIndexListOptions.mockReturnValue({
          dbName: 'testdb',
          collectionName: 'testcollection',
        });

        const result = await listTool({
          dbName: 'testdb',
          collectionName: 'testcollection',
        });

        expect(result).toEqual({
          indexes: [],
          success: false,
          message: 'Failed to list indexes: List indexes failed',
        });
      });

      it('should handle empty index list', async () => {
        const definition = { id: 'test-search-index' };
        const mockIndexes: any[] = [];

        const mockCursor = {
          toArray: jest.fn() as () => Promise<any>,
        } as any;
        mockCursor.toArray.mockResolvedValue(mockIndexes);
        mockCollection.listSearchIndexes.mockReturnValue(mockCursor);

        defineSearchIndexTools(mockGenkit, mockMongoClient, definition);
        const listTool = mockGenkit.defineTool.mock.calls.find(
          (call) => call[0].name === 'mongodb/test-search-index/list'
        )?.[1];

        const {
          validateSearchIndexListOptions,
        } = require('../../src/common/types');
        validateSearchIndexListOptions.mockReturnValue({
          dbName: 'testdb',
          collectionName: 'testcollection',
        });

        const result = await listTool({
          dbName: 'testdb',
          collectionName: 'testcollection',
        });

        expect(result).toEqual({
          indexes: [],
          success: true,
          message: 'Found 0 indexes on collection testcollection',
        });
      });
    });

    describe('drop search index tool', () => {
      it('should drop search index successfully', async () => {
        const definition = { id: 'test-search-index' };

        mockCollection.dropSearchIndex.mockResolvedValue(undefined);

        defineSearchIndexTools(mockGenkit, mockMongoClient, definition);
        const dropTool = mockGenkit.defineTool.mock.calls.find(
          (call) => call[0].name === 'mongodb/test-search-index/drop'
        )?.[1];

        const {
          validateSearchIndexDropOptions,
        } = require('../../src/common/types');
        validateSearchIndexDropOptions.mockReturnValue({
          dbName: 'testdb',
          collectionName: 'testcollection',
          indexName: 'test_index',
        });

        const result = await dropTool({
          dbName: 'testdb',
          collectionName: 'testcollection',
          indexName: 'test_index',
        });

        expect(mockCollection.dropSearchIndex).toHaveBeenCalledWith(
          'test_index'
        );
        expect(result).toEqual({
          success: true,
          message: 'Index test_index drop operation started successfully',
        });
      });

      it('should handle drop search index errors', async () => {
        const definition = { id: 'test-search-index' };

        mockCollection.dropSearchIndex.mockRejectedValue(
          new Error('Drop index failed')
        );

        defineSearchIndexTools(mockGenkit, mockMongoClient, definition);
        const dropTool = mockGenkit.defineTool.mock.calls.find(
          (call) => call[0].name === 'mongodb/test-search-index/drop'
        )?.[1];

        const {
          validateSearchIndexDropOptions,
        } = require('../../src/common/types');
        validateSearchIndexDropOptions.mockReturnValue({
          dbName: 'testdb',
          collectionName: 'testcollection',
          indexName: 'test_index',
        });

        const result = await dropTool({
          dbName: 'testdb',
          collectionName: 'testcollection',
          indexName: 'test_index',
        });

        expect(result).toEqual({
          success: false,
          message: 'Failed to drop index: Drop index failed',
        });
      });
    });
  });

  describe('Tool configuration', () => {
    it('should configure tools with correct names and schemas', () => {
      const definition = { id: 'test-search-index' };

      defineSearchIndexTools(mockGenkit, mockMongoClient, definition);

      const toolCalls = mockGenkit.defineTool.mock.calls;

      const createToolCall = toolCalls.find(
        (call) => call[0].name === 'mongodb/test-search-index/create'
      );
      expect(createToolCall).toBeDefined();
      expect(createToolCall![0].description).toBe(
        'Create a text search index on MongoDB'
      );
      expect(createToolCall![0].inputSchema).toBeDefined();
      expect(createToolCall![0].outputSchema).toBeDefined();

      const listToolCall = toolCalls.find(
        (call) => call[0].name === 'mongodb/test-search-index/list'
      );
      expect(listToolCall).toBeDefined();
      expect(listToolCall![0].description).toBe('List all indexes on MongoDB');
      expect(listToolCall![0].inputSchema).toBeDefined();
      expect(listToolCall![0].outputSchema).toBeDefined();

      const dropToolCall = toolCalls.find(
        (call) => call[0].name === 'mongodb/test-search-index/drop'
      );
      expect(dropToolCall).toBeDefined();
      expect(dropToolCall![0].description).toBe(
        'Drop an index by name from MongoDB'
      );
      expect(dropToolCall![0].inputSchema).toBeDefined();
      expect(dropToolCall![0].outputSchema).toBeDefined();
    });

    it('should handle retry options when provided', async () => {
      const definition = {
        id: 'test-search-index',
        retry: {
          retryAttempts: 3,
          baseDelay: 1000,
          jitterFactor: 0.1,
        },
      };

      mockCollection.createSearchIndex.mockResolvedValue('test_index');

      defineSearchIndexTools(mockGenkit, mockMongoClient, definition);
      const createTool = mockGenkit.defineTool.mock.calls.find(
        (call) => call[0].name === 'mongodb/test-search-index/create'
      )?.[1];

      const {
        validateSearchIndexCreateOptions,
      } = require('../../src/common/types');
      validateSearchIndexCreateOptions.mockReturnValue({
        dbName: 'testdb',
        collectionName: 'testcollection',
        indexName: 'test_index',
        schema: { mappings: { dynamic: true } },
      });

      await createTool({
        dbName: 'testdb',
        collectionName: 'testcollection',
        indexName: 'test_index',
        schema: { mappings: { dynamic: true } },
      });

      const { retryWithDelay } = require('../../src/common/retry');
      expect(retryWithDelay).toHaveBeenCalledWith(
        expect.any(Function),
        definition.retry
      );
    });
  });

  describe('Search Index tool error handling', () => {
    let ai: any;
    let client: any;
    let collection: any;

    beforeEach(() => {
      ai = { defineTool: jest.fn() };
      collection = {
        createSearchIndex: jest.fn(),
        listSearchIndexes: jest.fn(),
        dropSearchIndex: jest.fn(),
        collectionName: 'testcollection',
      };
      client = {
        db: jest.fn().mockReturnValue({
          collection: jest.fn().mockReturnValue(collection),
        }),
      };

      const { getCollection } = require('../../src/common/connection');
      getCollection.mockReturnValue(collection);
    });

    it('should handle non-Error exceptions in create search index', async () => {
      collection.createSearchIndex.mockRejectedValue(new Error('String error'));
      const {
        defineSearchIndexTools,
      } = require('../../src/tools/search-indexes');
      defineSearchIndexTools(ai, client, { id: 'test' });
      const createCall = ai.defineTool.mock.calls.find(([def]) =>
        def.name.includes('create')
      );
      expect(createCall).toBeDefined();
      const tool = createCall[1];

      const {
        validateSearchIndexCreateOptions,
      } = require('../../src/common/types');
      validateSearchIndexCreateOptions.mockReturnValue({
        dbName: 'db',
        collectionName: 'col',
        indexName: 'test_index',
        schema: { mappings: { dynamic: true } },
      });

      const result = await tool({
        dbName: 'db',
        collectionName: 'col',
        indexName: 'test_index',
        schema: { mappings: { dynamic: true } },
      });
      expect(result.success).toBe(false);
      expect(result.message).toMatch(/String error/);
    });

    it('should handle non-Error exceptions in list search indexes', async () => {
      const { retryWithDelay } = require('../../src/common/retry');
      retryWithDelay.mockImplementation(() => {
        throw 'String error';
      });

      const {
        defineSearchIndexTools,
      } = require('../../src/tools/search-indexes');
      defineSearchIndexTools(ai, client, { id: 'test' });
      const listCall = ai.defineTool.mock.calls.find(([def]) =>
        def.name.includes('list')
      );
      expect(listCall).toBeDefined();
      const tool = listCall[1];

      const {
        validateSearchIndexListOptions,
      } = require('../../src/common/types');
      validateSearchIndexListOptions.mockReturnValue({
        dbName: 'db',
        collectionName: 'col',
      });

      const result = await tool({
        dbName: 'db',
        collectionName: 'col',
      });
      expect(result.success).toBe(false);
      expect(result.message).toMatch(/Unknown error/);
    });

    it('should handle non-Error exceptions in drop search index', async () => {
      collection.dropSearchIndex.mockRejectedValue(new Error('String error'));
      const {
        defineSearchIndexTools,
      } = require('../../src/tools/search-indexes');
      defineSearchIndexTools(ai, client, { id: 'test' });
      const dropCall = ai.defineTool.mock.calls.find(([def]) =>
        def.name.includes('drop')
      );
      expect(dropCall).toBeDefined();
      const tool = dropCall[1];

      const {
        validateSearchIndexDropOptions,
      } = require('../../src/common/types');
      validateSearchIndexDropOptions.mockReturnValue({
        dbName: 'db',
        collectionName: 'col',
        indexName: 'test_index',
      });

      const result = await tool({
        dbName: 'db',
        collectionName: 'col',
        indexName: 'test_index',
      });
      expect(result.success).toBe(false);
      expect(result.message).toMatch(/String error/);
    });

    it('should handle non-Error exceptions in list search indexes with retry', async () => {
      const { retryWithDelay } = require('../../src/common/retry');
      retryWithDelay.mockImplementation(() => {
        throw 'String error';
      });

      const {
        defineSearchIndexTools,
      } = require('../../src/tools/search-indexes');
      defineSearchIndexTools(ai, client, { id: 'test' });
      const listCall = ai.defineTool.mock.calls.find(([def]) =>
        def.name.includes('list')
      );
      expect(listCall).toBeDefined();
      const tool = listCall[1];

      const {
        validateSearchIndexListOptions,
      } = require('../../src/common/types');
      validateSearchIndexListOptions.mockReturnValue({
        dbName: 'db',
        collectionName: 'col',
      });

      const result = await tool({
        dbName: 'db',
        collectionName: 'col',
      });
      expect(result.success).toBe(false);
      expect(result.message).toMatch(/Unknown error/);
    });

    it('should handle non-Error exceptions in drop search index with retry', async () => {
      const { retryWithDelay } = require('../../src/common/retry');
      retryWithDelay.mockImplementation(() => {
        throw 'String error';
      });

      const {
        defineSearchIndexTools,
      } = require('../../src/tools/search-indexes');
      defineSearchIndexTools(ai, client, { id: 'test' });
      const dropCall = ai.defineTool.mock.calls.find(([def]) =>
        def.name.includes('drop')
      );
      expect(dropCall).toBeDefined();
      const tool = dropCall[1];

      const {
        validateSearchIndexDropOptions,
      } = require('../../src/common/types');
      validateSearchIndexDropOptions.mockReturnValue({
        dbName: 'db',
        collectionName: 'col',
        indexName: 'test_index',
      });

      const result = await tool({
        dbName: 'db',
        collectionName: 'col',
        indexName: 'test_index',
      });
      expect(result.success).toBe(false);
      expect(result.message).toMatch(/Unknown error/);
    });

    it('should handle invalid input for create search index', async () => {
      const {
        defineSearchIndexTools,
      } = require('../../src/tools/search-indexes');
      defineSearchIndexTools(ai, client, { id: 'test' });
      const createCall = ai.defineTool.mock.calls.find(([def]) =>
        def.name.includes('create')
      );
      expect(createCall).toBeDefined();
      const tool = createCall[1];

      const {
        validateSearchIndexCreateOptions,
      } = require('../../src/common/types');
      validateSearchIndexCreateOptions.mockImplementation(() => {
        throw new Error('Invalid search index options');
      });

      const result = await tool({
        dbName: '',
        collectionName: '',
        indexName: '',
        schema: {},
      });
      expect(result.success).toBe(false);
      expect(result.message).toMatch(/Invalid search index options/);
    });

    it('should handle invalid input for list search indexes', async () => {
      const {
        defineSearchIndexTools,
      } = require('../../src/tools/search-indexes');
      defineSearchIndexTools(ai, client, { id: 'test' });
      const listCall = ai.defineTool.mock.calls.find(([def]) =>
        def.name.includes('list')
      );
      expect(listCall).toBeDefined();
      const tool = listCall[1];

      const {
        validateSearchIndexListOptions,
      } = require('../../src/common/types');
      validateSearchIndexListOptions.mockImplementation(() => {
        throw new Error('Invalid search index options');
      });

      const result = await tool({
        dbName: '',
        collectionName: '',
      });
      expect(result.success).toBe(false);
      expect(result.message).toMatch(/Invalid search index options/);
    });

    it('should handle invalid input for drop search index', async () => {
      const {
        defineSearchIndexTools,
      } = require('../../src/tools/search-indexes');
      defineSearchIndexTools(ai, client, { id: 'test' });
      const dropCall = ai.defineTool.mock.calls.find(([def]) =>
        def.name.includes('drop')
      );
      expect(dropCall).toBeDefined();
      const tool = dropCall[1];

      const {
        validateSearchIndexDropOptions,
      } = require('../../src/common/types');
      validateSearchIndexDropOptions.mockImplementation(() => {
        throw new Error('Invalid search index options');
      });

      const result = await tool({
        dbName: '',
        collectionName: '',
        indexName: '',
      });
      expect(result.success).toBe(false);
      expect(result.message).toMatch(/Invalid search index options/);
    });
  });
});
