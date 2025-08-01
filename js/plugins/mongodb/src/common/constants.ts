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

/** Default field name for storing embeddings in MongoDB documents */
export const DEFAULT_EMBEDDING_FIELD_NAME = 'embedding';
/** Default field name for storing document data in MongoDB documents */
export const DEFAULT_DATA_FIELD_NAME = 'data';
/** Default field name for storing metadata in MongoDB documents */
export const DEFAULT_METADATA_FIELD_NAME = 'metadata';
/** Default field name for storing data type in MongoDB documents */
export const DEFAULT_DATA_TYPE_FIELD_NAME = 'dataType';

/** Default batch size for processing documents in bulk operations */
export const DEFAULT_BATCH_SIZE = 100;

/** Default number of retry attempts for failed operations */
export const RETRY_ATTEMPTS = 0;
/** Default base delay in milliseconds for retry operations */
export const BASE_RETRY_DELAY_MS = 200;
/** Default jitter factor for adding randomness to retry delays */
export const JITTER_FACTOR = 0.1;

/** Maximum number of candidates to return in search operations */
export const MAX_NUM_CANDIDATES = 10000;

/** CRUD tool identifiers for MongoDB operations */
export const CRUD_TOOL_ID = {
  /** Create document operation */
  create: 'create',
  /** Read document operation */
  read: 'read',
  /** Update document operation */
  update: 'update',
  /** Delete document operation */
  delete: 'delete',
};

/** Search index tool identifiers for MongoDB operations */
export const SEARCH_INDEX_TOOL_ID = {
  /** Create search index operation */
  create: 'create',
  /** List search indexes operation */
  list: 'list',
  /** Drop search index operation */
  drop: 'drop',
};

/**
 * Creates a tool reference identifier for MongoDB tools.
 *
 * @param id - The plugin instance identifier
 * @param toolId - The specific tool identifier
 * @returns A formatted tool reference string
 */
export const toolRef = (id: string, toolId: string) =>
  `mongodb/${id}/${toolId}`;
