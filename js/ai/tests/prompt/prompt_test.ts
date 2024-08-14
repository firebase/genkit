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

import assert from 'node:assert';
import { describe, it } from 'node:test';
import * as z from 'zod';
import { definePrompt, renderPrompt } from '../../src/prompt.ts';

describe('prompt', () => {
  describe('render()', () => {
    it('respects output schema in the definition', async () => {
      const schema1 = z.object({
        puppyName: z.string({ description: 'A cute name for a puppy' }),
      });
      const prompt1 = definePrompt(
        {
          name: 'prompt1',
          inputSchema: z.string({ description: 'Dog breed' }),
        },
        async (breed) => {
          return {
            messages: [
              {
                role: 'user',
                content: [{ text: `Pick a name for a ${breed} puppy` }],
              },
            ],
            output: {
              format: 'json',
              schema: schema1,
            },
          };
        }
      );
      const generateRequest = await renderPrompt({
        prompt: prompt1,
        input: 'poodle',
        model: 'geminiPro',
      });
      assert.equal(generateRequest.output?.schema, schema1);
    });
  });
});
