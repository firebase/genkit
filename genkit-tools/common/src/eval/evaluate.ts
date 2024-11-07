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
import { EvalInferenceInput, getDatasetStore, getEvalStore } from '.';
import { RuntimeManager } from '../manager/manager';
import {
  Action,
  CandidateData,
  EvalInferenceInputSchema,
  EvalInput,
  EvalKeyAugments,
  EvalRun,
  EvalRunKey,
  FlowActionInputSchema,
  GenerateRequest,
  GenerateRequestSchema,
  GenerateResponseSchema,
  MessageData,
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

interface InferenceRunState {
  testCaseId: string;
  input: any;
  reference?: any;
  traceId?: string;
  response?: any;
  evalError?: string;
}

interface TestCase {
  testCaseId: string;
  input: any;
  reference?: any;
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
  const datasetMetadatas = await datasetStore.listDatasets();
  const targetDatasetMetadata = datasetMetadatas.find(
    (d) => d.datasetId === datasetId
  );
  const datasetVersion = targetDatasetMetadata?.version;

  logger.info('Running inference...');
  const evalDataset = await runInference({
    manager,
    actionRef,
    evalFlowInput: EvalInferenceInputSchema.parse({ samples: dataset }),
    auth: request.options?.auth,
    actionConfig: request.options?.actionConfig,
  });
  const evaluatorActions = await getMatchingEvaluatorActions(
    manager,
    evaluators
  );

  const evalRun = await runEvaluation({
    manager,
    evaluatorActions,
    evalDataset,
    augments: { actionRef, datasetId, datasetVersion },
  });
  return evalRun.key;
}

/** Handles the Inference part of Inference-Evaluation cycle */
export async function runInference(params: {
  manager: RuntimeManager;
  actionRef: string;
  evalFlowInput: EvalInferenceInput;
  auth?: string;
  actionConfig?: any;
}): Promise<EvalInput[]> {
  const { manager, actionRef, evalFlowInput, auth, actionConfig } = params;
  if (!isSupportedActionRef(actionRef)) {
    throw new Error('Inference is only supported on flows and models');
  }

  const evalDataset: EvalInput[] = await bulkRunAction({
    manager,
    actionRef,
    evalFlowInput,
    auth,
    actionConfig,
  });
  return evalDataset;
}

/** Handles the Evaluation part of Inference-Evaluation cycle */
export async function runEvaluation(params: {
  manager: RuntimeManager;
  evaluatorActions: Action[];
  evalDataset: EvalInput[];
  augments?: EvalKeyAugments;
}): Promise<EvalRun> {
  const { manager, evaluatorActions, evalDataset, augments } = params;
  const evalRunId = randomUUID();
  const scores: Record<string, any> = {};
  logger.info('Running evaluation...');
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
      evalRunId,
      createdAt: new Date().toISOString(),
      ...augments,
    },
    results: scoredResults,
    metricsMetadata: metadata,
  };

  logger.info('Finished evaluation, writing key...');
  const evalStore = getEvalStore();
  await evalStore.save(evalRun);
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
    evaluators.includes(action.key)
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
  evalFlowInput: EvalInferenceInput;
  auth?: string;
  actionConfig?: any;
}): Promise<EvalInput[]> {
  const { manager, actionRef, evalFlowInput, auth, actionConfig } = params;
  const isModelAction = actionRef.startsWith('/model');
  let testCases: TestCase[] = Array.isArray(evalFlowInput)
    ? (evalFlowInput as any[]).map((i) => ({
        input: i,
        testCaseId: generateTestCaseId(),
      }))
    : evalFlowInput.samples.map((c) => ({
        input: c.input,
        reference: c.reference,
        testCaseId: c.testCaseId ?? generateTestCaseId(),
      }));

  let states: InferenceRunState[] = [];
  let evalInputs: EvalInput[] = [];
  for (const testCase of testCases) {
    logger.info(`Running inference '${actionRef}' ...`);
    if (isModelAction) {
      states.push(
        await runModelAction({
          manager,
          actionRef,
          testCase,
          modelConfig: actionConfig,
        })
      );
    } else {
      states.push(
        await runFlowAction({
          manager,
          actionRef,
          testCase,
          auth,
        })
      );
    }
  }

  logger.info(`Gathering evalInputs...`);
  for (const state of states) {
    evalInputs.push(await gatherEvalInput({ manager, actionRef, state }));
  }
  return evalInputs;
}

