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

import { __hardResetConfigForTesting } from '@genkit-ai/core';
import { __hardResetRegistryForTesting } from '@genkit-ai/core/registry';
import assert from 'node:assert';
import { beforeEach, describe, it } from 'node:test';
import { z } from 'zod';
import {
  getFlowState,
  interrupt,
  resumeFlow,
  scheduleFlow,
} from '../src/experimental.js';
import { defineFlow, runFlow } from '../src/flow.js';

import { asyncTurn, configureInMemoryStateStore } from './testUtil.js';

function createSimpleTestDurableFlow() {
  return defineFlow(
    {
      name: 'testFlow',
      inputSchema: z.string(),
      outputSchema: z.string(),
      experimentalDurable: true,
    },
    async (input) => {
      return `bar ${input}`;
    }
  );
}

describe('durable', () => {
  beforeEach(__hardResetRegistryForTesting);
  beforeEach(() => {
    __hardResetConfigForTesting();
    delete process.env.GENKIT_ENV;
  });

  describe('runFlow', () => {
    it('should run the flow', async () => {
      configureInMemoryStateStore('prod');
      const testFlow = createSimpleTestDurableFlow();

      const result = await runFlow(testFlow, 'foo');

      assert.equal(result, 'bar foo');
    });
  });

  describe('resumeFlow', () => {
    it('should run the flow', async () => {
      configureInMemoryStateStore('prod');
      const testFlow = defineFlow(
        {
          name: 'testFlow',
          inputSchema: z.string(),
          outputSchema: z.string(),
          experimentalDurable: true,
        },
        async (input) => {
          const response = await interrupt(
            'take-a-break',
            z.object({ something: z.string() })
          );

          return `${input} ${response.something}`;
        }
      );

      const op = await scheduleFlow(testFlow, 'foo');
      assert.equal(op.done, false);
      assert.equal(op.blockedOnStep, undefined);

      await asyncTurn();

      const op2 = await getFlowState(testFlow, op.name);
      assert.equal(op2.name, op.name);
      assert.equal(op2.done, false);
      assert.equal(op2.blockedOnStep?.name, 'take-a-break');

      const op3 = await resumeFlow(testFlow, op2.name, { something: 'bar' });
      assert.equal(op3.blockedOnStep, undefined);
      assert.equal(op3.done, true);
      assert.equal(op3.result?.error, undefined);
      assert.equal(op3.result?.response, 'foo bar');

      // check persisted state
      const op4 = await getFlowState(testFlow, op.name);
      assert.deepEqual(op4, op3);
    });
  });

  describe('stateStore', () => {
    describe('dev', () => {
      beforeEach(() => {
        process.env.GENKIT_ENV = 'dev';
      });

      it('should persist state for durable flow in dev', async () => {
        const stateStore = configureInMemoryStateStore('dev');
        const testFlow = createSimpleTestDurableFlow();

        const result = await runFlow(testFlow, 'foo');

        assert.equal(result, 'bar foo');
        assert.equal(Object.keys(stateStore.state).length, 1);
      });
    });

    describe('prod', () => {
      it('should persist the state for durable flow', async () => {
        const stateStore = configureInMemoryStateStore('prod');
        const testFlow = createSimpleTestDurableFlow();

        const result = await runFlow(testFlow, 'foo');

        assert.equal(result, 'bar foo');
        assert.equal(Object.keys(stateStore.state).length, 1);
      });
    });
  });
});
