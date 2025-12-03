/**
 * Copyright 2025 Google LLC
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

import * as assert from 'assert';
import { genkit, z } from 'genkit';
import { describe, it } from 'node:test';
import { anthropic } from '../src/index.js';

const SKIP_LIVE_TESTS = !process.env.ANTHROPIC_API_KEY;

// TODO: clean this test up a little bit
describe('Anthropic Live Tests', { skip: SKIP_LIVE_TESTS }, () => {
  it('should return structured output matching the schema', async () => {
    const ai = genkit({
      plugins: [anthropic({ apiVersion: 'beta' })],
    });

    const schema = z.object({
      name: z.string(),
      age: z.number(),
      city: z.string(),
      isStudent: z.boolean(),
      isEmployee: z.boolean(),
      isRetired: z.boolean(),
      isUnemployed: z.boolean(),
      isDisabled: z.boolean(),
    });

    const result = await ai.generate({
      model: 'anthropic/claude-sonnet-4-5',
      prompt:
        'Generate a fictional person with name "Alice", age 30, and city "New York". Return only the JSON.',
      output: { schema, format: 'json', constrained: true },
    });

    const parsed = result.output;
    assert.ok(parsed, 'Should have parsed output');
    assert.strictEqual(parsed.name, 'Alice');
    assert.strictEqual(parsed.age, 30);
    assert.strictEqual(parsed.city, 'New York');
    // assert the others are NOT undefined
    assert.notStrictEqual(parsed.isStudent, undefined);
    assert.notStrictEqual(parsed.isEmployee, undefined);
    assert.notStrictEqual(parsed.isRetired, undefined);
    assert.notStrictEqual(parsed.isUnemployed, undefined);
    assert.notStrictEqual(parsed.isDisabled, undefined);
  });
});
