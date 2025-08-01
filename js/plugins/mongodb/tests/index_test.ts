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
import * as indexModule from '../src/index';
import mongodbDefault, { mongodb } from '../src/index';

// Mock dependencies
jest.mock('../src/common/connection');
jest.mock('../src/common/types');
jest.mock('../src/core/indexer');
jest.mock('../src/core/retriever');
jest.mock('../src/tools/crud');
jest.mock('../src/tools/search-indexes');

// Mock genkitPlugin
jest.mock('genkit/plugin', () => ({
  genkitPlugin: jest.fn((name, configure) => ({
    name,
    configure: async (ai: any) => {
      await (configure as any)(ai);
    },
  })),
}));

const mockGenkit = {
  defineIndexer: jest.fn(),
  defineRetriever: jest.fn(),
  defineTool: jest.fn(),
} as any;

describe('mongodb plugin', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('mongodb function', () => {
    it('should create plugin with valid connections', () => {
      const connections = [
        {
          url: 'mongodb://localhost:27017',
          id: 'test-connection',
          indexer: {
            id: 'test-indexer',
          },
          retriever: {
            id: 'test-retriever',
          },
        },
      ];

      const plugin = mongodb(connections);

      expect(plugin).toBeDefined();
      expect(plugin.name).toBe('mongodb');
    });

    it('should throw error for empty connections array', () => {
      expect(() => mongodb([])).toThrow(
        'At least one Mongo connection must be provided'
      );
    });

    it('should throw error for null connections', () => {
      expect(() => mongodb(null as any)).toThrow(
        'At least one Mongo connection must be provided'
      );
    });

    it('should throw error for undefined connections', () => {
      expect(() => mongodb(undefined as any)).toThrow(
        'At least one Mongo connection must be provided'
      );
    });
  });

  describe('default export', () => {
    it('should export the same function as named export', () => {
      const connections = [
        {
          url: 'mongodb://localhost:27017',
          id: 'test-connection',
          indexer: {
            id: 'test-indexer',
          },
          retriever: {
            id: 'test-retriever',
          },
        },
      ];

      const namedPlugin = mongodb(connections);
      const defaultPlugin = mongodbDefault(connections);

      expect(defaultPlugin).toBeDefined();
      expect(defaultPlugin.name).toBe('mongodb');
      expect(defaultPlugin.name).toBe(namedPlugin.name);
    });

    it('should throw error for empty connections array', () => {
      expect(() => mongodbDefault([])).toThrow(
        'At least one Mongo connection must be provided'
      );
    });

    it('should throw error for null connections', () => {
      expect(() => mongodbDefault(null as any)).toThrow(
        'At least one Mongo connection must be provided'
      );
    });

    it('should throw error for undefined connections', () => {
      expect(() => mongodbDefault(undefined as any)).toThrow(
        'At least one Mongo connection must be provided'
      );
    });

    it('should test default export initialization', async () => {
      const connections = [
        {
          url: 'mongodb://localhost:27017',
          id: 'test-connection',
          indexer: {
            id: 'test-indexer',
          },
          retriever: {
            id: 'test-retriever',
          },
          crudTools: {
            id: 'test-crud',
          },
          searchIndexTools: {
            id: 'test-search-index',
          },
        },
      ];

      const { getMongoClient } = require('../src/common/connection');
      const mockClient = { connect: jest.fn() };
      getMongoClient.mockResolvedValue(mockClient);

      const { validateConnection } = require('../src/common/types');
      validateConnection.mockReturnValue(connections[0]);

      const { defineIndexer } = require('../src/core/indexer');
      const { defineRetriever } = require('../src/core/retriever');
      const { defineCRUDTools } = require('../src/tools/crud');
      const { defineSearchIndexTools } = require('../src/tools/search-indexes');

      const plugin = mongodbDefault(connections);

      const { genkitPlugin } = require('genkit/plugin');
      const mockPlugin = genkitPlugin.mock.results[0].value;
      await mockPlugin.configure(mockGenkit);

      expect(plugin).toBeDefined();
      expect(plugin.name).toBe('mongodb');
      expect(getMongoClient).toHaveBeenCalledWith(
        'mongodb://localhost:27017',
        undefined
      );
      expect(validateConnection).toHaveBeenCalledWith(connections[0]);
      expect(defineIndexer).toHaveBeenCalledWith(
        mockGenkit,
        mockClient,
        connections[0].indexer
      );
      expect(defineRetriever).toHaveBeenCalledWith(
        mockGenkit,
        mockClient,
        connections[0].retriever
      );
      expect(defineCRUDTools).toHaveBeenCalledWith(
        mockGenkit,
        mockClient,
        connections[0].crudTools
      );
      expect(defineSearchIndexTools).toHaveBeenCalledWith(
        mockGenkit,
        mockClient,
        connections[0].searchIndexTools
      );
    });

    it('should test default export via module namespace', () => {
      const connections = [
        {
          url: 'mongodb://localhost:27017',
          id: 'test-connection',
          indexer: {
            id: 'test-indexer',
          },
          retriever: {
            id: 'test-retriever',
          },
        },
      ];

      const plugin = indexModule.default(connections);
      expect(plugin).toBeDefined();
      expect(plugin.name).toBe('mongodb');
    });
  });

  describe('named exports', () => {
    it('should export mongoIndexerRef', () => {
      expect(indexModule.mongoIndexerRef).toBeDefined();
    });

    it('should export mongoRetrieverRef', () => {
      expect(indexModule.mongoRetrieverRef).toBeDefined();
    });

    it('should export mongoCrudToolsRefArray', () => {
      expect(indexModule.mongoCrudToolsRefArray).toBeDefined();
    });

    it('should export mongoSearchIndexToolsRefArray', () => {
      expect(indexModule.mongoSearchIndexToolsRefArray).toBeDefined();
    });
  });

  describe('plugin initialization', () => {
    it('should initialize plugin successfully', async () => {
      const connections = [
        {
          url: 'mongodb://localhost:27017',
          id: 'test-connection',
          indexer: {
            id: 'test-indexer',
          },
          retriever: {
            id: 'test-retriever',
          },
          crudTools: {
            id: 'test-crud',
          },
          searchIndexTools: {
            id: 'test-search-index',
          },
        },
      ];

      const { getMongoClient } = require('../src/common/connection');
      const mockClient = { connect: jest.fn() };
      getMongoClient.mockResolvedValue(mockClient);

      const { validateConnection } = require('../src/common/types');
      validateConnection.mockReturnValue(connections[0]);

      const { defineIndexer } = require('../src/core/indexer');
      const { defineRetriever } = require('../src/core/retriever');
      const { defineCRUDTools } = require('../src/tools/crud');
      const { defineSearchIndexTools } = require('../src/tools/search-indexes');

      mongodb(connections);

      const { genkitPlugin } = require('genkit/plugin');
      const mockPlugin = genkitPlugin.mock.results[0].value;
      await mockPlugin.configure(mockGenkit);

      expect(getMongoClient).toHaveBeenCalledWith(
        'mongodb://localhost:27017',
        undefined
      );
      expect(validateConnection).toHaveBeenCalledWith(connections[0]);
      expect(defineIndexer).toHaveBeenCalledWith(
        mockGenkit,
        mockClient,
        connections[0].indexer
      );
      expect(defineRetriever).toHaveBeenCalledWith(
        mockGenkit,
        mockClient,
        connections[0].retriever
      );
      expect(defineCRUDTools).toHaveBeenCalledWith(
        mockGenkit,
        mockClient,
        connections[0].crudTools
      );
      expect(defineSearchIndexTools).toHaveBeenCalledWith(
        mockGenkit,
        mockClient,
        connections[0].searchIndexTools
      );
    });

    it('should handle multiple connections', async () => {
      const connections = [
        {
          url: 'mongodb://localhost:27017',
          id: 'connection1',
          indexer: { id: 'indexer1' },
        },
        {
          url: 'mongodb://localhost:27018',
          id: 'connection2',
          retriever: { id: 'retriever2' },
        },
      ];

      const { getMongoClient } = require('../src/common/connection');
      const mockClient1 = { connect: jest.fn() };
      const mockClient2 = { connect: jest.fn() };
      getMongoClient
        .mockResolvedValueOnce(mockClient1)
        .mockResolvedValueOnce(mockClient2);

      const { validateConnection } = require('../src/common/types');
      validateConnection.mockImplementation((conn) => conn);

      const { defineIndexer } = require('../src/core/indexer');
      const { defineRetriever } = require('../src/core/retriever');
      const { defineCRUDTools } = require('../src/tools/crud');
      const { defineSearchIndexTools } = require('../src/tools/search-indexes');

      mongodb(connections);

      const { genkitPlugin } = require('genkit/plugin');
      const mockPlugin = genkitPlugin.mock.results[0].value;
      await mockPlugin.configure(mockGenkit);

      expect(getMongoClient).toHaveBeenCalledTimes(2);
      expect(validateConnection).toHaveBeenCalledTimes(2);
      expect(defineIndexer).toHaveBeenCalledTimes(2);
      expect(defineRetriever).toHaveBeenCalledTimes(2);
      expect(defineCRUDTools).toHaveBeenCalledTimes(2);
      expect(defineSearchIndexTools).toHaveBeenCalledTimes(2);
    });

    it('should handle initialization errors', async () => {
      const connections = [
        {
          url: 'mongodb://localhost:27017',
          id: 'test-connection',
          indexer: { id: 'test-indexer' },
        },
      ];

      const { getMongoClient } = require('../src/common/connection');
      getMongoClient.mockRejectedValue(new Error('Connection failed'));

      const { closeConnections } = require('../src/common/connection');

      mongodb(connections);

      const { genkitPlugin } = require('genkit/plugin');
      const mockPlugin = genkitPlugin.mock.results[0].value;
      await expect(mockPlugin.configure(mockGenkit)).rejects.toThrow(
        'Mongo plugin initialization failed: Connection failed'
      );

      expect(closeConnections).toHaveBeenCalled();
    });

    it('should handle validation errors', async () => {
      const connections = [
        {
          url: 'invalid-url',
          id: 'test-connection',
          indexer: { id: 'test-indexer' },
        },
      ];

      const { validateConnection } = require('../src/common/types');
      validateConnection.mockImplementation(() => {
        throw new Error('Invalid connection');
      });

      const { closeConnections } = require('../src/common/connection');

      mongodb(connections);

      const { genkitPlugin } = require('genkit/plugin');
      const mockPlugin = genkitPlugin.mock.results[0].value;
      await expect(mockPlugin.configure(mockGenkit)).rejects.toThrow(
        'Mongo plugin initialization failed: Invalid connection'
      );

      expect(closeConnections).toHaveBeenCalled();
    });

    it('should handle unknown errors', async () => {
      const connections = [
        {
          url: 'mongodb://localhost:27017',
          id: 'test-connection',
          indexer: { id: 'test-indexer' },
        },
      ];

      const { getMongoClient } = require('../src/common/connection');
      getMongoClient.mockRejectedValue('String error');

      const { closeConnections } = require('../src/common/connection');

      mongodb(connections);

      const { genkitPlugin } = require('genkit/plugin');
      const mockPlugin = genkitPlugin.mock.results[0].value;
      await expect(mockPlugin.configure(mockGenkit)).rejects.toThrow(
        'Mongo plugin initialization failed: Invalid connection'
      );

      expect(closeConnections).toHaveBeenCalled();
    });
  });
});
