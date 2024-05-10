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

import {
  FlowInvokeEnvelopeMessage,
  FlowState,
  Operation,
} from '@genkit-ai/tools-common';
import {
  logger,
  runInRunnerThenStop,
  waitForFlowToComplete,
} from '@genkit-ai/tools-common/utils';
import { Command } from 'commander';
import { readFile, writeFile } from 'fs/promises';

interface FlowBatchRunOptions {
  wait?: boolean;
  output?: string;
  label?: string;
  auth?: string;
}

/** Command to run flows with batch input. */
export const flowBatchRun = new Command('flow:batchRun')
  .description(
    'batch run a flow using provided set of data from a file as input'
  )
  .argument('<flowName>', 'name of the flow to run')
  .argument('<inputFileName>', 'JSON batch data to use to run the flow')
  .option('-w, --wait', 'Wait for the flow to complete', false)
  .option(
    '-a, --auth <JSON>',
    'JSON object passed to authPolicy and stored in local state as auth',
    ''
  )
  .option('--output <filename>', 'name of the output file to store the output')
  .option('--label [label]', 'label flow run in this batch')
  .action(
    async (
      flowName: string,
      fileName: string,
      options: FlowBatchRunOptions
    ) => {
      await runInRunnerThenStop(async (runner) => {
        const inputData = JSON.parse(await readFile(fileName, 'utf8')) as any[];
        if (!Array.isArray(inputData)) {
          throw new Error('batch input data must be an array');
        }

        const outputValues = [] as { input: any; output: Operation }[];
        for (const data of inputData) {
          logger.info(`Running '/flow/${flowName}'...`);
          let state = (
            await runner.runAction({
              key: `/flow/${flowName}`,
              input: {
                start: {
                  input: data,
                  labels: options.label
                    ? { batchRun: options.label }
                    : undefined,
                  auth: options.auth ? JSON.parse(options.auth) : undefined,
                },
              } as FlowInvokeEnvelopeMessage,
            })
          ).result as FlowState;

          if (!state.operation.done && options.wait) {
            logger.info('Started flow run, waiting for it to complete...');
            state = await waitForFlowToComplete(runner, flowName, state.flowId);
          }
          logger.info(
            'Flow operation:\n' +
              JSON.stringify(state.operation, undefined, '  ')
          );
          outputValues.push({
            input: data,
            output: state.operation,
          });
        }

        if (options.output) {
          await writeFile(
            options.output,
            JSON.stringify(outputValues, undefined, ' ')
          );
        }
      });
    }
  );
