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
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  jest,
} from '@jest/globals';
import { Collection, MongoClient } from 'mongodb';
import {
  closeConnections,
  getCollection,
  getMongoClient,
} from '../../src/common/connection';

jest.mock('mongodb');

const mockMongoClient = {
  connect: jest.fn(),
  close: jest.fn(),
  db: jest.fn(),
} as unknown as jest.Mocked<MongoClient>;

const mockCollection = {} as Collection;

describe('connection utilities', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (MongoClient as jest.MockedClass<typeof MongoClient>).mockImplementation(
      () => mockMongoClient
    );
    mockMongoClient.db.mockReturnValue({
      collection: jest.fn().mockReturnValue(mockCollection),
    } as any);
  });

  afterEach(async () => {
    await closeConnections();
    jest.restoreAllMocks();
  });

  describe('getMongoClient', () => {
    it('should create and connect a new client', async () => {
      mockMongoClient.connect.mockResolvedValue(mockMongoClient);

      const result = await getMongoClient('mongodb://localhost:27017');

      expect(MongoClient).toHaveBeenCalledWith(
        'mongodb://localhost:27017',
        undefined
      );
      expect(mockMongoClient.connect).toHaveBeenCalled();
      expect(result).toBe(mockMongoClient);
    });

    it('should create client with options', async () => {
      mockMongoClient.connect.mockResolvedValue(mockMongoClient);
      const options = { maxPoolSize: 10 };

      const result = await getMongoClient('mongodb://localhost:27017', options);

      expect(MongoClient).toHaveBeenCalledWith(
        'mongodb://localhost:27017',
        options
      );
      expect(mockMongoClient.connect).toHaveBeenCalled();
      expect(result).toBe(mockMongoClient);
    });

    it('should reuse existing client for same connection', async () => {
      mockMongoClient.connect.mockResolvedValue(mockMongoClient);

      const client1 = await getMongoClient('mongodb://localhost:27017');
      const client2 = await getMongoClient('mongodb://localhost:27017');

      expect(client1).toBe(client2);
      expect(MongoClient).toHaveBeenCalledTimes(1);
      expect(mockMongoClient.connect).toHaveBeenCalledTimes(1);
    });

    it('should create separate clients for different connections', async () => {
      mockMongoClient.connect.mockResolvedValue(mockMongoClient);

      const client1 = await getMongoClient('mongodb://localhost:27017');
      const client2 = await getMongoClient('mongodb://localhost:27018');

      expect(client1).toBe(client2);
      expect(MongoClient).toHaveBeenCalledTimes(2);
      expect(mockMongoClient.connect).toHaveBeenCalledTimes(2);
    });

    it('should handle connection errors', async () => {
      const error = new Error('Connection failed');
      mockMongoClient.connect.mockRejectedValue(error);

      await expect(getMongoClient('mongodb://localhost:27017')).rejects.toThrow(
        'Failed to get Mongo client: Connection failed'
      );
    });

    it('should handle non-Error exceptions', async () => {
      mockMongoClient.connect.mockRejectedValue('String error');

      await expect(getMongoClient('mongodb://localhost:27017')).rejects.toThrow(
        'Failed to get Mongo client: Unknown error'
      );
    });
  });

  describe('closeConnections', () => {
    it('should close all connections', async () => {
      mockMongoClient.connect.mockResolvedValue(mockMongoClient);
      mockMongoClient.close.mockResolvedValue(undefined);
      await getMongoClient('mongodb://localhost:27017');
      await closeConnections();

      expect(mockMongoClient.close).toHaveBeenCalled();
    });

    it('should handle close errors gracefully', async () => {
      const error = new Error('Close failed');
      mockMongoClient.close.mockRejectedValue(error);

      await expect(closeConnections()).resolves.toBeUndefined();
    });
  });

  describe('getCollection', () => {
    it('should get collection from client', () => {
      const result = getCollection(mockMongoClient, 'testdb', 'testcollection');

      expect(mockMongoClient.db).toHaveBeenCalledWith('testdb', undefined);
      expect(mockMongoClient.db().collection).toHaveBeenCalledWith(
        'testcollection',
        undefined
      );
      expect(result).toBe(mockCollection);
    });

    it('should get collection with options', () => {
      const dbOptions = { retryWrites: true };
      const collectionOptions = { timeoutMS: 1000 };

      getCollection(
        mockMongoClient,
        'testdb',
        'testcollection',
        dbOptions,
        collectionOptions
      );

      expect(mockMongoClient.db).toHaveBeenCalledWith('testdb', dbOptions);
      expect(mockMongoClient.db().collection).toHaveBeenCalledWith(
        'testcollection',
        collectionOptions
      );
    });
  });
});
