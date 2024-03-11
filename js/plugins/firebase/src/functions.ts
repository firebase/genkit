import { OperationSchema, getLocation } from '@google-genkit/common';
import { Flow, FlowWrapper, StepsFunction, flow } from '@google-genkit/flow';
import {
  HttpsFunction,
  HttpsOptions,
  onRequest,
} from 'firebase-functions/v2/https';
import * as z from 'zod';
import { callHttpsFunction } from './helpers';

export type FunctionFlow<
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
