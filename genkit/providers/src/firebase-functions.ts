import { OperationSchema } from '@google-genkit/common';
import { FlowWrapper } from '@google-genkit/flow';
import { flow, Flow, FlowInvokeEnvelopeMessage, FlowInvokeEnvelopeMessageSchema } from '@google-genkit/flow';
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

type FunctionFlow<I extends z.ZodTypeAny, O extends z.ZodTypeAny> = HttpsFunction & FlowWrapper<I, O>;

interface FunctionFlowConfig<I extends z.ZodTypeAny, O extends z.ZodTypeAny> {
  name: string;
  input: I;
  output: O;
  options?: TaskQueueOptions,
}

export function onFlow<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  config: FunctionFlowConfig<I, O>,
  steps: (input: z.infer<I>) => Promise<z.infer<O>>
): FunctionFlow<I, O> {
  const f = flow({
    ...config,
    dispatcher: {
      async deliver(flow, data) {
        // TODO: unhardcode the location!
        const responseJson = await callHttpsFunction(flow.name, 'us-central1', data)
        return OperationSchema.parse(JSON.parse(responseJson));
      },
      async schedule(flow, msg, delaySeconds) {
        await enqueueCloudTask(flow.name, msg, delaySeconds);
      },
    }
  }, steps);

  const tq = tqWrapper(f, config)

  const funcFlow = tq as FunctionFlow<I, O>
  funcFlow.flow = f;

  return funcFlow;
}

function tqWrapper<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  flow: Flow<I, O>,
  config: FunctionFlowConfig<I, O>
): HttpsFunction {
  const tq = onTaskDispatched<FlowInvokeEnvelopeMessage>(
    {
      ...config.options,
      memory: config.options?.memory || '512MiB',
      retryConfig: config.options?.retryConfig || {
        maxAttempts: 2,
        minBackoffSeconds: 10,
      },
    },
    () => { } // never called, everything handled in createControlAPI.
  );
  return createControlAPI(flow, tq);
}

function createControlAPI(
  flow: Flow<any, any>,
  tq: TaskQueueFunction<FlowInvokeEnvelopeMessage>
) {
  const interceptor = async (req: Request, res: Response) => {
    var data = req.body;
    // Task queue will wrap body in a "data" object, unwrap it.
    if (req.body.data) {
      data = req.body.data;
    }
    const envMsg = FlowInvokeEnvelopeMessageSchema.parse(data);
    try {
      const state = await flow.runEnvelope(envMsg);
      res.status(200).send(state.operation).end();
    } catch (e) {
      res.status(500).send(e).end();
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
  logger.debug(`dispatchCloudTask targetUri for flow ${flowName} with delay ${scheduleDelaySeconds}`);
  await queue.enqueue(payload, {
    scheduleDelaySeconds,
    dispatchDeadlineSeconds: scheduleDelaySeconds,
    uri: targetUri,
    headers: {
      'Content-Type': 'application/json',
    }
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

const functionUrlCache = {} as Record<string, string>

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
  const res = await client.request({ url }) as any;
  const uri = res.data?.serviceConfig?.uri;
  if (!uri) {
    throw new Error(`Unable to retrieve uri for function at ${url}`);
  }
  functionUrlCache[name] = uri;
  return uri;
}


async function callHttpsFunction(functionName, location, data) {
  const auth = getAuthClient();
  const funcUrl = await getFunctionUrl(functionName, location);
  if (!funcUrl) {
    throw new Error(`Unable to retrieve uri for function at ${functionName}`);
  }
  const tokenClient = await auth.getIdTokenClient(funcUrl);
  const token = await tokenClient.idTokenProvider.fetchIdToken(funcUrl);

  const res = await fetch(
    funcUrl,
    {
      method: 'POST',
      body: JSON.stringify(data),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      }
    });
  const responseText = await res.text();
  logger.debug("res", responseText)
  return responseText
}
