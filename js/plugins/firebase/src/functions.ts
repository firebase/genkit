import {
  OperationSchema,
  StreamingCallback,
  getLocation,
} from '@google-genkit/common';
import {
  Flow,
  FlowInvokeEnvelopeMessage,
  FlowWrapper,
  StepsFunction,
  flow,
} from '@google-genkit/flow';
import { getFunctions } from 'firebase-admin/functions';
import { logger } from 'firebase-functions/v2';
import {
  HttpsFunction,
  HttpsOptions,
  onRequest,
} from 'firebase-functions/v2/https';
import {
  TaskQueueFunction,
  TaskQueueOptions,
  onTaskDispatched,
} from 'firebase-functions/v2/tasks';
import { GoogleAuth } from 'google-auth-library';
import * as z from 'zod';

type FunctionFlow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
> = HttpsFunction & FlowWrapper<I, O, S>;

interface FunctionFlowConfig<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
> {
  name: string;
  input: I;
  output: O;
  streamType?: S;
  httpsOptions?: HttpsOptions;
}

interface ScheduledFlowConfig<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
> {
  name: string;
  input: I;
  output: O;
  streamType?: S;
  experimentalTaskQueueOptions?: TaskQueueOptions;
}

const streamDelimiter = '\n';

/**
 * Creates a flow backed by Cloud Functions for Firebase gen2 HTTPS function.
 */
export function onFlow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
>(
  config: FunctionFlowConfig<I, O, S>,
  steps: StepsFunction<I, O, S>
): FunctionFlow<I, O, S> {
  const f = flow(
    {
      ...config,
      invoker: async (flow, data, streamingCallback) => {
        const responseJson = await callHttpsFunction(
          flow.name,
          getLocation() || 'us-central1',
          data,
          streamingCallback
        );
        return OperationSchema.parse(JSON.parse(responseJson));
      },
    },
    steps
  );

  const wrapped = wrapHttpsFlow(f, config);

  const funcFlow = wrapped as FunctionFlow<I, O, S>;
  funcFlow.flow = f;

  return funcFlow;
}

/**
 * Creates a scheduled flow backed by Cloud Functions for Firebase gen2 Cloud Task triggered function.
 * This feature is EXPERIMENTAL -- APIs will change or may get removed completely.
 * For testing and feedback only.
 */
export function onScheduledFlow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
>(
  config: ScheduledFlowConfig<I, O, S>,
  steps: StepsFunction<I, O, S>
): FunctionFlow<I, O, S> {
  const f = flow(
    {
      ...config,
      invoker: async (flow, data, streamingCallback) => {
        const responseJson = await callHttpsFunction(
          flow.name,
          getLocation() || 'us-central1',
          data,
          streamingCallback
        );
        return OperationSchema.parse(JSON.parse(responseJson));
      },
      experimentalDurable: true,
      experimentalScheduler: async (flow, msg, delaySeconds) => {
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

function wrapHttpsFlow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
>(flow: Flow<I, O, S>, config: FunctionFlowConfig<I, O, S>): HttpsFunction {
  return onRequest(
    {
      ...config.httpsOptions,
      memory: config.httpsOptions?.memory || '512MiB',
    },
    flow.expressHandler
  );
}

function wrapScheduledFlow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
>(flow: Flow<I, O, S>, config: ScheduledFlowConfig<I, O, S>): HttpsFunction {
  const tq = onTaskDispatched<FlowInvokeEnvelopeMessage>(
    {
      ...config.experimentalTaskQueueOptions,
      memory: config.experimentalTaskQueueOptions?.memory || '512MiB',
      retryConfig: config.experimentalTaskQueueOptions?.retryConfig || {
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

// cached `GoogleAuth` client.
let auth: GoogleAuth;
function getAuthClient() {
  // Lazy load GoogleAuth client.
  if (!auth) {
    auth = new GoogleAuth();
  }
  return auth;
}

const functionUrlCache = {} as Record<string, string>;

async function getFunctionUrl(name, location) {
  if (functionUrlCache[name]) {
    return functionUrlCache[name];
  }
  const auth = getAuthClient();
  const projectId = await auth.getProjectId();
  const url =
    'https://cloudfunctions.googleapis.com/v2beta/' +
    `projects/${projectId}/locations/${location}/functions/${name}`;

  const client = await auth.getClient();
  const res = (await client.request({ url })) as any;
  const uri = res.data?.serviceConfig?.uri;
  if (!uri) {
    throw new Error(`Unable to retrieve uri for function at ${url}`);
  }
  functionUrlCache[name] = uri;
  return uri;
}

async function callHttpsFunction(
  functionName: string,
  location: string,
  data: any,
  streamingCallback?: StreamingCallback<any>
) {
  const auth = getAuthClient();
  var funcUrl = await getFunctionUrl(functionName, location);
  if (!funcUrl) {
    throw new Error(`Unable to retrieve uri for function at ${functionName}`);
  }
  const tokenClient = await auth.getIdTokenClient(funcUrl);
  const token = await tokenClient.idTokenProvider.fetchIdToken(funcUrl);

  if (streamingCallback) {
    funcUrl += '?stream=true';
  }

  const res = await fetch(funcUrl, {
    method: 'POST',
    body: JSON.stringify(data),
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });

  if (streamingCallback) {
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    var buffer = '';
    while (true) {
      const result = await reader.read();
      const decodedValue = decoder.decode(result.value);
      if (decodedValue) {
        buffer += decodedValue;
      }
      // If buffer includes the delimiter that means we are still recieving chunks.
      while (buffer.includes(streamDelimiter)) {
        streamingCallback(
          JSON.parse(buffer.substring(0, buffer.indexOf(streamDelimiter)))
        );
        buffer = buffer.substring(
          buffer.indexOf(streamDelimiter) + streamDelimiter.length
        );
      }
      if (result.done) {
        return buffer;
      }
    }
  }
  const responseText = await res.text();
  return responseText;
}

/**
 * Extracts error message from the given error object, or if input is not an error then just turn the error into a string.
 */
export function getErrorMessage(e: any): string {
  if (e instanceof Error) {
    return e.message;
  }
  return `${e}`;
}

/**
 * Extracts stack trace from the given error object, or if input is not an error then returns undefined.
 */
export function getErrorStack(e: any): string | undefined {
  if (e instanceof Error) {
    return e.stack;
  }
  return undefined;
}
