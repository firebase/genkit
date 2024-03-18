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

import { Command } from 'commander';
import { startRunner } from '../utils/runner-utils';
import { logger } from '../utils/logger';
import { readFile, writeFile } from 'fs/promises';

interface EvalRunOptions {
  output?: string;
}
/** Command to run evaluation on a dataset. */
export const evalRun = new Command('eval:run')
  .argument(
    '<dataset>',
    'Dataset to evaluate on (currently only supports JSON)'
  )
  .option(
    '--output <filename>',
    'name of the output file to write evaluation results'
  )
  .action(async (dataset: string, options: EvalRunOptions) => {
    const runner = await startRunner();

    logger.debug(`Loading data from '${dataset}'...`);
    const loadedData = JSON.parse((await readFile(dataset)).toString('utf-8'));

    const evaluatorActions = Object.keys(await runner.listActions()).filter(
      (name) => name.startsWith('/evaluator')
    );
    if (!evaluatorActions) {
      logger.error('No evaluators installed');
      return undefined;
    }
    const results: Record<string, any> = {};
    await Promise.all(
      evaluatorActions.map(async (e) => {
        logger.info(`Running evaluator '${e}'...`);
        const response = await runner.runAction({
          key: e,
          input: {
            dataset: loadedData,
          },
        });
        results[e] = response.result;
      })
    );

    if (options.output) {
      logger.info(`Writing results to '${options.output}'...`);
      await writeFile(options.output, JSON.stringify(results, undefined, '  '));
    } else {
      console.log(JSON.stringify(results, undefined, '  '));
    }

    await runner.stop();
  });
