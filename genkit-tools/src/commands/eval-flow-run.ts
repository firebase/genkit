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
  DocumentData,
  EvalInput,
  FlowInvokeEnvelopeMessage,
  FlowState,
  RetrieverResponse,
  SpanData,
} from '@genkit-ai/tools-common';
import {
  EvalExporter,
  enrichResultsWithScoring,
  extractMetricsMetadata,
  getEvalStore,
  getExporterForString,
} from '@genkit-ai/tools-common/eval';
import { Runner } from '@genkit-ai/tools-common/runner';
import {
  confirmLlmUse,
  evaluatorName,
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

/** Command to run a flow and evaluate the output */
export const evalFlowRun = new Command('eval:flow')
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

        const errors = states
          .filter((s) => s.operation.result?.error)
          .map((s) => s.operation.result?.error);
        if (errors.length > 0) {
          logger.error('Some flows failed with the following errors');
          logger.error(errors);
          return;
        }

        const evalDataset = await fetchDataSet(runner, flowName, states);
        const evalRunId = randomUUID();
        const scores: Record<string, any> = {};
        for (const action of filteredEvaluatorActions) {
          const name = evaluatorName(action);
          logger.info(`Running evaluator '${name}'...`);
          const response = await runner.runAction({
            key: name,
            input: {
              dataset: evalDataset,
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

async function readInputs(data: string, filePath: string): Promise<any[]> {
  const parsedData = JSON.parse(
    data ? data : await readFile(filePath!, 'utf8')
  );
  if (Array.isArray(parsedData)) {
    return parsedData as any[];
  }

  return [parsedData];
}

async function runFlows(
  runner: Runner,
  flowName: string,
  data: any[]
): Promise<FlowState[]> {
  const states: FlowState[] = [];

  for (const d of data) {
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
  states: FlowState[]
): Promise<EvalInput[]> {
  return await Promise.all(
    states.map(async (s) => {
      const traceIds = s.executions.flatMap((e) => e.traceIds);

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

      let rootSpan: SpanData | undefined = undefined;
      let retrievers: SpanData[] = [];
      for (const trace of traces) {
        const tempRootSpan = Object.values(trace.spans).find(
          (s) =>
            s.attributes['genkit:type'] === 'flow' &&
            s.attributes['genkit:metadata:flow:name'] === flowName &&
            s.attributes['genkit:metadata:flow:state'] === 'done'
        );

        if (tempRootSpan) {
          rootSpan = tempRootSpan;
        }

        retrievers.push(
          ...Object.values(trace.spans).filter(
            (s) => s.attributes['genkit:metadata:subtype'] === 'retriever'
          )
        );
      }

      if (retrievers.length > 1) {
        logger.warn('The flow contains multiple retrieve actions.');
      }

      const context = retrievers.flatMap((s) => {
        const output: RetrieverResponse = JSON.parse(
          s.attributes['genkit:output'] as string
        );
        if (!output) {
          return [];
        }
        return output.documents.flatMap((d: DocumentData) => {
          return d.content
            .map((c) => c.text)
            .filter((text): text is string => !!text);
        });
      });

      if (!rootSpan) {
        // TODO: Handle error case
      }

      return {
        testCaseId: randomUUID(),
        input: rootSpan!.attributes['genkit:input'],
        output: rootSpan!.attributes['genkit:output'],
        context,
        traceIds,
      };
    })
  );
}
