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

import { EvalInput, EvalResponse } from '@genkit-ai/tools-common';
import {
  EvalExporter,
  enrichResultsWithScoring,
  extractMetricsMetadata,
  getEvalStore,
  getExporterForString,
} from '@genkit-ai/tools-common/eval';
import {
  confirmLlmUse,
  evaluatorName,
  isEvaluator,
  logger,
  runInRunnerThenStop,
} from '@genkit-ai/tools-common/utils';
import { Command } from 'commander';
import { randomUUID } from 'crypto';
import { readFile } from 'fs/promises';

interface EvalRunOptions {
  output?: string;
  evaluators?: string;
  force?: boolean;
  outputFormat: string;
}
/** Command to run evaluation on a dataset. */
export const evalRun = new Command('eval:run')
  .description('evaluate provided dataset against configured evaluators')
  .argument(
    '<dataset>',
    'Dataset to evaluate on (currently only supports JSON)'
  )
  .option(
    '--output <filename>',
    'name of the output file to write evaluation results. Defaults to json output.'
  )
  // TODO: Figure out why passing a new Option with choices doesn't work
  .option(
    '--output-format <format>',
    'The output file format (csv, json)',
    'json'
  )
  .option(
    '--evaluators <evaluators>',
    'comma separated list of evaluators to use (by default uses all)'
  )
  .option('--force', 'Automatically accept all interactive prompts')
  .action(async (dataset: string, options: EvalRunOptions) => {
    await runInRunnerThenStop(async (runner) => {
      const evalStore = getEvalStore();
      const exportFn: EvalExporter = getExporterForString(options.outputFormat);

      logger.debug(`Loading data from '${dataset}'...`);
      const evalDataset: EvalInput[] = JSON.parse(
        (await readFile(dataset)).toString('utf-8')
      ).map((testCase: any) => ({
        ...testCase,
        testCaseId: testCase.testCaseId || randomUUID(),
        traceIds: testCase.traceIds || [],
      }));

      const allActions = await runner.listActions();
      const allEvaluatorActions = [];
      for (const key in allActions) {
        if (isEvaluator(key)) {
          allEvaluatorActions.push(allActions[key]);
        }
      }

      const filteredEvaluatorActions = allEvaluatorActions.filter(
        (action) =>
          !options.evaluators ||
          options.evaluators.split(',').includes(action.name)
      );
      if (filteredEvaluatorActions.length === 0) {
        if (allEvaluatorActions.length == 0) {
          logger.error('No evaluators installed');
        } else {
          logger.error(
            `No evaluators matched your specifed filter: ${options.evaluators}`
          );
          logger.info(
            `All available evaluators: ${allEvaluatorActions.map((action) => action.name).join(',')}`
          );
        }
        return;
      }
      logger.info(
        `Using evaluators: ${filteredEvaluatorActions.map((action) => action.name).join(',')}`
      );

      const confirmed = await confirmLlmUse(
        filteredEvaluatorActions,
        options.force
      );
      if (!confirmed) {
        return;
      }

      const scores: Record<string, EvalResponse> = {};
      const evalRunId = randomUUID();
      for (const action of filteredEvaluatorActions) {
        const name = evaluatorName(action);
        logger.info(`Running evaluator '${name}'...`);
        const response = await runner.runAction({
          key: name,
          input: {
            dataset: evalDataset,
            evalRunId,
          },
        });
        scores[name] = response.result as EvalResponse;
      }

      const scoredResults = enrichResultsWithScoring(scores, evalDataset);
      const metadata = extractMetricsMetadata(filteredEvaluatorActions);

      const evalRun = {
        key: {
          evalRunId,
          createdAt: new Date().toISOString(),
        },
        results: scoredResults,
        metricsMetadata: metadata,
      };

      logger.info(`Writing results to EvalStore...`);
      await evalStore.save(evalRun);

      if (options.output) {
        await exportFn(evalRun, options.output);
      }
    });
  });
