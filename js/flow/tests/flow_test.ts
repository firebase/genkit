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

import { FlowState, __hardResetConfigForTesting } from '@genkit-ai/core';
import { __hardResetRegistryForTesting } from '@genkit-ai/core/registry';
import assert from 'node:assert';
import { beforeEach, describe, it } from 'node:test';
import { z } from 'zod';
import { defineFlow, runFlow, streamFlow } from '../src/flow.js';
import { getFlowAuth } from '../src/utils.js';
import { configureInMemoryStateStore } from './testUtil.js';

function createTestFlow() {
  return defineFlow(
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

function createTestFlowWithAuth() {
  return defineFlow(
    {
      name: 'testFlowWithAuth',
      inputSchema: z.string(),
      outputSchema: z.string(),
      authPolicy: async (auth) => {
        if (auth != 'open sesame') {
          throw new Error('forty thieves!');
        }
      },
    },
    async (input) => {
      return `foo ${input}, auth ${JSON.stringify(getFlowAuth())}`;
    }
  );
}

function createTestStreamingFlow() {
  return defineFlow(
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
  beforeEach(__hardResetRegistryForTesting);
  beforeEach(() => {
    __hardResetConfigForTesting();
    delete process.env.GENKIT_ENV;
  });

  describe('runFlow', () => {
    it('should run the flow', async () => {
      configureInMemoryStateStore('prod');
      const testFlow = createTestFlow();

      const result = await runFlow(testFlow, 'foo');

      assert.equal(result, 'bar foo');
    });

    it('should rethrow the error', async () => {
      configureInMemoryStateStore('prod');
      const testFlow = defineFlow(
        {
          name: 'throwing',
          inputSchema: z.string(),
          outputSchema: z.string(),
        },
        async (input) => {
          throw new Error(`bad happened: ${input}`);
        }
      );

      await assert.rejects(async () => await runFlow(testFlow, 'foo'), {
        name: 'Error',
        message: 'bad happened: foo',
      });
    });

    it('should validate input', async () => {
      configureInMemoryStateStore('prod');
      const testFlow = defineFlow(
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
        async () => await runFlow(testFlow, { foo: 'foo', bar: 'bar' } as any),
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

    it('should pass auth context all the way', async () => {
      configureInMemoryStateStore('prod');
      const testFlow = createTestFlowWithAuth();

      const result = await runFlow(testFlow, 'bar', {
        withLocalAuthContext: 'open sesame',
      });

      assert.equal(result, 'foo bar, auth "open sesame"');
    });

    it('should fail auth', async () => {
      configureInMemoryStateStore('prod');
      const testFlow = createTestFlowWithAuth();

      await assert.rejects(
        () =>
          runFlow(testFlow, 'bar', {
            withLocalAuthContext: 'yolo',
          }),
        /forty thieves/
      );
    });
  });

  describe('streamFlow', () => {
    it('should run the flow', async () => {
      configureInMemoryStateStore('prod');
      const testFlow = createTestStreamingFlow();

      const response = streamFlow(testFlow, 3);

      const gotChunks: any[] = [];
      for await (const chunk of response.stream()) {
        gotChunks.push(chunk);
      }

      assert.equal(await response.output(), 'bar 3 true');
      assert.deepEqual(gotChunks, [{ count: 0 }, { count: 1 }, { count: 2 }]);
    });

    it('should rethrow the error', async () => {
      configureInMemoryStateStore('prod');
      const testFlow = defineFlow(
        {
          name: 'throwing',
          inputSchema: z.string(),
        },
        async (input) => {
          throw new Error(`bad happened: ${input}`);
        }
      );

      const response = streamFlow(testFlow, 'foo');
      await assert.rejects(async () => await response.output(), {
        name: 'Error',
        message: 'bad happened: foo',
      });
    });

    it('should pass auth context all the way', async () => {
      configureInMemoryStateStore('prod');
      const testFlow = createTestFlowWithAuth();

      const result = await streamFlow(testFlow, 'bar', {
        withLocalAuthContext: 'open sesame',
      });

      assert.equal(await result.output(), 'foo bar, auth "open sesame"');
    });

    it('should fail auth', async () => {
      configureInMemoryStateStore('prod');
      const testFlow = createTestFlowWithAuth();
      const response = streamFlow(testFlow, 'bar', {
        withLocalAuthContext: 'yolo',
      });

      await assert.rejects(() => response.output(), /forty thieves/);
    });
  });

  describe('stateStore', () => {
    describe('dev', () => {
      beforeEach(() => {
        process.env.GENKIT_ENV = 'dev';
      });

      it('should persist state in dev', async () => {
        const stateStore = configureInMemoryStateStore('dev');
        const testFlow = createTestFlow();

        const result = await runFlow(testFlow, 'foo');

        assert.equal(result, 'bar foo');
        assert.equal(Object.keys(stateStore.state).length, 1);

        // do some asserting on the state... TODO: make this better.
        const state = JSON.parse(
          Object.values(stateStore.state)[0]
        ) as FlowState;
        assert.equal(state.executions.length, 1);
        assert.equal(state.operation.done, true);
        assert.deepEqual(state.operation.result, {
          response: 'bar foo',
        });
        assert.equal(state.blockedOnStep, null);
        assert.deepEqual(state.eventsTriggered, {});
        assert.deepEqual(state.cache, {});
        assert.equal(state.input, 'foo');
        assert.equal(state.name, 'testFlow');
      });
    });

    describe('prod', () => {
      it('should not persist the state for non-durable flow', async () => {
        const stateStore = configureInMemoryStateStore('prod');
        const testFlow = createTestFlow();

        const result = await runFlow(testFlow, 'foo');

        assert.equal(result, 'bar foo');
        assert.equal(Object.keys(stateStore.state).length, 0);
      });
    });
  });
});
