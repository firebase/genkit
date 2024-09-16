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

import { randomUUID } from 'crypto';
import { readFile } from 'fs/promises';
import { EvalFlowInput, EvalFlowInputSchema, getEvalStore } from '.';
import { Runner } from '../runner';
import { Action, EvalInput, EvalRun, RunActionResponse } from '../types';
import {
  confirmLlmUse,
  evaluatorName,
  getEvalExtractors,
  isEvaluator,
  logger,
} from '../utils';
import { EvalExporter, getExporterForString } from './exporter';
import { enrichResultsWithScoring, extractMetricsMetadata } from './parser';

export interface EvalFlowRunOptions {
  input?: string;
  output?: string;
  auth?: string;
  evaluators?: string;
  interactive?: boolean;
  outputFormat: string;
}

interface EvalRunOptions {
  output?: string;
  evaluators?: string;
  interactive?: boolean;
  outputFormat: string;
  auth?: string;
}

interface BulkRunResponse {
  traceId?: string;
  hasErrored: boolean;
  response: any;
}

interface EvaluationResponse {
  evalRunId?: string;
  success: boolean;
  error?: string;
}

const EVAL_FLOW_SCHEMA = '{samples: Array<{input: any; reference?: any;}>}';
export async function evalFlow(
  runner: Runner,
  flowName: string,
  data: string,
  options: EvalFlowRunOptions
): Promise<EvaluationResponse> {
  if (!data && !options.input) {
    return {
      success: false,
      error:
        'No input data passed. Specify input data using [data] argument or --input <filename> option',
    };
  }

  let filteredEvaluatorActions: Action[];
  try {
    filteredEvaluatorActions = await getMatchingEvaluators(
      runner,
      options.evaluators
    );
  } catch (e) {
    if (e instanceof Error) {
      return { success: false, error: e.message };
    }
    return { success: false, error: 'Error during extracting evaluators' };
  }
  logger.debug(
    `Using evaluators: ${filteredEvaluatorActions.map((action) => action.name).join(',')}`
  );

  if (options.interactive) {
    const confirmed = await confirmLlmUse(filteredEvaluatorActions);
    if (!confirmed) {
      return {
        success: false,
        error: 'User declined using billed evaluators.',
      };
    }
  }

  const actionRef = `/flow/${flowName}`;
  const parsedData = await readInputs(data, options.input!);
  const evalDataset = await runInference(runner, actionRef, parsedData);

  const evalRun = await runEvaluation(
    runner,
    filteredEvaluatorActions,
    evalDataset,
    options.auth,
    `/flow/${flowName}`
  );

  const evalStore = getEvalStore();
  await evalStore.save(evalRun);

  if (options.output) {
    const exportFn: EvalExporter = getExporterForString(options.outputFormat);
    await exportFn(evalRun, options.output);
  }

  return { evalRunId: evalRun.key.evalRunId, success: true };
}

export async function evalRun(
  runner: Runner,
  dataset: string,
  options: EvalRunOptions
): Promise<EvaluationResponse> {
  if (!dataset) {
    return {
      success: false,
      error: 'No input data passed. Specify input data using [data] argument',
    };
  }

  let filteredEvaluatorActions: Action[];
  try {
    filteredEvaluatorActions = await getMatchingEvaluators(
      runner,
      options.evaluators
    );
  } catch (e) {
    if (e instanceof Error) {
      return { success: false, error: e.message };
    }
    return { success: false, error: 'Error during extracting evaluators' };
  }
  logger.info(
    `Using evaluators: ${filteredEvaluatorActions.map((action) => action.name).join(',')}`
  );

  if (options.interactive) {
    const confirmed = await confirmLlmUse(filteredEvaluatorActions);
    if (!confirmed) {
      return {
        success: false,
        error: 'User declined using billed evaluators.',
      };
    }
  }

  const evalDataset: EvalInput[] = JSON.parse(
    (await readFile(dataset)).toString('utf-8')
  ).map((testCase: any) => ({
    ...testCase,
    testCaseId: testCase.testCaseId || randomUUID(),
    traceIds: testCase.traceIds || [],
  }));
  const evalRun = await runEvaluation(
    runner,
    filteredEvaluatorActions,
    evalDataset,
    options.auth,
    undefined
  );

  logger.info(`Writing results to EvalStore...`);
  const evalStore = getEvalStore();
  await evalStore.save(evalRun);

  if (options.output) {
    const exportFn: EvalExporter = getExporterForString(options.outputFormat);
    await exportFn(evalRun, options.output);
  }

  return {
    success: true,
    evalRunId: evalRun.key.evalRunId,
  };
}

