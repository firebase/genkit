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
import { EvalFlowInput, getDatasetStore, getEvalStore } from '.';
import { Runner } from '../runner';
import {
  Action,
  EvalInput,
  EvalRun,
  EvalRunKey,
  RunNewEvaluationRequest,
  SpanData,
} from '../types';
import {
  evaluatorName,
  generateTestCaseId,
  getEvalExtractors,
  isEvaluator,
  logger,
  stackTraceSpans,
} from '../utils';
import { enrichResultsWithScoring, extractMetricsMetadata } from './parser';

interface BulkRunResponse {
  traceId?: string;
  testCaseId: string;
  response?: any;
}

/**
 * Starts a new evaluation run. Intended to be used via the reflection API.
 */
export async function runNewEvaluation(
  runner: Runner,
  request: RunNewEvaluationRequest
): Promise<EvalRunKey> {
  const { datasetId, actionRef, evaluators } = request;
  const datasetStore = await getDatasetStore();
  logger.info(`Fetching dataset ${datasetId}...`);
  const dataset = await datasetStore.getDataset(datasetId);
  const datasetMetadatas = await datasetStore.listDatasets();
  const targetDataset = datasetMetadatas.find((d) => d.datasetId === datasetId);

  logger.info('Running inference...');
  const evalDataset = await runInference({
    runner,
    actionRef,
    evalFlowInput: dataset,
    auth: request.options?.auth,
  });
  const evaluatorActions = await getMatchingEvaluatorActions(
    runner,
    evaluators
  );

  logger.info('Running evaluation...');
  const evalRun = await runEvaluation({
    runner,
    evaluatorActions,
    evalDataset,
    actionRef,
  });
  // Augment metadata in evalKey
  evalRun.key = {
    ...evalRun.key,
    datasetId,
    datasetVersion: targetDataset?.version,
  };
  logger.info('Finished evaluation, writing key...');
  const evalStore = getEvalStore();
  await evalStore.save(evalRun);

  return evalRun.key;
}

/** Handles the Inference part of Inference-Evaluation cycle */
export async function runInference(params: {
  runner: Runner;
  actionRef: string;
  evalFlowInput: EvalFlowInput;
  auth?: string;
}): Promise<EvalInput[]> {
  const { runner, actionRef, evalFlowInput, auth } = params;
  if (!actionRef.startsWith('/flow')) {
    // TODO(ssbushi): Support model inference
    throw new Error('Inference is only supported on flows');
  }

  const runResponses: BulkRunResponse[] = await bulkRunAction({
    runner,
    actionRef,
    evalFlowInput,
    auth,
  });

  // TODO(ssbushi): Support model inference
  const evalDataset = await fetchEvalInput({
    runner,
    actionRef,
    states: runResponses,
    parsedData: evalFlowInput,
  });
  return evalDataset;
}

