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
  Action,
  EvalFlowInput,
  EvalFlowInputSchema,
} from '@genkit-ai/tools-common';
import {
  EvalExporter,
  getDatasetStore,
  getEvalStore,
  getExporterForString,
  getMatchingEvaluators,
  runEvaluation,
  runInference,
} from '@genkit-ai/tools-common/eval';
import { confirmLlmUse, logger } from '@genkit-ai/tools-common/utils';
import { Command } from 'commander';
import { readFile } from 'fs/promises';
import { runInRunnerThenStop } from '../utils/runner-utils';

interface EvalFlowRunCliOptions {
  input?: string;
  output?: string;
  auth?: string;
  evaluators?: string;
  force?: boolean;
  outputFormat: string;
}

const EVAL_FLOW_SCHEMA = '{samples: Array<{input: any; reference?: any;}>}';

/** Command to run a flow and evaluate the output */
export const evalFlow = new Command('eval:flow')
  .description(
    'evaluate a flow against configured evaluators using provided data as input'
  )
  .argument('<flowName>', 'Name of the flow to run')
  .argument('[data]', 'JSON data to use to start the flow')
  .option(
    '--input <input>',
    'Input dataset ID or JSON file to be used for evaluation'
  )
  .option(
    '-a, --auth <JSON>',
    'JSON object passed to authPolicy and stored in local state as auth',
    ''
  )
  .option(
    '-o, --output <filename>',
    'Name of the output file to write evaluation results. Defaults to json output.'
  )
  // TODO: Figure out why passing a new Option with choices doesn't work
  .option(
    '--output-format <format>',
    'The output file format (csv, json)',
    'json'
  )
  .option(
    '-e, --evaluators <evaluators>',
    'comma separated list of evaluators to use (by default uses all)'
  )
  .option('-f, --force', 'Automatically accept all interactive prompts')
  .action(
    async (flowName: string, data: string, options: EvalFlowRunCliOptions) => {
      await runInRunnerThenStop(async (runner) => {
        if (!data && !options.input) {
          throw new Error(
            'No input data passed. Specify input data using [data] argument or --input <filename> option'
          );
        }

        let filteredEvaluatorActions: Action[];
        filteredEvaluatorActions = await getMatchingEvaluators(
          runner,
          options.evaluators
        );
        logger.debug(
          `Using evaluators: ${filteredEvaluatorActions.map((action) => action.name).join(',')}`
        );

        if (!options.force) {
          const confirmed = await confirmLlmUse(filteredEvaluatorActions);
          if (!confirmed) {
            throw new Error('User declined using billed evaluators.');
          }
        }

        const actionRef = `/flow/${flowName}`;
        const evalFlowInput = await readInputs(data, options.input);
        const evalDataset = await runInference({
          runner,
          actionRef,
          evalFlowInput,
          auth: options.auth,
        });

        const evalRun = await runEvaluation({
          runner,
          filteredEvaluatorActions,
          evalDataset,
          actionRef: `/flow/${flowName}`,
          datasetId: !options.input?.endsWith('.json')
            ? options.input
            : undefined,
        });

        const evalStore = getEvalStore();
        await evalStore.save(evalRun);

        if (options.output) {
          const exportFn: EvalExporter = getExporterForString(
            options.outputFormat
          );
          await exportFn(evalRun, options.output);
        }

        console.log(
          `Succesfully ran evaluation, with evalId: ${evalRun.key.evalRunId}`
        );
      });
    }
  );

async function readInputs(
  data?: string,
  input?: string
): Promise<EvalFlowInput> {
  let parsedData;
  if (input) {
    if (data) {
      logger.warn('Both [data] and input provided, ignoring [data]...');
    }
    const isFile = input.endsWith('.json');
    if (isFile) {
      parsedData = JSON.parse(await readFile(input, 'utf8'));
    } else {
      const datasetStore = await getDatasetStore();
      parsedData = await datasetStore.getDataset(input);
    }
  }

  if (data) {
    parsedData = JSON.parse(data);
  }
  if (Array.isArray(parsedData)) {
    return parsedData as any[];
  }

  try {
    return EvalFlowInputSchema.parse(parsedData);
  } catch (e) {
    throw new Error(
      `Error parsing the input. Please provide an array of inputs for the flow or a ${EVAL_FLOW_SCHEMA} object. Error: ${e}`
    );
  }
}