/** Handles the Inference part of Inference-Evaluation cycle */
async function runInference(
  runner: Runner,
  actionRef: string,
  evalFlowInput: EvalFlowInput
): Promise<EvalInput[]> {
  let inputs: any[] = Array.isArray(evalFlowInput)
    ? (evalFlowInput as any[])
    : evalFlowInput.samples.map((c) => c.input);

  const runResponses = await bulkRunAction(runner, actionRef, inputs);
  const runStates: BulkRunResponse[] = runResponses.map((r) => {
    return {
      traceId: r.telemetry?.traceId,
      // todo: how to track errors
      hasErrored: !r.telemetry?.traceId,
      response: r.result,
    } as BulkRunResponse;
  });
  if (runStates.some((s) => s.hasErrored)) {
    logger.debug('Some flows failed with errors');
  }

  const evalDataset = await fetchDataSet(
    runner,
    actionRef,
    runStates,
    evalFlowInput
  );
  return evalDataset;
}

/** Handles the Evaluation part of Inference-Evaluation cycle */
async function runEvaluation(
  runner: Runner,
  filteredEvaluatorActions: Action[],
  evalDataset: EvalInput[],
  auth?: string,
  actionRef?: string
): Promise<EvalRun> {
  const evalRunId = randomUUID();
  const scores: Record<string, any> = {};
  for (const action of filteredEvaluatorActions) {
    const name = evaluatorName(action);
    const response = await runner.runAction({
      key: name,
      input: {
        dataset: evalDataset.filter((row) => !row.error),
        evalRunId,
        auth: auth ? JSON.parse(auth) : undefined,
      },
    });
    scores[name] = response.result;
  }

  const scoredResults = enrichResultsWithScoring(scores, evalDataset);
  const metadata = extractMetricsMetadata(filteredEvaluatorActions);

  const evalRun = {
    key: {
      actionRef,
      evalRunId,
      createdAt: new Date().toISOString(),
    },
    results: scoredResults,
    metricsMetadata: metadata,
  };
  return evalRun;
}

async function getMatchingEvaluators(
  runner: Runner,
  evaluators?: string
): Promise<Action[]> {
  const allActions = await runner.listActions();
  const allEvaluatorActions = [];
  for (const key in allActions) {
    if (isEvaluator(key)) {
      allEvaluatorActions.push(allActions[key]);
    }
  }
  const filteredEvaluatorActions = allEvaluatorActions.filter(
    (action) => !evaluators || evaluators.split(',').includes(action.name)
  );
  if (filteredEvaluatorActions.length === 0) {
    if (allEvaluatorActions.length == 0) {
      throw new Error('No evaluators installed');
    } else {
      const availableActions = allEvaluatorActions
        .map((action) => action.name)
        .join(',');
      throw new Error(
        `No evaluators matched your specifed filter: ${evaluators}. All available evaluators: '${availableActions}'`
      );
    }
  }
  return filteredEvaluatorActions;
}

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

async function bulkRunAction(
  runner: Runner,
  actionRef: string,
  inputs: any[]
): Promise<RunActionResponse[]> {
  let responses: RunActionResponse[] = [];
  for (const d of inputs) {
    logger.info(`Running '${actionRef}' ...`);
    let response = await runner.runAction({
      key: actionRef,
      input: {
        start: {
          input: d,
        },
      },
    });
    responses.push(response);
  }

  return responses;
}

async function fetchDataSet(
  runner: Runner,
  flowName: string,
  states: BulkRunResponse[],
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
      const traceId = s.traceId;
      if (!traceId) {
        logger.warn('No traceId available...');
        return {
          // TODO Replace this with unified trace class
          testCaseId: randomUUID(),
          traceIds: [],
        };
      }

      const trace = await runner.getTrace({
        // TODO: We should consider making this a argument and using it to
        // to control which tracestore environment is being used when
        // running a flow.
        env: 'dev',
        traceId,
      });

      let inputs: string[] = [];
      let outputs: string[] = [];
      let contexts: string[] = [];

      inputs.push(extractors.input(trace));
      outputs.push(extractors.output(trace));
      contexts.push(extractors.context(trace));

      if (s.hasErrored) {
        return {
          testCaseId: randomUUID(),
          input: inputs[0],
          error: 'Inference error',
          reference: references?.at(i),
          traceIds: [traceId],
        };
      }

      return {
        // TODO Replace this with unified trace class
        testCaseId: randomUUID(),
        input: inputs[0],
        output: outputs[0],
        context: JSON.parse(contexts[0]) as string[],
        reference: references?.at(i),
        traceIds: [traceId],
      };
    })
  );
}
