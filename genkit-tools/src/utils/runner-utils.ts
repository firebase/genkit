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
import { FlowInvokeEnvelopeMessage, FlowState } from '../types/flow';

/**
 * Start the runner and waits for it to fully load -- reflection API to become avaialble.
 */
export async function startRunner(): Promise<Runner> {
  const runner = new Runner({ autoReload: false });
  runner.start();
  await runner.waitUntilHealthy();
  return runner;
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
  return (await runner.runAction({
    key: `/flow/${flowName}`,
    input: {
      state: {
        flowId,
      },
    } as FlowInvokeEnvelopeMessage,
  })) as FlowState;
}
