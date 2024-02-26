import {
  Operation,
  StreamingCallback,
  getLocation,
} from '@google-genkit/common';
import { OperationSchema } from '@google-genkit/common';
import { StepsFunction } from '@google-genkit/flow';
import {
  flow,
  Flow,
  FlowInvokeEnvelopeMessage,
  FlowInvokeEnvelopeMessageSchema,
  FlowWrapper,
} from '@google-genkit/flow';
import { Response } from 'express';
import { getFunctions } from 'firebase-admin/functions';
import { logger } from 'firebase-functions/v2';
import { HttpsFunction, Request } from 'firebase-functions/v2/https';
import {
  onTaskDispatched,
  TaskQueueFunction,
  TaskQueueOptions,
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
  options?: TaskQueueOptions;
}

const streamDelimiter = '\n';

/**
 *
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
      dispatcher: {
        async deliver(flow, data, streamingCallback) {
          // TODO: unhardcode the location!
          const responseJson = await callHttpsFunction(
            flow.name,
            getLocation() || 'us-central1',
            data,
            streamingCallback
          );
          return OperationSchema.parse(JSON.parse(responseJson));
        },
        async schedule(flow, msg, delaySeconds) {
          await enqueueCloudTask(flow.name, msg, delaySeconds);
        },
      },
    },
    steps
  );

  const tq = tqWrapper(f, config);

  const funcFlow = tq as FunctionFlow<I, O, S>;
  funcFlow.flow = f;

  return funcFlow;
}

function tqWrapper<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
>(flow: Flow<I, O, S>, config: FunctionFlowConfig<I, O, S>): HttpsFunction {
  const tq = onTaskDispatched<FlowInvokeEnvelopeMessage>(
    {
      ...config.options,
      memory: config.options?.memory || '512MiB',
      retryConfig: config.options?.retryConfig || {
        maxAttempts: 2,
        minBackoffSeconds: 10,
      },
    },
    // eslint-disable-next-line @typescript-eslint/no-empty-function
    () => {} // never called, everything handled in createControlAPI.
  );
  return createControlAPI(flow, tq);
}

function createControlAPI(
  flow: Flow<any, any, any>,
  tq: TaskQueueFunction<FlowInvokeEnvelopeMessage>
) {
  const interceptor = async (req: Request, res: Response) => {
    const { stream } = req.query;
    let data = req.body;
    // Task queue will wrap body in a "data" object, unwrap it.
    if (req.body.data) {
      data = req.body.data;
    }
    const envMsg = FlowInvokeEnvelopeMessageSchema.parse(data);
    if (stream === 'true') {
      res.writeHead(200, {
        'Content-Type': 'text/plain',
        'Transfer-Encoding': 'chunked',
      });
      try {
        const state = await flow.runEnvelope(envMsg, (c) => {
          res.write(JSON.stringify(c) + streamDelimiter);
        });
        res.write(JSON.stringify(state.operation));
        res.end();
      } catch (e) {
        logger.error(e);
        res.write(
          JSON.stringify({
            done: true,
            result: {
              error: getErrorMessage(e),
              stacktrace: getErrorStack(e),
            },
          } as Operation)
        );
        res.end();
      }
    } else {
      try {
        const state = await flow.runEnvelope(envMsg);
        res.status(200).send(state.operation).end();
      } catch (e) {
        logger.error(e);
        res
          .status(500)
          .send({
            done: true,
            result: {
              error: getErrorMessage(e),
              stacktrace: getErrorStack(e),
            },
          } as Operation)
          .end();
      }
    }
  };
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
