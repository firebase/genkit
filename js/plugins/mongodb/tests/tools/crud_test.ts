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
import { Collection, MongoClient, ObjectId } from 'mongodb';
import { BaseDefinition } from '../../src/common/types';
import { defineCRUDTools, mongoCrudToolsRefArray } from '../../src/tools/crud';

jest.mock('../../src/common/connection');
jest.mock('../../src/common/types');
jest.mock('../../src/common/retry');

const mockCollection = {
  insertOne: jest.fn(),
  findOne: jest.fn(),
  updateOne: jest.fn(),
  deleteOne: jest.fn(),
} as unknown as jest.Mocked<Collection>;

const mockMongoClient = {} as MongoClient;

const mockGenkit = {
  defineTool: jest.fn(),
} as any;

describe('CRUD tools', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { retryWithDelay } = require('../../src/common/retry');
    retryWithDelay.mockImplementation(async (fn, _opts) => {
      try {
        return await fn();
      } catch (error) {
        throw error;
      }
    });
  });

  describe('mongoCrudToolsRefArray', () => {
    it('should return array of tool names', () => {
      const toolNames = mongoCrudToolsRefArray('test-crud');

      expect(Array.isArray(toolNames)).toBe(true);
      expect(toolNames).toEqual([
        'mongodb/test-crud/create',
        'mongodb/test-crud/read',
        'mongodb/test-crud/update',
        'mongodb/test-crud/delete',
      ]);
    });
  });

  describe('defineCRUDTools', () => {
    it('should define CRUD tools when definition is provided', () => {
      const definition = {
        id: 'test-crud',
      };

      defineCRUDTools(mockGenkit, mockMongoClient, definition);

      expect(mockGenkit.defineTool).toHaveBeenCalledTimes(4);
    });

    it('should not define tools when definition is missing', () => {
      defineCRUDTools(mockGenkit, mockMongoClient, undefined);

      expect(mockGenkit.defineTool).not.toHaveBeenCalled();
    });

    it('should not define tools when definition id is missing', () => {
      const definition = {
        retry: {
          retryAttempts: 3,
        },
      } as unknown as BaseDefinition;

      defineCRUDTools(mockGenkit, mockMongoClient, definition);

      expect(mockGenkit.defineTool).not.toHaveBeenCalled();
    });
  });

  describe('CRUD tool functions', () => {
    beforeEach(() => {
      const { getCollection } = require('../../src/common/connection');
      getCollection.mockReturnValue(mockCollection);
    });

    describe('create tool', () => {
      it('should create document successfully', async () => {
        const definition = { id: 'test-crud' };
        const mockObjectId = new ObjectId('687a163e0914005f62392d14');

        mockCollection.insertOne.mockResolvedValue({
          acknowledged: true,
          insertedId: mockObjectId,
        });

        defineCRUDTools(mockGenkit, mockMongoClient, definition);
        const createTool = mockGenkit.defineTool.mock.calls.find(
          (call) => call[0].name === 'mongodb/test-crud/create'
        )?.[1];

        const { validateCreateOptions } = require('../../src/common/types');
        validateCreateOptions.mockReturnValue({
          dbName: 'testdb',
          collectionName: 'testcollection',
          document: { name: 'test' },
        });

        const result = await createTool({
          dbName: 'testdb',
          collectionName: 'testcollection',
          document: { name: 'test' },
        });

        expect(mockCollection.insertOne).toHaveBeenCalledWith({ name: 'test' });
        expect(result).toEqual({
          insertedId: mockObjectId.toString(),
          success: true,
          message:
            'Document created successfully with ID: 687a163e0914005f62392d14',
        });
      });

      it('should handle create errors', async () => {
        const definition = { id: 'test-crud' };

        mockCollection.insertOne.mockRejectedValue(new Error('Insert failed'));

        defineCRUDTools(mockGenkit, mockMongoClient, definition);
        const createTool = mockGenkit.defineTool.mock.calls.find(
          (call) => call[0].name === 'mongodb/test-crud/create'
        )?.[1];

        const { validateCreateOptions } = require('../../src/common/types');
        validateCreateOptions.mockReturnValue({
          dbName: 'testdb',
          collectionName: 'testcollection',
          document: { name: 'test' },
        });

        const result = await createTool({
          dbName: 'testdb',
          collectionName: 'testcollection',
          document: { name: 'test' },
        });

        expect(result).toEqual({
          insertedId: '',
          success: false,
          message: 'Failed to create document: Insert failed',
        });
      });
    });

    describe('read tool', () => {
      it('should read document successfully', async () => {
        const definition = { id: 'test-crud' };
        const mockDocument = { _id: new ObjectId(), name: 'test' };

        mockCollection.findOne.mockResolvedValue(mockDocument);

        defineCRUDTools(mockGenkit, mockMongoClient, definition);
        const readTool = mockGenkit.defineTool.mock.calls.find(
          (call) => call[0].name === 'mongodb/test-crud/read'
        )?.[1];

        const { validateReadOptions } = require('../../src/common/types');
        validateReadOptions.mockReturnValue({
          dbName: 'testdb',
          collectionName: 'testcollection',
          id: '507f1f77bcf86cd799439011',
        });

        const result = await readTool({
          dbName: 'testdb',
          collectionName: 'testcollection',
          id: '507f1f77bcf86cd799439011',
        });

        expect(mockCollection.findOne).toHaveBeenCalledWith({
          _id: new ObjectId('507f1f77bcf86cd799439011'),
        });
        expect(result).toEqual({
          document: mockDocument,
          success: true,
          message: 'Document found successfully',
        });
      });

      it('should handle document not found', async () => {
        const definition = { id: 'test-crud' };

        mockCollection.findOne.mockResolvedValue(null);

        defineCRUDTools(mockGenkit, mockMongoClient, definition);
        const readTool = mockGenkit.defineTool.mock.calls.find(
          (call) => call[0].name === 'mongodb/test-crud/read'
        )?.[1];

        const { validateReadOptions } = require('../../src/common/types');
        validateReadOptions.mockReturnValue({
          dbName: 'testdb',
          collectionName: 'testcollection',
          id: '507f1f77bcf86cd799439011',
        });

        const result = await readTool({
          dbName: 'testdb',
          collectionName: 'testcollection',
          id: '507f1f77bcf86cd799439011',
        });

        expect(result).toEqual({
          document: null,
          success: true,
          message: 'Document not found',
        });
      });
    });

    describe('update tool', () => {
      it('should update document successfully', async () => {
        const definition = { id: 'test-crud' };

        mockCollection.updateOne.mockResolvedValue({
          acknowledged: true,
          matchedCount: 1,
          modifiedCount: 1,
          upsertedId: null,
          upsertedCount: 0,
        });

        defineCRUDTools(mockGenkit, mockMongoClient, definition);
        const updateTool = mockGenkit.defineTool.mock.calls.find(
          (call) => call[0].name === 'mongodb/test-crud/update'
        )?.[1];

        const { validateUpdateOptions } = require('../../src/common/types');
        validateUpdateOptions.mockReturnValue({
          dbName: 'testdb',
          collectionName: 'testcollection',
          id: '507f1f77bcf86cd799439011',
          update: { $set: { status: 'updated' } },
        });

        const result = await updateTool({
          dbName: 'testdb',
          collectionName: 'testcollection',
          id: '507f1f77bcf86cd799439011',
          update: { $set: { status: 'updated' } },
        });

        expect(mockCollection.updateOne).toHaveBeenCalledWith(
          { _id: new ObjectId('507f1f77bcf86cd799439011') },
          { $set: { status: 'updated' } },
          undefined
        );
        expect(result).toEqual({
          matchedCount: 1,
          modifiedCount: 1,
          upsertedId: null,
          success: true,
          message: 'Update operation completed. Matched: 1, Modified: 1',
        });
      });
    });

    describe('delete tool', () => {
      it('should delete document successfully', async () => {
        const definition = { id: 'test-crud' };

        mockCollection.deleteOne.mockResolvedValue({
          acknowledged: true,
          deletedCount: 1,
        });

        defineCRUDTools(mockGenkit, mockMongoClient, definition);
        const deleteTool = mockGenkit.defineTool.mock.calls.find(
          (call) => call[0].name === 'mongodb/test-crud/delete'
        )?.[1];

        const { validateDeleteOptions } = require('../../src/common/types');
        validateDeleteOptions.mockReturnValue({
          dbName: 'testdb',
          collectionName: 'testcollection',
          id: '507f1f77bcf86cd799439011',
        });

        const result = await deleteTool({
          dbName: 'testdb',
          collectionName: 'testcollection',
          id: '507f1f77bcf86cd799439011',
        });

        expect(mockCollection.deleteOne).toHaveBeenCalledWith({
          _id: new ObjectId('507f1f77bcf86cd799439011'),
        });
        expect(result).toEqual({
          deletedCount: 1,
          success: true,
          message: 'Delete operation completed. Deleted: 1 document(s)',
        });
      });
    });
  });
});

