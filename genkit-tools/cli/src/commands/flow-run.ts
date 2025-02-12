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

import { logger } from '@genkit-ai/tools-common/utils';
import { Command } from 'commander';
import { writeFile } from 'fs/promises';
import { runWithManager } from '../utils/manager-utils';

interface FlowRunOptions {
  wait?: boolean;
  output?: string;
  stream?: boolean;
  context?: string;
}

/** Command to run a flow. */
export const flowRun = new Command('flow:run')
  .description('run a flow using provided data as input')
  .argument('<flowName>', 'name of the flow to run')
  .argument('[data]', 'JSON data to use to start the flow')
  .option('-w, --wait', 'Wait for the flow to complete', false)
  .option('-s, --stream', 'Stream output', false)
  .option('-c, --context <JSON>', 'JSON object passed to context', '')
  .option(
    '--output <filename>',
    'name of the output file to store the extracted data'
  )
  .action(async (flowName: string, data: string, options: FlowRunOptions) => {
    await runWithManager(async (manager) => {
      logger.info(`Running '/flow/${flowName}' (stream=${options.stream})...`);
      let result = (
        await manager.runAction(
          {
            key: `/flow/${flowName}`,
            input: data ? JSON.parse(data) : undefined,
            context: options.context ? JSON.parse(options.context) : undefined,
          },
          options.stream
            ? (chunk) => console.log(JSON.stringify(chunk, undefined, '  '))
            : undefined
        )
      ).result;

      logger.info('Result:\n' + JSON.stringify(result, undefined, '  '));

      if (options.output && result) {
        await writeFile(options.output, JSON.stringify(result, undefined, ' '));
      }
    });
  });
