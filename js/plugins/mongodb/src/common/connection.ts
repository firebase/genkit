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
  Collection,
  CollectionOptions,
  DbOptions,
  MongoClient,
  MongoClientOptions,
} from 'mongodb';

const connectionPool = new Map<string, MongoClient>();

/**
 * Creates a unique key for a MongoDB connection based on URL and options.
 *
 * @param url - MongoDB connection URL
 * @param options - Optional MongoDB client options
 * @returns A string key representing the connection configuration
 */
const createConnectionKey = (
  url: string,
  options?: MongoClientOptions
): string =>
  JSON.stringify({
    url,
    options: options || {},
  });

/**
 * Safely closes a MongoDB client connection.
 *
 * @param client - The MongoDB client to close
 */
async function closeMongoClient(client: MongoClient): Promise<void> {
  try {
    await client.close();
  } catch (error) {
    console.error('Error closing Mongo client connection:', error);
  }
}

/**
 * Gets or creates a MongoDB client connection.
 *
 * This function implements connection pooling to reuse existing connections
 * with the same URL and options configuration.
 *
 * @param url - MongoDB connection URL
 * @param options - Optional MongoDB client options
 * @returns A connected MongoDB client
 * @throws {Error} If connection fails
 */
export async function getMongoClient(
  url: string,
  options?: MongoClientOptions
): Promise<MongoClient> {
  try {
    const connectionKey = createConnectionKey(url, options);
    if (connectionPool.has(connectionKey)) {
      return connectionPool.get(connectionKey)!;
    }

    const client = new MongoClient(url, options);
    await client.connect();

    connectionPool.set(connectionKey, client);

    return client;
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : 'Unknown error';
    throw new Error(`Failed to get Mongo client: ${errorMessage}`);
  }
}

/**
 * Closes all MongoDB client connections in the connection pool.
 *
 * This function should be called during application shutdown to properly
 * clean up database connections.
 */
export async function closeConnections(): Promise<void> {
  try {
    const closePromises = Array.from(connectionPool.entries()).map(
      ([key, client]) =>
        closeMongoClient(client).then(() => connectionPool.delete(key))
    );
    await Promise.allSettled(closePromises);
  } catch (error) {
    console.error('Error during connection cleanup:', error);
  }
}

/**
 * Gets a MongoDB collection with specified database and collection options.
 *
 * @param client - MongoDB client instance
 * @param dbName - Database name
 * @param collectionName - Collection name
 * @param dbOptions - Optional database options
 * @param collectionOptions - Optional collection options
 * @returns MongoDB collection instance
 */
export function getCollection(
  client: MongoClient,
  dbName: string,
  collectionName: string,
  dbOptions?: DbOptions,
  collectionOptions?: CollectionOptions
): Collection {
  return client
    .db(dbName, dbOptions)
    .collection(collectionName, collectionOptions);
}