describe('CRUD tool error handling', () => {
  let ai: any;
  let client: any;
  let collection: any;

  beforeEach(() => {
    ai = { defineTool: jest.fn() };
    collection = {
      insertOne: jest.fn(),
      findOne: jest.fn(),
      updateOne: jest.fn(),
      deleteOne: jest.fn(),
    };
    client = {
      db: jest
        .fn()
        .mockReturnValue({ collection: jest.fn().mockReturnValue(collection) }),
    };

    const { getCollection } = require('../../src/common/connection');
    getCollection.mockReturnValue(collection);
  });

  it('should handle insertOne failure', async () => {
    collection.insertOne.mockRejectedValue(new Error('Insert failed'));
    const { defineCRUDTools } = require('../../src/tools/crud');
    defineCRUDTools(ai, client, { id: 'test' });
    const insertCall = ai.defineTool.mock.calls.find(([def]) =>
      def.name.includes('create')
    );
    expect(insertCall).toBeDefined();
    const tool = insertCall[1];

    const { validateCreateOptions } = require('../../src/common/types');
    validateCreateOptions.mockReturnValue({
      dbName: 'db',
      collectionName: 'col',
      document: {},
    });

    const result = await tool({
      dbName: 'db',
      collectionName: 'col',
      document: {},
    });
    expect(result.success).toBe(false);
    expect(result.message).toMatch(/Insert failed/);
  });

  it('should handle findOne failure', async () => {
    collection.findOne.mockRejectedValue(new Error('Find failed'));
    const { defineCRUDTools } = require('../../src/tools/crud');
    defineCRUDTools(ai, client, { id: 'test' });
    const findCall = ai.defineTool.mock.calls.find(([def]) =>
      def.name.includes('read')
    );
    expect(findCall).toBeDefined();
    const tool = findCall[1];

    const { validateReadOptions } = require('../../src/common/types');
    validateReadOptions.mockReturnValue({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
    });

    const result = await tool({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
    });
    expect(result.success).toBe(false);
    expect(result.message).toMatch(/Find failed/);
  });

  it('should handle updateOne failure', async () => {
    collection.updateOne.mockRejectedValue(new Error('Update failed'));
    const { defineCRUDTools } = require('../../src/tools/crud');
    defineCRUDTools(ai, client, { id: 'test' });
    const updateCall = ai.defineTool.mock.calls.find(([def]) =>
      def.name.includes('update')
    );
    expect(updateCall).toBeDefined();
    const tool = updateCall[1];

    const { validateUpdateOptions } = require('../../src/common/types');
    validateUpdateOptions.mockReturnValue({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
      update: {},
    });

    const result = await tool({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
      update: {},
    });
    expect(result.success).toBe(false);
    expect(result.message).toMatch(/Update failed/);
  });

  it('should handle deleteOne failure', async () => {
    collection.deleteOne.mockRejectedValue(new Error('Delete failed'));
    const { defineCRUDTools } = require('../../src/tools/crud');
    defineCRUDTools(ai, client, { id: 'test' });
    const deleteCall = ai.defineTool.mock.calls.find(([def]) =>
      def.name.includes('delete')
    );
    expect(deleteCall).toBeDefined();
    const tool = deleteCall[1];

    const { validateDeleteOptions } = require('../../src/common/types');
    validateDeleteOptions.mockReturnValue({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
    });

    const result = await tool({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
    });
    expect(result.success).toBe(false);
    expect(result.message).toMatch(/Delete failed/);
  });

  it('should handle findById not found', async () => {
    collection.findOne.mockResolvedValue(null);
    const { defineCRUDTools } = require('../../src/tools/crud');
    defineCRUDTools(ai, client, { id: 'test' });
    const findCall = ai.defineTool.mock.calls.find(([def]) =>
      def.name.includes('read')
    );
    expect(findCall).toBeDefined();
    const tool = findCall[1];

    const { validateReadOptions } = require('../../src/common/types');
    validateReadOptions.mockReturnValue({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
    });

    const result = await tool({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
    });
    expect(result.success).toBe(true);
    expect(result.document).toBeNull();
    expect(result.message).toMatch(/not found/);
  });

  it('should handle invalid input for update', async () => {
    const { defineCRUDTools } = require('../../src/tools/crud');
    defineCRUDTools(ai, client, { id: 'test' });
    const updateCall = ai.defineTool.mock.calls.find(([def]) =>
      def.name.includes('update')
    );
    expect(updateCall).toBeDefined();
    const tool = updateCall[1];

    const { validateUpdateOptions } = require('../../src/common/types');
    validateUpdateOptions.mockImplementation(() => {
      throw new Error('Invalid Mongo options');
    });

    const result = await tool({
      dbName: '',
      collectionName: '',
      id: 'invalid-id',
      update: {},
    });
    expect(result.success).toBe(false);
    expect(result.message).toMatch(/Invalid Mongo options/);
  });

  it('should handle invalid input for delete', async () => {
    const { defineCRUDTools } = require('../../src/tools/crud');
    defineCRUDTools(ai, client, { id: 'test' });
    const deleteCall = ai.defineTool.mock.calls.find(([def]) =>
      def.name.includes('delete')
    );
    expect(deleteCall).toBeDefined();
    const tool = deleteCall[1];

    const { validateDeleteOptions } = require('../../src/common/types');
    validateDeleteOptions.mockImplementation(() => {
      throw new Error('Invalid Mongo options');
    });

    const result = await tool({
      dbName: '',
      collectionName: '',
      id: 'invalid-id',
    });
    expect(result.success).toBe(false);
    expect(result.message).toMatch(/Invalid Mongo options/);
  });

  it('should handle non-Error exceptions in create', async () => {
    collection.insertOne.mockRejectedValue('String error');
    const { defineCRUDTools } = require('../../src/tools/crud');
    defineCRUDTools(ai, client, { id: 'test' });
    const insertCall = ai.defineTool.mock.calls.find(([def]) =>
      def.name.includes('create')
    );
    expect(insertCall).toBeDefined();
    const tool = insertCall[1];

    const { validateCreateOptions } = require('../../src/common/types');
    validateCreateOptions.mockReturnValue({
      dbName: 'db',
      collectionName: 'col',
      document: {},
    });

    const result = await tool({
      dbName: 'db',
      collectionName: 'col',
      document: {},
    });
    expect(result.success).toBe(false);
    expect(result.message).toMatch(/Unknown error/);
  });

  it('should handle non-Error exceptions in read', async () => {
    collection.findOne.mockRejectedValue('String error');
    const { defineCRUDTools } = require('../../src/tools/crud');
    defineCRUDTools(ai, client, { id: 'test' });
    const findCall = ai.defineTool.mock.calls.find(([def]) =>
      def.name.includes('read')
    );
    expect(findCall).toBeDefined();
    const tool = findCall[1];

    const { validateReadOptions } = require('../../src/common/types');
    validateReadOptions.mockReturnValue({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
    });

    const result = await tool({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
    });
    expect(result.success).toBe(false);
    expect(result.message).toMatch(/Unknown error/);
  });

  it('should handle non-Error exceptions in update', async () => {
    collection.updateOne.mockRejectedValue('String error');
    const { defineCRUDTools } = require('../../src/tools/crud');
    defineCRUDTools(ai, client, { id: 'test' });
    const updateCall = ai.defineTool.mock.calls.find(([def]) =>
      def.name.includes('update')
    );
    expect(updateCall).toBeDefined();
    const tool = updateCall[1];

    const { validateUpdateOptions } = require('../../src/common/types');
    validateUpdateOptions.mockReturnValue({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
      update: {},
    });

    const result = await tool({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
      update: {},
    });
    expect(result.success).toBe(false);
    expect(result.message).toMatch(/Unknown error/);
  });

  it('should handle non-Error exceptions in delete', async () => {
    collection.deleteOne.mockRejectedValue('String error');
    const { defineCRUDTools } = require('../../src/tools/crud');
    defineCRUDTools(ai, client, { id: 'test' });
    const deleteCall = ai.defineTool.mock.calls.find(([def]) =>
      def.name.includes('delete')
    );
    expect(deleteCall).toBeDefined();
    const tool = deleteCall[1];

    const { validateDeleteOptions } = require('../../src/common/types');
    validateDeleteOptions.mockReturnValue({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
    });

    const result = await tool({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
    });
    expect(result.success).toBe(false);
    expect(result.message).toMatch(/Unknown error/);
  });

  it('should handle update with upsertedId', async () => {
    const mockUpsertedId = new ObjectId('507f1f77bcf86cd799439011');
    collection.updateOne.mockResolvedValue({
      matchedCount: 0,
      modifiedCount: 1,
      upsertedId: mockUpsertedId,
    });
    const { defineCRUDTools } = require('../../src/tools/crud');
    defineCRUDTools(ai, client, { id: 'test' });
    const updateCall = ai.defineTool.mock.calls.find(([def]) =>
      def.name.includes('update')
    );
    expect(updateCall).toBeDefined();
    const tool = updateCall[1];

    const { validateUpdateOptions } = require('../../src/common/types');
    validateUpdateOptions.mockReturnValue({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
      update: {},
    });

    const result = await tool({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
      update: {},
    });
    expect(result.success).toBe(true);
    expect(result.upsertedId).toBe(mockUpsertedId.toString());
  });

  it('should handle update without upsertedId', async () => {
    collection.updateOne.mockResolvedValue({
      matchedCount: 1,
      modifiedCount: 1,
      upsertedId: null,
    });
    const { defineCRUDTools } = require('../../src/tools/crud');
    defineCRUDTools(ai, client, { id: 'test' });
    const updateCall = ai.defineTool.mock.calls.find(([def]) =>
      def.name.includes('update')
    );
    expect(updateCall).toBeDefined();
    const tool = updateCall[1];

    const { validateUpdateOptions } = require('../../src/common/types');
    validateUpdateOptions.mockReturnValue({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
      update: {},
    });

    const result = await tool({
      dbName: 'db',
      collectionName: 'col',
      id: '507f1f77bcf86cd799439011',
      update: {},
    });
    expect(result.success).toBe(true);
    expect(result.upsertedId).toBeNull();
  });
});
