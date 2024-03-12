import { __hardResetConfigForTesting } from '@genkit-ai/common/config';
import { __hardResetRegistryForTesting } from '@genkit-ai/common/registry';
import assert from 'node:assert';
import { beforeEach, describe, it } from 'node:test';
import { z } from 'zod';
import {
  getFlowState,
  interrupt,
  resumeFlow,
  scheduleFlow,
} from '../src/experimental';
import { flow, runFlow } from '../src/flow';

import { asyncTurn, configureInMemoryStateStore } from './testUtil';

function createSimpleTestDurableFlow() {
  return flow(
    {
      name: 'testFlow',
      input: z.string(),
      output: z.string(),
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
      const testFlow = flow(
        {
          name: 'testFlow',
          input: z.string(),
          output: z.string(),
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
