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

import { SimpleSpanProcessor } from '@opentelemetry/sdk-trace-base';
import assert from 'node:assert';
import { beforeEach, describe, it } from 'node:test';
import { defineFlow, defineStreamingFlow, run } from '../src/flow.js';
import { defineAction, getFlowAuth, z } from '../src/index.js';
import { Registry } from '../src/registry.js';
import { enableTelemetry } from '../src/tracing.js';
import { TestSpanExporter } from './utils.js';

const spanExporter = new TestSpanExporter();
enableTelemetry({
  spanProcessors: [new SimpleSpanProcessor(spanExporter)],
});

function createTestFlow(registry: Registry) {
  return defineFlow(
    registry,
    {
      name: 'testFlow',
      inputSchema: z.string(),
      outputSchema: z.string(),
    },
    async (input) => {
      return `bar ${input}`;
    }
  );
}

function createTestAuthFlow(registry: Registry) {
  return defineFlow(
    registry,
    {
      name: 'testFlow',
      inputSchema: z.string(),
      outputSchema: z.string(),
    },
    async (input) => {
      return `bar ${input} ${JSON.stringify(getFlowAuth())}`;
    }
  );
}

function createTestAuthStreamingFlow(registry: Registry) {
  return defineStreamingFlow(
    registry,
    {
      name: 'testFlow',
      inputSchema: z.number(),
      outputSchema: z.string(),
      streamSchema: z.object({ count: z.number() }),
    },
    async (input, streamingCallback) => {
      if (streamingCallback) {
        for (let i = 0; i < input; i++) {
          streamingCallback({ count: i });
        }
      }
      return `bar ${input} ${!!streamingCallback} ${JSON.stringify(getFlowAuth())}`;
    }
  );
}

function createTestStreamingFlow(registry: Registry) {
  return defineStreamingFlow(
    registry,
    {
      name: 'testFlow',
      inputSchema: z.number(),
      outputSchema: z.string(),
      streamSchema: z.object({ count: z.number() }),
    },
    async (input, streamingCallback) => {
      if (streamingCallback) {
        for (let i = 0; i < input; i++) {
          streamingCallback({ count: i });
        }
      }
      return `bar ${input} ${!!streamingCallback}`;
    }
  );
}

