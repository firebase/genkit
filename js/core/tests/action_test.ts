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

import * as assert from 'assert';
import { beforeEach, describe, it } from 'node:test';
import { z } from 'zod';
import { action, defineAction } from '../src/action.js';
import { Registry } from '../src/registry.js';

describe('action', () => {
  var registry: Registry;
  beforeEach(() => {
    registry = new Registry();
  });

  it('applies middleware', async () => {
    const act = action(
      registry,
      {
        name: 'foo',
        inputSchema: z.string(),
        outputSchema: z.number(),
        use: [
          async (input, next) => (await next(input + 'middle1')) + 1,
          async (input, opts, next) =>
            (await next(input + 'middle2', opts)) + 2,
        ],
        actionType: 'util',
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
      registry,
      {
        name: 'foo',
        inputSchema: z.string(),
        outputSchema: z.number(),
        use: [
          async (input, next) => (await next(input + 'middle1')) + 1,
          async (input, opts, next) =>
            (await next(input + 'middle2', opts)) + 2,
        ],
        actionType: 'util',
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
      registry,
      {
        name: 'foo',
        inputSchema: z.string(),
        outputSchema: z.number(),
        actionType: 'util',
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

  it('should stream the response', async () => {
    const action = defineAction(
      registry,
      { name: 'hello', actionType: 'custom' },
      async (input, { sendChunk }) => {
        sendChunk({ count: 1 });
        sendChunk({ count: 2 });
        sendChunk({ count: 3 });
        return `hi ${input}`;
      }
    );

    const response = action.stream('Pavel');

    const gotChunks: any[] = [];
    for await (const chunk of response.stream) {
      gotChunks.push(chunk);
    }

    assert.equal(await response.output, 'hi Pavel');
    assert.deepStrictEqual(gotChunks, [
      { count: 1 },
      { count: 2 },
      { count: 3 },
    ]);
  });

  it('should inherit context from parent action invocation', async () => {
    const child = defineAction(
      registry,
      { name: 'child', actionType: 'custom' },
      async (_, { context }) => {
        return `hi ${context?.auth?.email}`;
      }
    );
    const parent = defineAction(
      registry,
      { name: 'parent', actionType: 'custom' },
      async () => {
        return child();
      }
    );

    const response = await parent(undefined, {
      context: { auth: { email: 'a@b.c' } },
    });

    assert.strictEqual(response, 'hi a@b.c');
  });

  it('should include trace info in the context', async () => {
    const act = defineAction(
      registry,
      { name: 'child', actionType: 'custom' },
      async (_, ctx) => {
        return `traceId=${!!ctx.trace.traceId} spanId=${!!ctx.trace.spanId}`;
      }
    );

    const response = await act(undefined);

    assert.strictEqual(response, 'traceId=true spanId=true');
  });
});
