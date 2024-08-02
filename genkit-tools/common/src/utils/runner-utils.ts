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

import { Runner } from '../runner/runner';
import { GenkitToolsError } from '../runner/types';
import { FlowInvokeEnvelopeMessage, FlowState } from '../types/flow';
import { Status } from '../types/status';
import { logger } from './logger';

/**
 * Start the runner and waits for it to fully load -- reflection API to become avaialble.
 */
export async function startRunner(): Promise<Runner> {
  const runner = new Runner({ autoReload: false, buildOnStart: true });
  if (!(await runner.start())) {
    throw new Error('Failed to load app code.');
  }
  await runner.waitUntilHealthy();
  return runner;
}

export async function runInRunnerThenStop(
  fn: (runner: Runner) => Promise<void>
) {
  let runner: Runner;
  try {
    runner = await startRunner();
  } catch (e) {
    process.exit(1);
  }
  try {
    await fn(runner);
  } catch (err) {
    logger.info('Command exited with an Error:');
    const error = err as GenkitToolsError;
    if (typeof error.data === 'object') {
      const errorStatus = error.data as Status;
      const { code, details, message } = errorStatus;
      logger.info(`\tCode: ${code}`);
      logger.info(`\tMessage: ${message}`);
      logger.info(`\tTrace: http://localhost:4200/traces/${details.traceId}\n`);
    } else {
      logger.info(`\tMessage: ${error.data}\n`);
    }
    logger.error('Stacktrace:');
    logger.error(`${error.stack}`);
  } finally {
    await runner.sendQuit();
    await runner.stop();
  }
}

/**
 * Poll and wait for the flow to fully complete.
 */
export async function waitForFlowToComplete(
  runner: Runner,
  flowName: string,
  flowId: string
): Promise<FlowState> {
  let state;
  // eslint-disable-next-line no-constant-condition
  while (true) {
    state = await getFlowState(runner, flowName, flowId);
    if (state.operation.done) {
      break;
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  return state;
}

/**
 * Retrieve the flow state.
 */
export async function getFlowState(
  runner: Runner,
  flowName: string,
  flowId: string
): Promise<FlowState> {
  return (
    await runner.runAction({
      key: `/flow/${flowName}`,
      input: {
        state: {
          flowId,
        },
      } as FlowInvokeEnvelopeMessage,
    })
  ).result as FlowState;
}
