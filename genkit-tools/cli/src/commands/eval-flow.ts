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
  EvalInferenceInput,
  EvalInferenceInputSchema,
} from '@genkit-ai/tools-common';
import {
  EvalExporter,
  getAllEvaluatorActions,
  getDatasetStore,
  getExporterForString,
  getMatchingEvaluatorActions,
  runEvaluation,
  runInference,
} from '@genkit-ai/tools-common/eval';
import { confirmLlmUse, logger } from '@genkit-ai/tools-common/utils';
import { Command } from 'commander';
import { readFile } from 'fs/promises';
import { runWithManager } from '../utils/manager-utils';

interface EvalFlowRunCliOptions {
  input?: string;
  output?: string;
  auth?: string;
  evaluators?: string;
  force?: boolean;
  outputFormat: string;
}

const EVAL_FLOW_SCHEMA = '{samples: Array<{input: any; reference?: any;}>}';
enum SourceType {
  DATA = 'data',
  FILE = 'file',
  DATASET = 'dataset',
}

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
      await runWithManager(async (manager) => {
        if (!data && !options.input) {
          throw new Error(
            'No input data passed. Specify input data using [data] argument or --input <filename> option'
          );
        }

        let evaluatorActions: Action[];
        if (!options.evaluators) {
          evaluatorActions = await getAllEvaluatorActions(manager);
        } else {
          evaluatorActions = await getMatchingEvaluatorActions(
            manager,
            options.evaluators.split(',')
          );
        }
        logger.debug(
          `Using evaluators: ${evaluatorActions.map((action) => action.name).join(',')}`
        );

        if (!options.force) {
          const confirmed = await confirmLlmUse(evaluatorActions);
          if (!confirmed) {
            throw new Error('User declined using billed evaluators.');
          }
        }

        const sourceType = getSourceType(data, options.input);
        let targetDatasetMetadata;
        if (sourceType === SourceType.DATASET) {
          const datasetStore = await getDatasetStore();
          const datasetMetadatas = await datasetStore.listDatasets();
          targetDatasetMetadata = datasetMetadatas.find(
            (d) => d.datasetId === options.input
          );
        }

        const actionRef = `/flow/${flowName}`;
        const evalFlowInput = await readInputs(sourceType, data, options.input);
        const evalDataset = await runInference({
          manager,
          actionRef,
          evalFlowInput,
          auth: options.auth,
        });

        const evalRun = await runEvaluation({
          manager,
          evaluatorActions,
          evalDataset,
          augments: {
            actionRef: `/flow/${flowName}`,
            datasetId:
              sourceType === SourceType.DATASET ? options.input : undefined,
            datasetVersion: targetDatasetMetadata?.version,
          },
        });

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

/**
 * Reads EvalFlowInput dataset from data string or input identified.
 * Only one of these parameters is expected to be provided.
 **/
async function readInputs(
  sourceType: SourceType,
  dataField?: string,
  input?: string
): Promise<EvalInferenceInput> {
  let parsedData;
  switch (sourceType) {
    case SourceType.DATA:
      parsedData = JSON.parse(dataField!);
      break;
    case SourceType.FILE:
      parsedData = JSON.parse(await readFile(input!, 'utf8'));
      break;
    case SourceType.DATASET:
      const datasetStore = await getDatasetStore();
      const data = await datasetStore.getDataset(input!);
      // Format to match EvalInferenceInputSchema
      parsedData = { samples: data };
      break;
  }

  try {
    return EvalInferenceInputSchema.parse(parsedData);
  } catch (e) {
    throw new Error(
      `Error parsing the input. Please provide an array of inputs for the flow or a ${EVAL_FLOW_SCHEMA} object. Error: ${e}`
    );
  }
}

function getSourceType(data?: string, input?: string): SourceType {
  if (input) {
    if (data) {
      logger.warn('Both [data] and input provided, ignoring [data]...');
    }
    return input.endsWith('.json') ? SourceType.FILE : SourceType.DATASET;
  } else if (data) {
    return SourceType.DATA;
  }
  throw new Error('Must provide either data or input');
}
