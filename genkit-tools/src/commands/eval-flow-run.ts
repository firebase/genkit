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
import { randomUUID } from 'crypto';
import { readFile, writeFile } from 'fs/promises';
import {
  EvalInput,
  LocalFileEvalStore,
  enrichResultsWithScoring,
} from '../eval';
import { Runner } from '../runner/runner';
import { FlowInvokeEnvelopeMessage, FlowState } from '../types/flow';
import { DocumentData, RetrieverResponse } from '../types/retrievers';
import { SpanData } from '../types/trace';
import {
  EVALUATOR_ACTION_PREFIX,
  stripEvaluatorNamePrefix,
} from '../utils/eval';
import { logger } from '../utils/logger';
import {
  runInRunnerThenStop,
  waitForFlowToComplete,
} from '../utils/runner-utils';

// TODO: Support specifying waiting or streaming
interface EvalFlowRunOptions {
  input?: string;
  output?: string;
  auth?: string;
  evaluators?: string;
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
    '--output <filename>',
    'Name of the output file to write evaluation results'
  )
  .option(
    '--evaluators <evaluators>',
    'comma separated list of evaluators to use (by default uses all)'
  )
  .action(
    async (flowName: string, data: string, options: EvalFlowRunOptions) => {
      await runInRunnerThenStop(async (runner) => {
        const evalStore = new LocalFileEvalStore();
        const allEvaluatorActions = Object.keys(
          await runner.listActions()
        ).filter((name) => name.startsWith(EVALUATOR_ACTION_PREFIX));
        const filteredEvaluatorActions = allEvaluatorActions.filter(
          (name) =>
            !options.evaluators ||
            options.evaluators
              .split(',')
              .includes(stripEvaluatorNamePrefix(name))
        );
        if (filteredEvaluatorActions.length === 0) {
          if (allEvaluatorActions.length == 0) {
            logger.error('No evaluators installed');
          } else {
            logger.error(
              `No evaluators matched your specifed filter: ${options.evaluators}`
            );
            logger.info(
              `All available evaluators: ${allEvaluatorActions.map(stripEvaluatorNamePrefix).join(',')}`
            );
          }
          return;
        }
        logger.info(
          `Using evaluators: ${filteredEvaluatorActions.map(stripEvaluatorNamePrefix).join(',')}`
        );

        if (!data && !options.input) {
          logger.error(
            'No input data passed. Specify input data using [data] argument or --input <filename> option'
          );
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

        const datasetToEval = await fetchDataSet(runner, flowName, states);

        const scores: Record<string, any> = {};
        await Promise.all(
          filteredEvaluatorActions.map(async (e) => {
            logger.info(`Running evaluator '${e}'...`);
            const response = await runner.runAction({
              key: e,
              input: {
                dataset: datasetToEval,
                auth: options.auth ? JSON.parse(options.auth) : undefined,
              },
            });
            scores[e] = response.result;
          })
        );

        const scoredResults = enrichResultsWithScoring(scores, datasetToEval);

        if (options.output) {
          logger.info(`Writing results to '${options.output}'...`);
          await writeFile(
            options.output,
            JSON.stringify(scoredResults, undefined, '  ')
          );
        }

        logger.info(`Writing results to EvalStore...`);
        await evalStore.save({
          key: {
            actionId: flowName,
            evalRunId: randomUUID(),
            createdAt: new Date().toISOString(),
          },
          results: scoredResults,
        });
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
    var state = (
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

      var rootSpan: SpanData | undefined = undefined;
      var retrievers: SpanData[] = [];
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
