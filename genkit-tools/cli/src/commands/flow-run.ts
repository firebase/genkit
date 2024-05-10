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
import {
  logger,
  runInRunnerThenStop,
  waitForFlowToComplete,
} from '@genkit-ai/tools-common/utils';
import { Command } from 'commander';
import { writeFile } from 'fs/promises';

interface FlowRunOptions {
  wait?: boolean;
  output?: string;
  stream?: boolean;
  auth?: string;
}

/** Command to start GenKit server, optionally without static file serving */
export const flowRun = new Command('flow:run')
  .description('run a flow using provided data as input')
  .argument('<flowName>', 'name of the flow to run')
  .argument('[data]', 'JSON data to use to start the flow')
  .option('-w, --wait', 'Wait for the flow to complete', false)
  .option('-s, --stream', 'Stream output', false)
  .option(
    '-a, --auth <JSON>',
    'JSON object passed to authPolicy and stored in local state as auth',
    ''
  )
  .option(
    '--output <filename>',
    'name of the output file to store the extracted data'
  )
  .action(async (flowName: string, data: string, options: FlowRunOptions) => {
    await runInRunnerThenStop(async (runner) => {
      logger.info(`Running '/flow/${flowName}' (stream=${options.stream})...`);
      let state = (
        await runner.runAction(
          {
            key: `/flow/${flowName}`,
            input: {
              start: {
                input: data ? JSON.parse(data) : undefined,
              },
              auth: options.auth ? JSON.parse(options.auth) : undefined,
            } as FlowInvokeEnvelopeMessage,
          },
          options.stream
            ? (chunk) => console.log(JSON.stringify(chunk, undefined, '  '))
            : undefined
        )
      ).result as FlowState;

      if (!state.operation.done && options.wait) {
        logger.info('Started flow run, waiting for it to complete...');
        state = await waitForFlowToComplete(runner, flowName, state.flowId);
      }
      logger.info(
        'Flow operation:\n' + JSON.stringify(state.operation, undefined, '  ')
      );

      if (options.output && state.operation.result?.response) {
        await writeFile(
          options.output,
          JSON.stringify(state.operation.result?.response, undefined, ' ')
        );
      }
    });
  });
