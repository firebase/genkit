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
  FlowActionInputSchema,
  GenerateRequest,
  MessageData,
  MessageSchema,
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

interface InferenceRunState {
  input: any;
  reference?: any;
  traceId?: string;
  response?: any;
  evalError?: string;
}

const SUPPORTED_ACTION_TYPES = ['flow', 'model'] as const;

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

  logger.info('Running inference...');
  const evalDataset = await runInference({
    runner,
    actionRef,
    evalFlowInput: dataset,
    auth: request.options?.auth,
    actionConfig: request.options?.actionConfig,
  });
  const evaluatorActions = await getMatchingEvaluatorActions(
    runner,
    evaluators
  );

  const evalRun = await runEvaluation({
    runner,
    evaluatorActions,
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
  runner: Runner;
  actionRef: string;
  evalFlowInput: EvalFlowInput;
  auth?: string;
  actionConfig?: any;
}): Promise<EvalInput[]> {
  const { runner, actionRef, evalFlowInput, auth, actionConfig } = params;
  if (!isSupportedActionRef(actionRef)) {
    throw new Error('Inference is only supported on flows and models');
  }

  const evalDataset: EvalInput[] = await bulkRunAction({
    runner,
    actionRef,
    evalFlowInput,
    auth,
    actionConfig,
  });
  return evalDataset;
}

/** Handles the Evaluation part of Inference-Evaluation cycle */
export async function runEvaluation(params: {
  runner: Runner;
  evaluatorActions: Action[];
  evalDataset: EvalInput[];
  actionRef?: string;
  datasetId?: string;
}): Promise<EvalRun> {
  const { runner, evaluatorActions, evalDataset, actionRef, datasetId } =
    params;
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
      datasetId,
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
  actionConfig?: any;
}): Promise<EvalInput[]> {
  const { runner, actionRef, evalFlowInput, auth, actionConfig } = params;
  const isModelAction = actionRef.startsWith('/model');
  let inputs: { input: string; reference?: string }[] = Array.isArray(
    evalFlowInput
  )
    ? evalFlowInput.map((i) => ({ input: i }))
    : evalFlowInput.samples.map((c) => ({
        input: c.input,
        reference: c.reference,
      }));

  let evalInputs: EvalInput[] = [];
  for (const sample of inputs) {
    logger.info(`Running '${actionRef}' ...`);
    if (isModelAction) {
      evalInputs.push(
        await runModelAction({
          runner,
          actionRef,
          input: sample.input,
          reference: sample.reference,
          modelConfig: actionConfig,
        })
      );
    } else {
      evalInputs.push(
        await runFlowAction({
          runner,
          actionRef,
          input: sample.input,
          reference: sample.reference,
          auth,
        })
      );
    }
  }
  return evalInputs;
}

async function runFlowAction(params: {
  runner: Runner;
  actionRef: string;
  input: any;
  reference?: any;
  auth?: any;
}): Promise<EvalInput> {
  const { runner, actionRef, input, auth, reference } = { ...params };
  let state: InferenceRunState;
  try {
    const flowInput = FlowActionInputSchema.parse({
      start: {
        input,
      },
      auth: auth ? JSON.parse(auth) : undefined,
    });
    const runActionResponse = await runner.runAction({
      key: actionRef,
      input: flowInput,
    });
    state = {
      reference,
      input,
      traceId: runActionResponse.telemetry?.traceId,
      response: runActionResponse.result,
    };
  } catch (e: any) {
    const traceId = e?.data?.details?.traceId;
    state = {
      input,
      reference,
      traceId,
      evalError: `Error when running inference. Details: ${e?.message ?? e}`,
    };
  }
  return gatherEvalInput({ runner, actionRef, state });
}

async function runModelAction(params: {
  runner: Runner;
  actionRef: string;
  input: any;
  reference?: any;
  modelConfig?: any;
}): Promise<EvalInput> {
  const { runner, actionRef, input, modelConfig, reference } = { ...params };
  let state: InferenceRunState;
  try {
    const modelInput = getModelInput(input, modelConfig);
    const runActionResponse = await runner.runAction({
      key: actionRef,
      input: modelInput,
    });
    state = {
      input,
      reference,
      traceId: runActionResponse.telemetry?.traceId,
      response: runActionResponse.result,
    };
  } catch (e: any) {
    const traceId = e?.data?.details?.traceId;
    state = {
      input,
      reference,
      traceId,
      evalError: `Error when running inference. Details: ${e?.message ?? e}`,
    };
  }
  return gatherEvalInput({ runner, actionRef, state });
}

async function gatherEvalInput(params: {
  runner: Runner;
  actionRef: string;
  state: InferenceRunState;
}): Promise<EvalInput> {
  const { runner, actionRef, state } = params;

  const extractors = await getEvalExtractors(actionRef);
  const traceId = state.traceId;
  if (!traceId) {
    logger.warn('No traceId available...');
    return {
      ...state,
      error: state.evalError,
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

  const isModelAction = actionRef.startsWith('/model');
  // Always use original input for models.
  const input = isModelAction ? state.input : extractors.input(trace);

  const nestedSpan = stackTraceSpans(trace);
  if (!nestedSpan) {
    return {
      testCaseId: randomUUID(),
      input,
      error: `Unable to extract any spans from trace ${traceId}`,
      reference: state.reference,
      traceIds: [traceId],
    };
  }

  if (nestedSpan.attributes['genkit:state'] === 'error') {
    return {
      testCaseId: randomUUID(),
      input,
      error:
        getSpanErrorMessage(nestedSpan) ?? `Unknown error in trace${traceId}`,
      reference: state.reference,
      traceIds: [traceId],
    };
  }

  const output = extractors.output(trace);
  const context = extractors.context(trace);

  return {
    // TODO Replace this with unified trace class
    testCaseId: randomUUID(),
    input,
    output,
    context: JSON.parse(context) as string[],
    reference: state.reference,
    traceIds: [traceId],
  };
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

function getModelInput(data: any, modelConfig: any): GenerateRequest {
  let message: MessageData;
  if (typeof data === 'string') {
    message = {
      role: 'user',
      content: [
        {
          text: data,
        },
      ],
    } as MessageData;
  } else {
    const maybeMessage = MessageSchema.safeParse(data);
    if (maybeMessage.success) {
      message = maybeMessage.data;
    } else {
      throw new Error(
        `Unable to parse model input as MessageSchema as input. Details: ${maybeMessage.error}`
      );
    }
  }
  return {
    messages: message ? [message] : [],
    config: modelConfig,
  };
}
