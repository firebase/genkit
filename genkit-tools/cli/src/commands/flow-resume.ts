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

import { FlowInvokeEnvelopeMessage, FlowState } from '@genkit-ai/tools-common';
import { logger, runInRunnerThenStop } from '@genkit-ai/tools-common/utils';
import { Command } from 'commander';

/** Command to start GenKit server, optionally without static file serving */
export const flowResume = new Command('flow:resume')
  .description('resume an interrupted flow (experimental)')
  .argument('<flowName>', 'name of the flow to resume')
  .argument('<flowId>', 'ID of the flow to resume')
  .argument('<data>', 'JSON data to use to resume the flow')
  .action(async (flowName: string, flowId: string, data: string) => {
    await runInRunnerThenStop(async (runner) => {
      logger.info(`Resuming '/flow/${flowName}'`);
      const state = (
        await runner.runAction({
          key: `/flow/${flowName}`,
          input: {
            resume: {
              flowId,
              // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
              payload: JSON.parse(data),
            },
          } as FlowInvokeEnvelopeMessage,
        })
      ).result as FlowState;

      logger.info(
        'Flow operation:\n' + JSON.stringify(state.operation, undefined, '  ')
      );
    });
  });