async function runFlowAction(params: {
  manager: RuntimeManager;
  actionRef: string;
  testCase: TestCase;
  auth?: any;
}): Promise<InferenceRunState> {
  const { manager, actionRef, testCase, auth } = { ...params };
  let state: InferenceRunState;
  try {
    const flowInput = FlowActionInputSchema.parse({
      start: {
        input: testCase.input,
      },
      auth: auth ? JSON.parse(auth) : undefined,
    });
    const runActionResponse = await manager.runAction({
      key: actionRef,
      input: flowInput,
    });
    state = {
      ...testCase,
      traceId: runActionResponse.telemetry?.traceId,
      response: runActionResponse.result,
    };
  } catch (e: any) {
    const traceId = e?.data?.details?.traceId;
    state = {
      ...testCase,
      traceId,
      evalError: `Error when running inference. Details: ${e?.message ?? e}`,
    };
  }
  return state;
}

async function runModelAction(params: {
  manager: RuntimeManager;
  actionRef: string;
  testCase: TestCase;
  modelConfig?: any;
}): Promise<InferenceRunState> {
  const { manager, actionRef, modelConfig, testCase } = { ...params };
  let state: InferenceRunState;
  try {
    const modelInput = getModelInput(testCase.input, modelConfig);
    const runActionResponse = await manager.runAction({
      key: actionRef,
      input: modelInput,
    });
    state = {
      ...testCase,
      traceId: runActionResponse.telemetry?.traceId,
      response: runActionResponse.result,
    };
  } catch (e: any) {
    const traceId = e?.data?.details?.traceId;
    state = {
      ...testCase,
      traceId,
      evalError: `Error when running inference. Details: ${e?.message ?? e}`,
    };
  }
  return state;
}

async function gatherEvalInput(params: {
  manager: RuntimeManager;
  actionRef: string;
  state: InferenceRunState;
}): Promise<EvalInput> {
  const { manager, actionRef, state } = params;

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

  const trace = await manager.getTrace({
    traceId,
  });

  const isModelAction = actionRef.startsWith('/model');
  // Always use original input for models.
  const input = isModelAction ? state.input : extractors.input(trace);

  const nestedSpan = stackTraceSpans(trace);
  if (!nestedSpan) {
    return {
      testCaseId: state.testCaseId,
      input,
      error: `Unable to extract any spans from trace ${traceId}`,
      reference: state.reference,
      traceIds: [traceId],
    };
  }

  if (nestedSpan.attributes['genkit:state'] === 'error') {
    return {
      testCaseId: state.testCaseId,
      input,
      error:
        getSpanErrorMessage(nestedSpan) ?? `Unknown error in trace ${traceId}`,
      reference: state.reference,
      traceIds: [traceId],
    };
  }

  const output = extractors.output(trace);
  const context = extractors.context(trace);
  const error = isModelAction ? getErrorFromModelResponse(output) : undefined;

  return {
    // TODO Replace this with unified trace class
    testCaseId: state.testCaseId,
    input,
    output,
    error,
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

function getErrorFromModelResponse(output: string): string | undefined {
  const obj = JSON.parse(output);
  const response = GenerateResponseSchema.parse(obj);

  if (!response || !response.candidates || response.candidates.length === 0) {
    return `No response was extracted from the output. '${output}'`;
  }

  // We currently only support the first candidate
  const candidate = response.candidates[0] as CandidateData;
  if (candidate.finishReason === 'blocked') {
    return candidate.finishMessage || `Generation was blocked by the model.`;
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
    return {
      messages: message ? [message] : [],
      config: modelConfig,
    };
  } else {
    const maybeRequest = GenerateRequestSchema.safeParse(data);
    if (maybeRequest.success) {
      return maybeRequest.data;
    } else {
      throw new Error(
        `Unable to parse model input as MessageSchema as input. Details: ${maybeRequest.error}`
      );
    }
  }
}
