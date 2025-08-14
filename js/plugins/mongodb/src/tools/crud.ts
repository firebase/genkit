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

import { Genkit } from 'genkit';
import { MongoClient, ObjectId } from 'mongodb';
import { getCollection } from '../common/connection';
import { CRUD_TOOL_ID, toolRef } from '../common/constants';
import { retryWithDelay } from '../common/retry';
import {
  BaseDefinition,
  InputCreateSchema,
  InputDeleteSchema,
  InputReadSchema,
  InputUpdateSchema,
  OutputCreateSchema,
  OutputDeleteSchema,
  OutputReadSchema,
  OutputUpdateSchema,
  validateCreateOptions,
  validateDeleteOptions,
  validateReadOptions,
  validateUpdateOptions,
} from '../common/types';

/**
 * Configures the MongoDB insert tool for creating new documents.
 *
 * @param ai - Genkit AI instance
 * @param client - MongoDB client
 * @param options - Tool configuration options
 */
function configureInsertTool(
  ai: Genkit,
  client: MongoClient,
  options: BaseDefinition
) {
  ai.defineTool(
    {
      name: toolRef(options.id, CRUD_TOOL_ID.create),
      description: `Create a new document in MongoDB`,
      inputSchema: InputCreateSchema,
      outputSchema: OutputCreateSchema,
    },
    async (input) => {
      try {
        const parsedInput = validateCreateOptions(input);

        const collection = getCollection(
          client,
          parsedInput.dbName,
          parsedInput.collectionName,
          parsedInput.dbOptions,
          parsedInput.collectionOptions
        );

        const result = await retryWithDelay(
          async () => await collection.insertOne(parsedInput.document),
          options.retry
        );

        return {
          insertedId: result.insertedId.toString(),
          success: true,
          message: `Document created successfully with ID: ${result.insertedId}`,
        };
      } catch (error) {
        return {
          insertedId: '',
          success: false,
          message: `Failed to create document: ${error instanceof Error ? error.message : 'Unknown error'}`,
        };
      }
    }
  );
}

/**
 * Configures the MongoDB find by ID tool for retrieving documents.
 *
 * @param ai - Genkit AI instance
 * @param client - MongoDB client
 * @param options - Tool configuration options
 */
function configureFindByIdTool(
  ai: Genkit,
  client: MongoClient,
  options: BaseDefinition
) {
  ai.defineTool(
    {
      name: toolRef(options.id, CRUD_TOOL_ID.read),
      description: `Retrieve a document by its ID from MongoDB`,
      inputSchema: InputReadSchema,
      outputSchema: OutputReadSchema,
    },
    async (input) => {
      try {
        const parsedInput = validateReadOptions(input);

        const collection = getCollection(
          client,
          parsedInput.dbName,
          parsedInput.collectionName,
          parsedInput.dbOptions,
          parsedInput.collectionOptions
        );

        const result = await retryWithDelay(
          async () =>
            await collection.findOne({ _id: new ObjectId(parsedInput.id) }),
          options.retry
        );

        return {
          document: result,
          success: true,
          message: result
            ? 'Document found successfully'
            : 'Document not found',
        };
      } catch (error) {
        return {
          document: null,
          success: false,
          message: `Failed to retrieve document: ${error instanceof Error ? error.message : 'Unknown error'}`,
        };
      }
    }
  );
}

/**
 * Configures the MongoDB update tool for modifying existing documents.
 *
 * @param ai - Genkit AI instance
 * @param client - MongoDB client
 * @param options - Tool configuration options
 */
function configureUpdateTool(
  ai: Genkit,
  client: MongoClient,
  options: BaseDefinition
) {
  ai.defineTool(
    {
      name: toolRef(options.id, CRUD_TOOL_ID.update),
      description: `Update a document by its ID in MongoDB`,
      inputSchema: InputUpdateSchema,
      outputSchema: OutputUpdateSchema,
    },
    async (input) => {
      try {
        const parsedInput = validateUpdateOptions(input);

        const collection = getCollection(
          client,
          parsedInput.dbName,
          parsedInput.collectionName,
          parsedInput.dbOptions,
          parsedInput.collectionOptions
        );

        const result = await retryWithDelay(
          async () =>
            await collection.updateOne(
              { _id: new ObjectId(parsedInput.id) },
              parsedInput.update,
              parsedInput.options
            ),
          options.retry
        );

        return {
          matchedCount: result.matchedCount,
          modifiedCount: result.modifiedCount,
          upsertedId: result.upsertedId?.toString() || null,
          success: true,
          message: `Update operation completed. Matched: ${result.matchedCount}, Modified: ${result.modifiedCount}`,
        };
      } catch (error) {
        return {
          matchedCount: 0,
          modifiedCount: 0,
          upsertedId: null,
          success: false,
          message: `Failed to update document: ${error instanceof Error ? error.message : 'Unknown error'}`,
        };
      }
    }
  );
}

/**
 * Configures the MongoDB delete tool for removing documents.
 *
 * @param ai - Genkit AI instance
 * @param client - MongoDB client
 * @param options - Tool configuration options
 */
function configureDeleteTool(
  ai: Genkit,
  client: MongoClient,
  options: BaseDefinition
) {
  ai.defineTool(
    {
      name: toolRef(options.id, CRUD_TOOL_ID.delete),
      description: `Delete a document by its ID from MongoDB`,
      inputSchema: InputDeleteSchema,
      outputSchema: OutputDeleteSchema,
    },
    async (input) => {
      try {
        const parsedInput = validateDeleteOptions(input);

        const collection = getCollection(
          client,
          parsedInput.dbName,
          parsedInput.collectionName,
          parsedInput.dbOptions,
          parsedInput.collectionOptions
        );

        const result = await retryWithDelay(
          async () =>
            await collection.deleteOne({ _id: new ObjectId(parsedInput.id) }),
          options.retry
        );

        return {
          deletedCount: result.deletedCount,
          success: true,
          message: `Delete operation completed. Deleted: ${result.deletedCount} document(s)`,
        };
      } catch (error) {
        return {
          deletedCount: 0,
          success: false,
          message: `Failed to delete document: ${error instanceof Error ? error.message : 'Unknown error'}`,
        };
      }
    }
  );
}

/**
 * Defines all CRUD tools for MongoDB operations.
 *
 * This function configures four tools: create, read, update, and delete
 * operations for MongoDB documents.
 *
 * @param ai - Genkit AI instance
 * @param client - MongoDB client
 * @param definition - Optional tool definition configuration
 */
export function defineCRUDTools(
  ai: Genkit,
  client: MongoClient,
  definition?: BaseDefinition
) {
  if (!definition?.id) {
    return;
  }
  configureInsertTool(ai, client, definition);
  configureFindByIdTool(ai, client, definition);
  configureUpdateTool(ai, client, definition);
  configureDeleteTool(ai, client, definition);
}

/**
 * Creates an array of CRUD tool references for MongoDB operations.
 *
 * @param id - The tool instance identifier
 * @returns Array of tool references for create, read, update, and delete operations
 */
export const mongoCrudToolsRefArray = (id: string) =>
  Object.values(CRUD_TOOL_ID).map((toolId) => toolRef(id, toolId));