/** Handles the Evaluation part of Inference-Evaluation cycle */
export async function runEvaluation(params: {
  runner: Runner;
  evaluatorActions: Action[];
  evalDataset: EvalInput[];
  actionRef?: string;
}): Promise<EvalRun> {
  const { runner, evaluatorActions, evalDataset, actionRef } = params;
  const evalRunId = randomUUID();
  const scores: Record<string, any> = {};
  for (const action of evaluatorActions) {
    const name = evaluatorName(action);
    const response = await runner.runAction({
      key: name,
      input: {
        dataset: evalDataset.filter((row) => !row.error),
        evalRunId,
      },
    });
    scores[name] = response.result;
  }

  const scoredResults = enrichResultsWithScoring(scores, evalDataset);
  const metadata = extractMetricsMetadata(evaluatorActions);

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

export async function getAllEvaluatorActions(
  runner: Runner
): Promise<Action[]> {
  const allActions = await runner.listActions();
  const allEvaluatorActions = [];
  for (const key in allActions) {
    if (isEvaluator(key)) {
      allEvaluatorActions.push(allActions[key]);
    }
  }
  return allEvaluatorActions;
}

export async function getMatchingEvaluatorActions(
  runner: Runner,
  evaluators?: string[]
): Promise<Action[]> {
  if (!evaluators) {
    return [];
  }
  const allEvaluatorActions = await getAllEvaluatorActions(runner);
  const filteredEvaluatorActions = allEvaluatorActions.filter((action) =>
    evaluators.includes(action.name)
  );
  if (filteredEvaluatorActions.length === 0) {
    if (allEvaluatorActions.length == 0) {
      throw new Error('No evaluators installed');
    }
  }
  return filteredEvaluatorActions;
}

async function bulkRunAction(params: {
  runner: Runner;
  actionRef: string;
  evalFlowInput: EvalFlowInput;
  auth?: string;
}): Promise<BulkRunResponse[]> {
  const { runner, actionRef, evalFlowInput, auth } = params;
  let inputs: { input?: any; testCaseId: string }[] = Array.isArray(
    evalFlowInput
  )
    ? (evalFlowInput as any[]).map((i) => ({
        input: i,
        testCaseId: generateTestCaseId(),
      }))
    : evalFlowInput.samples.map((c) => ({
        ...c,
        testCaseId: c.testCaseId ?? generateTestCaseId(),
      }));

  let responses: BulkRunResponse[] = [];
  for (const d of inputs) {
    logger.info(`Running '${actionRef}' ...`);
    let response: BulkRunResponse;
    try {
      const runActionResponse = await runner.runAction({
        key: actionRef,
        input: {
          start: {
            input: d.input,
          },
          auth: auth ? JSON.parse(auth) : undefined,
        },
      });
      response = {
        testCaseId: d.testCaseId,
        traceId: runActionResponse.telemetry?.traceId,
        response: runActionResponse.result,
      };
    } catch (e: any) {
      const traceId = e?.data?.details?.traceId;
      response = { testCaseId: d.testCaseId, traceId };
    }
    responses.push(response);
  }

  return responses;
}

async function fetchEvalInput(params: {
  runner: Runner;
  actionRef: string;
  states: BulkRunResponse[];
  parsedData: EvalFlowInput;
}): Promise<EvalInput[]> {
  const { runner, actionRef, states, parsedData } = params;
  const flowName = actionRef.split('/')[-1];

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
          testCaseId: s.testCaseId,
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

      const nestedSpan = stackTraceSpans(trace);
      if (!nestedSpan) {
        return {
          testCaseId: s.testCaseId,
          input: inputs[0],
          error: `Unable to extract any spans from trace ${traceId}`,
          reference: references?.at(i),
          traceIds: [traceId],
        };
      }

      if (nestedSpan.attributes['genkit:state'] === 'error') {
        return {
          testCaseId: s.testCaseId,
          input: inputs[0],
          error:
            getSpanErrorMessage(nestedSpan) ??
            `Unknown error in trace${traceId}`,
          reference: references?.at(i),
          traceIds: [traceId],
        };
      }

      outputs.push(extractors.output(trace));
      contexts.push(extractors.context(trace));

      return {
        // TODO Replace this with unified trace class
        testCaseId: s.testCaseId,
        input: inputs[0],
        output: outputs[0],
        context: JSON.parse(contexts[0]) as string[],
        reference: references?.at(i),
        traceIds: [traceId],
      };
    })
  );
}

function getSpanErrorMessage(span: SpanData): string | undefined {
  if (span && span.status?.code === 2 /* SpanStatusCode.ERROR */) {
    // It's possible for a trace to have multiple exception events,
    // however we currently only expect and display the first one.
    const event = span.timeEvents?.timeEvent
      ?.filter((e) => e.annotation.description === 'exception')
      .shift();
    return (
      (event?.annotation?.attributes['exception.message'] as string) ?? 'Error'
    );
  }
}
