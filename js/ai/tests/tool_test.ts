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

import { z } from '@genkit-ai/core';
import { Registry } from '@genkit-ai/core/registry';
import * as assert from 'assert';
import { afterEach, describe, it } from 'node:test';
import { defineInterrupt } from '../src/tool.js';

describe('defineInterrupt', () => {
  let registry = new Registry();

  afterEach(() => {
    registry = new Registry();
  });

  function expectInterrupt(fn: () => any, metadata?: Record<string, any>) {
    assert.rejects(fn, { name: 'ToolInterruptError', metadata });
  }

  it('should throw a simple interrupt with no metadata', () => {
    const simple = defineInterrupt(registry, {
      name: 'simple',
      description: 'simple interrupt',
    });
    expectInterrupt(async () => {
      await simple({});
    });
  });

  it('should throw a simple interrupt with fixed metadata', () => {
    const simple = defineInterrupt(registry, {
      name: 'simple',
      description: 'simple interrupt',
      requestMetadata: { foo: 'bar' },
    });
    expectInterrupt(
      async () => {
        await simple({});
      },
      { foo: 'bar' }
    );
  });

  it('should throw a simple interrupt with function-returned metadata', () => {
    const simple = defineInterrupt(registry, {
      name: 'simple',
      description: 'simple interrupt',
      inputSchema: z.string(),
      requestMetadata: (foo) => ({ foo }),
    });
    expectInterrupt(
      async () => {
        await simple('bar');
      },
      { foo: 'bar' }
    );
  });

  it('should throw a simple interrupt with async function-returned metadata', () => {
    const simple = defineInterrupt(registry, {
      name: 'simple',
      description: 'simple interrupt',
      inputSchema: z.string(),
      requestMetadata: async (foo) => ({ foo }),
    });
    expectInterrupt(
      async () => {
        await simple('bar');
      },
      { foo: 'bar' }
    );
  });

  it('should register the reply schema / json schema as the output schema of the tool', () => {
    const ReplySchema = z.object({ foo: z.string() });
    const simple = defineInterrupt(registry, {
      name: 'simple',
      description: 'simple',
      replySchema: ReplySchema,
    });
    assert.equal(simple.__action.outputSchema, ReplySchema);
    const simple2 = defineInterrupt(registry, {
      name: 'simple2',
      description: 'simple2',
      replyJsonSchema: { type: 'string' },
    });
    assert.deepStrictEqual(simple2.__action.outputJsonSchema, {
      type: 'string',
    });
  });
});
