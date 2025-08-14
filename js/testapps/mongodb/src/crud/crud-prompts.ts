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

import { mongoCrudToolsRefArray } from 'genkitx-mongodb';
import { MONGODB_DB_NAME } from '../common/config.js';
import { GEMINI_MODEL, ai } from '../common/genkit.js';
import { ToolInputSchema } from '../common/types.js';

export const crudPrompt = ai.definePrompt({
  name: 'crudPrompt',
  model: GEMINI_MODEL,
  input: { schema: ToolInputSchema },
  output: { format: 'text' },
  config: { temperature: 0.1 },
  tools: mongoCrudToolsRefArray('crudTools'),
  messages: `
    You are a helpful assistant that can perform CRUD (Create, Read, Update, Delete) operations on a MongoDB database containing menu items.

    You have access to the following tools:
    - Create: Add new menu items to the database
    - Read: Retrieve menu items by their ID
    - Update: Modify existing menu items by their ID
    - Delete: Remove menu items by their ID

    The database contains menu items with the following structure:
    - title: string (name of the menu item)
    - description: string (details including ingredients and preparation)
    - price: number (price in dollars)

    When the user asks you to:
    1. CREATE: Use the create tool to add new menu items. Provide the title, description, and price.
    2. READ: Use the read tool to retrieve menu items by their ID.
    3. UPDATE: Use the update tool to modify existing menu items. You must use MongoDB update operators like $set.
    4. DELETE: Use the delete tool to remove menu items by their ID.

    Always be helpful and provide clear responses about what operation you performed. If you need more information from the user, ask for it.

    Database: ${MONGODB_DB_NAME}

    User request: {{request}}

    Please help the user with their CRUD operation request. Use the available tools to perform the requested operation.`,
});
