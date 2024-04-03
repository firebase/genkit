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

import { OperationSchema } from '@genkit-ai/core';
import {
  Flow,
  FlowInvokeEnvelopeMessage,
  StepsFunction,
} from '@genkit-ai/flow';
import { durableFlow } from '@genkit-ai/flow/experimental';
import { getFunctions } from 'firebase-admin/functions';
import { logger } from 'firebase-functions/v2';
import { HttpsFunction } from 'firebase-functions/v2/https';
import {
  TaskQueueFunction,
  TaskQueueOptions,
  onTaskDispatched,
} from 'firebase-functions/v2/tasks';
import * as z from 'zod';
import { FunctionFlow } from './functions.js';
import { callHttpsFunction, getFunctionUrl, getLocation } from './helpers.js';

interface ScheduledFlowConfig<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> {
  name: string;
  inputSchema?: I;
  outputSchema?: O;
  streamSchema?: S;
  taskQueueOptions?: TaskQueueOptions;
}

/**
 * Creates a scheduled flow backed by Cloud Functions for Firebase gen2 Cloud Task triggered function.
 * This feature is EXPERIMENTAL -- APIs will change or may get removed completely.
 * For testing and feedback only.
 */
export function onScheduledFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  config: ScheduledFlowConfig<I, O, S>,
  steps: StepsFunction<I, O, S>
): FunctionFlow<I, O, S> {
  const f = durableFlow(
    {
      ...config,
      invoker: async (flow, data, streamingCallback) => {
        const responseJson = await callHttpsFunction(
          flow.name,
          await getLocation(),
          data,
          streamingCallback
        );
        return OperationSchema.parse(JSON.parse(responseJson));
      },
      scheduler: async (flow, msg, delaySeconds) => {
        await enqueueCloudTask(flow.name, msg, delaySeconds);
      },
    },
    steps
  );

  const wrapped = wrapScheduledFlow(f, config);

  const funcFlow = wrapped as FunctionFlow<I, O, S>;
  funcFlow.flow = f;

  return funcFlow;
}

function wrapScheduledFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(flow: Flow<I, O, S>, config: ScheduledFlowConfig<I, O, S>): HttpsFunction {
  const tq = onTaskDispatched<FlowInvokeEnvelopeMessage>(
    {
      ...config.taskQueueOptions,
      memory: config.taskQueueOptions?.memory || '512MiB',
      retryConfig: config.taskQueueOptions?.retryConfig || {
        maxAttempts: 2,
        minBackoffSeconds: 10,
      },
    },
    () => {} // never called, everything handled in createControlAPI.
  );
  return createControlAPI(flow, tq);
}

function createControlAPI(
  flow: Flow<any, any, any>,
  tq: TaskQueueFunction<FlowInvokeEnvelopeMessage>
) {
  const interceptor = flow.expressHandler as any;
  interceptor.__endpoint = tq.__endpoint;
  if (tq.hasOwnProperty('__requiredAPIs')) {
    interceptor.__requiredAPIs = tq['__requiredAPIs'];
  }
  return interceptor;
}

/**
 * Sends the flow invocation envelope to the flow via a task queue.
 */
async function enqueueCloudTask(
  flowName: string,
  payload: FlowInvokeEnvelopeMessage,
  scheduleDelaySeconds?
) {
  const queue = getFunctions().taskQueue(flowName);
  // TODO: set the right location
  const targetUri = await getFunctionUrl(flowName, 'us-central1');
  logger.debug(
    `dispatchCloudTask targetUri for flow ${flowName} with delay ${scheduleDelaySeconds}`
  );
  await queue.enqueue(payload, {
    scheduleDelaySeconds,
    dispatchDeadlineSeconds: scheduleDelaySeconds,
    uri: targetUri,
    headers: {
      'Content-Type': 'application/json',
    },
  });
}
