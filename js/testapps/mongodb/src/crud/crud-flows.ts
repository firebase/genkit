/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of this file except in compliance with the License.
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

import { ai } from '../common/genkit.js';
import { ToolInputSchema, ToolOutputSchema } from '../common/types.js';
import { crudPrompt } from './crud-prompts.js';

export const crudManagement = ai.defineFlow(
  {
    name: 'Tools - CRUD - Management Flow',
    inputSchema: ToolInputSchema,
    outputSchema: ToolOutputSchema,
  },
  async (input) => {
    const response = await crudPrompt(input);
    return {
      response: response.text,
    };
  }
);