describe('flow', () => {
  let registry: Registry;

  beforeEach(() => {
    // Skips starting reflection server.
    delete process.env.GENKIT_ENV;
    registry = new Registry();
  });

  describe('runFlow', () => {
    it('should run the flow', async () => {
      const testFlow = createTestFlow(registry);

      const result = await testFlow('foo');

      assert.equal(result, 'bar foo');
    });

    it('should run simple sync flow', async () => {
      const testFlow = defineFlow(registry, 'testFlow', (input) => {
        return `bar ${input}`;
      });

      const result = await testFlow('foo');

      assert.equal(result, 'bar foo');
    });

    it('should rethrow the error', async () => {
      const testFlow = defineFlow(
        registry,
        {
          name: 'throwing',
          inputSchema: z.string(),
          outputSchema: z.string(),
        },
        async (input) => {
          throw new Error(`bad happened: ${input}`);
        }
      );

      await assert.rejects(() => testFlow('foo'), {
        name: 'Error',
        message: 'bad happened: foo',
      });
    });

    it('should validate input', async () => {
      const testFlow = defineFlow(
        registry,
        {
          name: 'validating',
          inputSchema: z.object({ foo: z.string(), bar: z.number() }),
          outputSchema: z.string(),
        },
        async (input) => {
          return `ok ${input}`;
        }
      );

      await assert.rejects(
        async () => await testFlow({ foo: 'foo', bar: 'bar' } as any),
        (err: Error) => {
          assert.strictEqual(err.name, 'ZodError');
          assert.equal(
            err.message.includes('Expected number, received string'),
            true
          );
          return true;
        }
      );
    });
  });

  describe('streamFlow', () => {
    it('should run the flow', async () => {
      const testFlow = createTestStreamingFlow(registry);

      const response = testFlow(3);

      const gotChunks: any[] = [];
      for await (const chunk of response.stream) {
        gotChunks.push(chunk);
      }

      assert.equal(await response.output, 'bar 3 true');
      assert.deepEqual(gotChunks, [{ count: 0 }, { count: 1 }, { count: 2 }]);
    });

    it('should rethrow the error', async () => {
      const testFlow = defineStreamingFlow(
        registry,
        {
          name: 'throwing',
          inputSchema: z.string(),
        },
        async (input) => {
          throw new Error(`stream bad happened: ${input}`);
        }
      );

      const response = testFlow('foo');
      await assert.rejects(() => response.output, {
        name: 'Error',
        message: 'stream bad happened: foo',
      });
    });
  });

  describe('getFlowAuth', () => {
    it('should run the flow', async () => {
      const testFlow = createTestAuthFlow(registry);

      const response = await testFlow('foo', {
        withLocalAuthContext: { user: 'test-user' },
      });

      assert.equal(response, 'bar foo {"user":"test-user"}');
    });

    it('should streams the flow', async () => {
      const testFlow = createTestAuthStreamingFlow(registry);

      const response = testFlow(3, {
        withLocalAuthContext: { user: 'test-user' },
      });

      const gotChunks: any[] = [];
      for await (const chunk of response.stream) {
        gotChunks.push(chunk);
      }

      assert.equal(await response.output, 'bar 3 true {"user":"test-user"}');
      assert.deepEqual(gotChunks, [{ count: 0 }, { count: 1 }, { count: 2 }]);
    });
  });

  describe('telemetry', async () => {
    beforeEach(() => {
      spanExporter.exportedSpans = [];
    });

    it('should create a trace', async () => {
      const testFlow = createTestFlow(registry);

      const result = await testFlow('foo');

      assert.equal(result, 'bar foo');
      assert.strictEqual(spanExporter.exportedSpans.length, 1);
      assert.strictEqual(spanExporter.exportedSpans[0].displayName, 'testFlow');
      assert.deepStrictEqual(spanExporter.exportedSpans[0].attributes, {
        'genkit:input': '"foo"',
        'genkit:isRoot': true,
        'genkit:metadata:flow:name': 'testFlow',
        'genkit:metadata:flow:state': 'done',
        'genkit:name': 'testFlow',
        'genkit:output': '"bar foo"',
        'genkit:path': '/{testFlow,t:flow}',
        'genkit:state': 'success',
        'genkit:type': 'flow',
      });
    });

    it('records traces of nested actions', async () => {
      const testAction = defineAction(
        registry,
        {
          name: 'testAction',
          actionType: 'tool',
          metadata: { type: 'tool' },
        },
        async (i) => {
          return 'bar';
        }
      );

      const testFlow = defineFlow(
        registry,
        {
          name: 'testFlow',
          inputSchema: z.string(),
          outputSchema: z.string(),
        },
        async (input) => {
          return run('custom', async () => {
            return 'foo ' + (await testAction(undefined));
          });
        }
      );
      const result = await testFlow('foo');

      assert.equal(result, 'foo bar');
      assert.strictEqual(spanExporter.exportedSpans.length, 3);

      assert.strictEqual(
        spanExporter.exportedSpans[0].displayName,
        'testAction'
      );
      assert.deepStrictEqual(spanExporter.exportedSpans[0].attributes, {
        'genkit:metadata:subtype': 'tool',
        'genkit:name': 'testAction',
        'genkit:output': '"bar"',
        'genkit:path':
          '/{testFlow,t:flow}/{custom,t:flowStep}/{testAction,t:action,s:tool}',
        'genkit:state': 'success',
        'genkit:type': 'action',
      });

      assert.strictEqual(spanExporter.exportedSpans[1].displayName, 'custom');
      assert.deepStrictEqual(spanExporter.exportedSpans[1].attributes, {
        'genkit:name': 'custom',
        'genkit:output': '"foo bar"',
        'genkit:path': '/{testFlow,t:flow}/{custom,t:flowStep}',
        'genkit:state': 'success',
        'genkit:type': 'flowStep',
      });

      assert.strictEqual(spanExporter.exportedSpans[2].displayName, 'testFlow');
      assert.deepStrictEqual(spanExporter.exportedSpans[2].attributes, {
        'genkit:input': '"foo"',
        'genkit:isRoot': true,
        'genkit:metadata:flow:name': 'testFlow',
        'genkit:metadata:flow:state': 'done',
        'genkit:name': 'testFlow',
        'genkit:output': '"foo bar"',
        'genkit:path': '/{testFlow,t:flow}',
        'genkit:state': 'success',
        'genkit:type': 'flow',
      });
    });
  });
});
