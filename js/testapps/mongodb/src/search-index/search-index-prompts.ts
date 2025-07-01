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

import { mongoSearchIndexToolsRefArray } from 'genkitx-mongodb';
import { MONGODB_DB_NAME } from '../common/config.js';
import { GEMINI_MODEL, ai } from '../common/genkit.js';
import { ToolInputSchema } from '../common/types.js';

export const searchIndexPrompt = ai.definePrompt({
  name: 'searchIndexPrompt',
  model: GEMINI_MODEL,
  input: { schema: ToolInputSchema },
  output: { format: 'text' },
  config: { temperature: 0.1 },
  tools: mongoSearchIndexToolsRefArray('searchIndexTools'),
  messages: `
    You are a helpful assistant that can manage search indexes on a MongoDB database containing menu items.

    You have access to the following search index management tools:
    - Create: Create new search indexes for text search or vector search
    - List: List all existing search indexes on the collection
    - Drop: Remove search indexes by name

    The database contains menu items with the following structure:
    - title: string (name of the menu item)
    - description: string (details including ingredients and preparation)
    - price: number (price in dollars)

    When the user asks you to:
    1. CREATE INDEX: Use the create tool to add new search indexes. You can create:
       - Text search indexes for searching through text fields
       - Vector search indexes for semantic search using embeddings
       - Provide the index name, type (search or vectorSearch), and definition
    2. LIST INDEXES: Use the list tool to see all existing indexes on the collection
    3. DROP INDEX: Use the drop tool to remove indexes by their name

    Common index types and their purposes:
    - Text search indexes: For full-text search on string fields like title and description
    - Vector search indexes: For semantic search using embeddings (requires embedding field)

    Always be helpful and provide clear responses about what operation you performed. If you need more information from the user, ask for it.

    Database: ${MONGODB_DB_NAME}

    User request: {{request}}

    Please help the user with their search index management request. Use the available tools to perform the requested operation.`,
});
