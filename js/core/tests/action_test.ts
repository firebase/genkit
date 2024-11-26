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
import { z } from 'zod';
import { action } from '../src/action.js';

describe('action', () => {
  it('applies middleware', async () => {
    const act = action(
      {
        name: 'foo',
        inputSchema: z.string(),
        outputSchema: z.number(),
        use: [
          async (input, next) => (await next(input + 'middle1')) + 1,
          async (input, opts, next) =>
            (await next(input + 'middle2', opts)) + 2,
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

  it('returns telemetry info', async () => {
    const act = action(
      {
        name: 'foo',
        inputSchema: z.string(),
        outputSchema: z.number(),
        use: [
          async (input, next) => (await next(input + 'middle1')) + 1,
          async (input, opts, next) =>
            (await next(input + 'middle2', opts)) + 2,
        ],
      },
      async (input) => {
        return input.length;
      }
    );

    const result = await act.run('foo');
    assert.strictEqual(
      result.result,
      20 // "foomiddle1middle2".length + 1 + 2
    );
    assert.strictEqual(result.telemetry !== null, true);
    assert.strictEqual(
      result.telemetry.traceId !== null && result.telemetry.traceId.length > 0,
      true
    );
    assert.strictEqual(
      result.telemetry.spanId !== null && result.telemetry.spanId.length > 0,
      true
    );
  });

  it('run the action with options', async () => {
    let passedContext;
    const act = action(
      {
        name: 'foo',
        inputSchema: z.string(),
        outputSchema: z.number(),
      },
      async (input, { sendChunk, context }) => {
        passedContext = context;
        sendChunk(1);
        sendChunk(2);
        sendChunk(3);
        return input.length;
      }
    );

    const chunks: any[] = [];
    await act.run('1234', {
      context: { foo: 'bar' },
      onChunk: (c) => chunks.push(c),
    });

    assert.deepStrictEqual(passedContext, {
      foo: 'bar',
    });

    assert.deepStrictEqual(chunks, [1, 2, 3]);
  });
});
