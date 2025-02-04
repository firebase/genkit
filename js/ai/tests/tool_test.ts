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
import { defineInterrupt, defineTool } from '../src/tool.js';

describe('defineInterrupt', () => {
  let registry = new Registry();
  registry.apiStability = 'beta';

  afterEach(() => {
    registry = new Registry();
    registry.apiStability = 'beta';
  });

  function expectInterrupt(fn: () => any, metadata?: Record<string, any>) {
    return assert.rejects(fn, { name: 'ToolInterruptError', metadata });
  }

  it('should throw a simple interrupt with no metadata', async () => {
    const simple = defineInterrupt(registry, {
      name: 'simple',
      description: 'simple interrupt',
    });
    await expectInterrupt(async () => {
      await simple({});
    });
  });

  it('should throw a simple interrupt with fixed metadata', async () => {
    const simple = defineInterrupt(registry, {
      name: 'simple',
      description: 'simple interrupt',
      requestMetadata: { foo: 'bar' },
    });
    await expectInterrupt(
      async () => {
        await simple({});
      },
      { foo: 'bar' }
    );
  });

  it('should throw a simple interrupt with function-returned metadata', async () => {
    const simple = defineInterrupt(registry, {
      name: 'simple',
      description: 'simple interrupt',
      inputSchema: z.string(),
      requestMetadata: (foo) => ({ foo }),
    });
    await expectInterrupt(
      async () => {
        await simple('bar');
      },
      { foo: 'bar' }
    );
  });

  it('should throw a simple interrupt with async function-returned metadata', async () => {
    const simple = defineInterrupt(registry, {
      name: 'simple',
      description: 'simple interrupt',
      inputSchema: z.string(),
      requestMetadata: async (foo) => ({ foo }),
    });
    await expectInterrupt(
      async () => {
        await simple('bar');
      },
      { foo: 'bar' }
    );
  });

  it('should register the reply schema / json schema as the output schema of the tool', () => {
    const ResponseSchema = z.object({ foo: z.string() });
    const simple = defineInterrupt(registry, {
      name: 'simple',
      description: 'simple',
      outputSchema: ResponseSchema,
    });
    assert.equal(simple.__action.outputSchema, ResponseSchema);
    const simple2 = defineInterrupt(registry, {
      name: 'simple2',
      description: 'simple2',
      outputJsonSchema: { type: 'string' },
    });
    assert.deepStrictEqual(simple2.__action.outputJsonSchema, {
      type: 'string',
    });
  });
});

describe('defineTool', () => {
  let registry = new Registry();
  registry.apiStability = 'beta';
  afterEach(() => {
    registry = new Registry();
    registry.apiStability = 'beta';
  });

  describe('.respond()', () => {
    it('constructs a ToolResponsePart', () => {
      const t = defineTool(
        registry,
        { name: 'test', description: 'test' },
        async () => {}
      );
      assert.deepStrictEqual(
        t.respond({ toolRequest: { name: 'test', input: {} } }, 'output'),
        {
          toolResponse: {
            name: 'test',
            output: 'output',
          },
          metadata: {
            interruptResponse: true,
          },
        }
      );
    });

    it('includes metadata', () => {
      const t = defineTool(
        registry,
        { name: 'test', description: 'test' },
        async () => {}
      );
      assert.deepStrictEqual(
        t.respond({ toolRequest: { name: 'test', input: {} } }, 'output', {
          metadata: { extra: 'data' },
        }),
        {
          toolResponse: {
            name: 'test',
            output: 'output',
          },
          metadata: {
            interruptResponse: { extra: 'data' },
          },
        }
      );
    });

    it('validates schema', () => {
      const t = defineTool(
        registry,
        { name: 'test', description: 'test', outputSchema: z.number() },
        async (input, { interrupt }) => interrupt()
      );
      assert.throws(
        () => {
          t.respond(
            { toolRequest: { name: 'test', input: {} } },
            'not_a_number' as any
          );
        },
        { name: 'GenkitError', status: 'INVALID_ARGUMENT' }
      );

      assert.deepStrictEqual(
        t.respond({ toolRequest: { name: 'test', input: {} } }, 55),
        {
          toolResponse: {
            name: 'test',
            output: 55,
          },
          metadata: {
            interruptResponse: true,
          },
        }
      );
    });
  });

  describe('.restart()', () => {
    it('constructs a ToolRequestPart', () => {
      const t = defineTool(
        registry,
        { name: 'test', description: 'test' },
        async () => {}
      );
      assert.deepStrictEqual(
        t.restart({ toolRequest: { name: 'test', input: {} } }),
        {
          toolRequest: {
            name: 'test',
            input: {},
          },
          metadata: {
            resumed: true,
          },
        }
      );
    });

    it('includes metadata', () => {
      const t = defineTool(
        registry,
        { name: 'test', description: 'test' },
        async () => {}
      );
      assert.deepStrictEqual(
        t.restart(
          { toolRequest: { name: 'test', input: {} } },
          { extra: 'data' }
        ),
        {
          toolRequest: {
            name: 'test',
            input: {},
          },
          metadata: {
            resumed: { extra: 'data' },
          },
        }
      );
    });

    it('validates schema', () => {
      const t = defineTool(
        registry,
        { name: 'test', description: 'test', inputSchema: z.number() },
        async (input, { interrupt }) => interrupt()
      );
      assert.throws(
        () => {
          t.restart({ toolRequest: { name: 'test', input: {} } }, undefined, {
            replaceInput: 'not_a_number' as any,
          });
        },
        { name: 'GenkitError', status: 'INVALID_ARGUMENT' }
      );

      assert.deepStrictEqual(
        t.restart({ toolRequest: { name: 'test', input: {} } }, undefined, {
          replaceInput: 55,
        }),
        {
          toolRequest: {
            name: 'test',
            input: 55,
          },
          metadata: {
            resumed: true,
            replacedInput: {},
          },
        }
      );
    });
  });
});
