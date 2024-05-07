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
import { beforeEach, describe, it } from 'node:test';
import { z } from 'zod';
import { action } from '../src/action.js';
import { __hardResetRegistryForTesting } from '../src/registry.js';

describe('action', () => {
  beforeEach(__hardResetRegistryForTesting);

  it('applies middleware', async () => {
    const act = action(
      {
        name: 'foo',
        inputSchema: z.string(),
        outputSchema: z.number(),
        use: [
          async (input, next) => (await next(input + 'middle1')) + 1,
          async (input, next) => (await next(input + 'middle2')) + 2,
        ],
      },
      async (input) => {
        return input.length;
      }
    );

    assert.strictEqual(
      await act('foo'),
      20 // "foomiddle1middle2".length + 1 + 2
    );
  });
});
