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
import { RuntimeManager } from '../manager/manager';
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
  getEvalExtractors,
  isEvaluator,
  logger,
  stackTraceSpans,
} from '../utils';
import { enrichResultsWithScoring, extractMetricsMetadata } from './parser';

interface BulkRunResponse {
  traceId?: string;
  response?: any;
}

const SUPPORTED_ACTION_TYPES = ['flow', 'model'] as const;

/**
 * Starts a new evaluation run. Intended to be used via the reflection API.
 */
export async function runNewEvaluation(
  manager: RuntimeManager,
  request: RunNewEvaluationRequest
): Promise<EvalRunKey> {
  const { datasetId, actionRef, evaluators } = request;
  const datasetStore = await getDatasetStore();
  logger.info(`Fetching dataset ${datasetId}...`);
  const dataset = await datasetStore.getDataset(datasetId);

  logger.info('Running inference...');
  const evalDataset = await runInference({
    manager,
    actionRef,
    evalFlowInput: dataset,
    auth: request.options?.auth,
  });
  const evaluatorAction = await getMatchingEvaluatorActions(
    manager,
    evaluators
  );

  logger.info('Running evaluation...');
  const evalRun = await runEvaluation({
    manager,
    evaluatorActions: evaluatorAction,
    evalDataset,
    actionRef,
    datasetId,
  });
  logger.info('Finished evaluation, returning key...');
  const evalStore = getEvalStore();
  await evalStore.save(evalRun);

  return evalRun.key;
}

/** Handles the Inference part of Inference-Evaluation cycle */
export async function runInference(params: {
  manager: RuntimeManager;
  actionRef: string;
  evalFlowInput: EvalFlowInput;
  auth?: string;
}): Promise<EvalInput[]> {
  const { manager, actionRef, evalFlowInput, auth } = params;
  if (!isSupportedActionRef(actionRef)) {
    throw new Error('Inference is only supported on flows and models');
  }
  let inputs: any[] = Array.isArray(evalFlowInput)
    ? (evalFlowInput as any[])
    : evalFlowInput.samples.map((c) => c.input);

  const runResponses: BulkRunResponse[] = await bulkRunAction({
    manager,
    actionRef,
    inputs,
    auth,
  });

  const evalDataset = await fetchEvalInput({
    manager,
    actionRef,
    states: runResponses,
    parsedData: evalFlowInput,
  });
  return evalDataset;
}

/** Handles the Evaluation part of Inference-Evaluation cycle */
export async function runEvaluation(params: {
  manager: RuntimeManager;
  evaluatorActions: Action[];
  evalDataset: EvalInput[];
  actionRef?: string;
  datasetId?: string;
}): Promise<EvalRun> {
  const { manager, evaluatorActions, evalDataset, actionRef, datasetId } =
    params;
  const evalRunId = randomUUID();
  const scores: Record<string, any> = {};
  for (const action of evaluatorActions) {
    const name = evaluatorName(action);
    const response = await manager.runAction({
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
      datasetId,
      createdAt: new Date().toISOString(),
    },
    results: scoredResults,
    metricsMetadata: metadata,
  };
  return evalRun;
}

export async function getAllEvaluatorActions(
  manager: RuntimeManager
): Promise<Action[]> {
  const allActions = await manager.listActions();
  const allEvaluatorActions = [];
  for (const key in allActions) {
    if (isEvaluator(key)) {
      allEvaluatorActions.push(allActions[key]);
    }
  }
  return allEvaluatorActions;
}

export async function getMatchingEvaluatorActions(
  manager: RuntimeManager,
  evaluators?: string[]
): Promise<Action[]> {
  if (!evaluators) {
    return [];
  }
  const allEvaluatorActions = await getAllEvaluatorActions(manager);
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
  manager: RuntimeManager;
  actionRef: string;
  inputs: any[];
  auth?: string;
}): Promise<BulkRunResponse[]> {
  const { manager, actionRef, inputs, auth } = params;
  let responses: BulkRunResponse[] = [];
  for (const d of inputs) {
    logger.info(`Running '${actionRef}' ...`);
    let response: BulkRunResponse;
    try {
      const runActionResponse = await manager.runAction({
        key: actionRef,
        input: {
          start: {
            input: d,
          },
          auth: auth ? JSON.parse(auth) : undefined,
        },
      });
      response = {
        traceId: runActionResponse.telemetry?.traceId,
        response: runActionResponse.result,
      };
    } catch (e: any) {
      const traceId = e?.data?.details?.traceId;
      response = { traceId };
    }
    responses.push(response);
  }

  return responses;
}

async function fetchEvalInput(params: {
  manager: RuntimeManager;
  actionRef: string;
  states: BulkRunResponse[];
  parsedData: EvalFlowInput;
}): Promise<EvalInput[]> {
  const { manager, actionRef, states, parsedData } = params;

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
  const extractors = await getEvalExtractors(actionRef);
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

      const trace = await manager.getTrace({
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
          testCaseId: randomUUID(),
          input: inputs[0],
          error: `Unable to extract any spans from trace ${traceId}`,
          reference: references?.at(i),
          traceIds: [traceId],
        };
      }

      if (nestedSpan.attributes['genkit:state'] === 'error') {
        return {
          testCaseId: randomUUID(),
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

function isSupportedActionRef(actionRef: string) {
  return SUPPORTED_ACTION_TYPES.some((supportedType) =>
    actionRef.startsWith(`/${supportedType}`)
  );
}
