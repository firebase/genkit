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
  EvalInput,
  FlowInvokeEnvelopeMessage,
  FlowState,
} from '@genkit-ai/tools-common';
import {
  EvalExporter,
  EvalFlowInput,
  EvalFlowInputSchema,
  enrichResultsWithScoring,
  extractMetricsMetadata,
  getEvalStore,
  getExporterForString,
} from '@genkit-ai/tools-common/eval';
import { Runner } from '@genkit-ai/tools-common/runner';
import {
  confirmLlmUse,
  evaluatorName,
  getEvalExtractors,
  isEvaluator,
  logger,
  runInRunnerThenStop,
  waitForFlowToComplete,
} from '@genkit-ai/tools-common/utils';
import { Command } from 'commander';
import { randomUUID } from 'crypto';
import { readFile } from 'fs/promises';

// TODO: Support specifying waiting or streaming
interface EvalFlowRunOptions {
  input?: string;
  output?: string;
  auth?: string;
  evaluators?: string;
  force?: boolean;
  outputFormat: string;
}

interface FlowRunState {
  state: FlowState;
  hasErrored: boolean;
  error?: string;
}

const EVAL_FLOW_SCHEMA = '{samples: Array<{input: any; reference?: any;}>}';

/** Command to run a flow and evaluate the output */
export const evalFlow = new Command('eval:flow')
  .description(
    'evaluate a flow against configured evaluators using provided data as input'
  )
  .argument('<flowName>', 'Name of the flow to run')
  .argument('[data]', 'JSON data to use to start the flow')
  .option('--input <filename>', 'JSON batch data to use to run the flow')
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
    async (flowName: string, data: string, options: EvalFlowRunOptions) => {
      await runInRunnerThenStop(async (runner) => {
        const evalStore = getEvalStore();
        let exportFn: EvalExporter = getExporterForString(options.outputFormat);
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

        if (!data && !options.input) {
          logger.error(
            'No input data passed. Specify input data using [data] argument or --input <filename> option'
          );
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

        const parsedData = await readInputs(data, options.input!);

        const states = await runFlows(runner, flowName, parsedData);

        const runStates: FlowRunState[] = states.map((s) => {
          return {
            state: s,
            hasErrored: !!s.operation.result?.error,
            error: s.operation.result?.error,
          } as FlowRunState;
        });
        if (runStates.some((s) => s.hasErrored)) {
          logger.error('Some flows failed with errors');
        }

        const evalDataset = await fetchDataSet(
          runner,
          flowName,
          runStates,
          parsedData
        );
        const evalRunId = randomUUID();
        const scores: Record<string, any> = {};
        for (const action of filteredEvaluatorActions) {
          const name = evaluatorName(action);
          logger.info(`Running evaluator '${name}'...`);
          const response = await runner.runAction({
            key: name,
            input: {
              dataset: evalDataset.filter((row) => !row.error),
              evalRunId,
              auth: options.auth ? JSON.parse(options.auth) : undefined,
            },
          });
          scores[name] = response.result;
        }

        const scoredResults = enrichResultsWithScoring(scores, evalDataset);
        const metadata = extractMetricsMetadata(filteredEvaluatorActions);

        const evalRun = {
          key: {
            actionId: flowName,
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
    }
  );

async function readInputs(
  data: string,
  filePath: string
): Promise<EvalFlowInput> {
  const parsedData = JSON.parse(
    data ? data : await readFile(filePath!, 'utf8')
  );
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

async function runFlows(
  runner: Runner,
  flowName: string,
  data: EvalFlowInput
): Promise<FlowState[]> {
  const states: FlowState[] = [];
  let inputs: any[] = Array.isArray(data)
    ? (data as any[])
    : data.samples.map((c) => c.input);

  for (const d of inputs) {
    logger.info(`Running '/flow/${flowName}' ...`);
    let state = (
      await runner.runAction({
        key: `/flow/${flowName}`,
        input: {
          start: {
            input: d,
          },
        } as FlowInvokeEnvelopeMessage,
      })
    ).result as FlowState;

    if (!state?.operation.done) {
      logger.info('Started flow run, waiting for it to complete...');
      state = await waitForFlowToComplete(runner, flowName, state.flowId);
    }

    logger.info(
      'Flow operation:\n' + JSON.stringify(state.operation, undefined, '  ')
    );

    states.push(state);
  }

  return states;
}

async function fetchDataSet(
  runner: Runner,
  flowName: string,
  states: FlowRunState[],
  parsedData: EvalFlowInput
): Promise<EvalInput[]> {
  let references: any[] | undefined = undefined;
  if (!Array.isArray(parsedData)) {
    const maybeReferences = parsedData.samples.map((c: any) => c.reference);
    if (maybeReferences.length === states.length) {
      references = maybeReferences;
    } else {
      logger.warn(
        'The input size does not match the flow states generated. Ignoring reference mapping...'
      );
    }
  }
  const extractors = await getEvalExtractors(flowName);
  return await Promise.all(
    states.map(async (s, i) => {
      const traceIds = s.state.executions.flatMap((e) => e.traceIds);
      if (traceIds.length > 1) {
        logger.warn('The flow is split across multiple traces');
      }

      const traces = await Promise.all(
        traceIds.map(async (traceId) =>
          runner.getTrace({
            // TODO: We should consider making this a argument and using it to
            // to control which tracestore environment is being used when
            // running a flow.
            env: 'dev',
            traceId,
          })
        )
      );

      let inputs: string[] = [];
      let outputs: string[] = [];
      let contexts: string[] = [];

      // First extract inputs for all traces
      traces.forEach((trace) => {
        inputs.push(extractors.input(trace));
      });

      if (s.hasErrored) {
        return {
          testCaseId: randomUUID(),
          input: inputs[0],
          error: s.error,
          reference: references?.at(i),
          traceIds,
        };
      }

      traces.forEach((trace) => {
        outputs.push(extractors.output(trace));
        contexts.push(extractors.context(trace));
      });

      return {
        // TODO Replace this with unified trace class
        testCaseId: randomUUID(),
        input: inputs[0],
        output: outputs[0],
        context: JSON.parse(contexts[0]) as string[],
        reference: references?.at(i),
        traceIds,
      };
    })
  );
}
