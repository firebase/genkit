import { ActionMetadata, asyncSleep } from '@google-genkit/common';
import * as registry from '@google-genkit/common/registry';
import { HttpsFunction } from 'firebase-functions/v2/https';
import { MemoryOption } from 'firebase-functions/v2/options';
import {
  Request as TaskRequest,
  onTaskDispatched,
} from 'firebase-functions/v2/tasks';
import * as z from 'zod';
import { dispatchCloudTask } from './cloudTaskDispatcher';
import { createControlAPI } from './controlApi';
import { FlowRunner } from './runner';
import {
  FlowInvokeEnvelopeMessage,
  FlowInvokeEnvelopeMessageSchema,
  Operation,
  RetryConfig,
} from './types';
import { generateFlowId } from './utils';

type TaskQueueWithMetadata<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny
> = HttpsFunction & { __metadata: ActionMetadata<I, O> } & {
  __flow: FlowRunner<I, O>;
};

/**
 * Step configuration for retries, etc.
 */
export interface RunStepConfig {
  name: string;
  retryConfig?: RetryConfig;
}

export type ConfiguredFlow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny
> = TaskQueueWithMetadata<I, O>;

/**
 * Defines the flow.
 */
export function flow<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  config: {
    name: string;
    input: I;
    output: O;
    // TODO: remove this.
    local?: boolean;
    retryPolicy?: RetryConfig;
    // TODO: add all runtime options, not just memory.
    memory?: MemoryOption;
  },
  steps: (input: z.infer<I>) => Promise<z.infer<O>>
): ConfiguredFlow<I, O> {
  const stateStore = registry.lookup('/flows/stateStore');
  if (!stateStore) {
    throw new Error(
      'State store is not configured/provided. Either pass in a state store instance or, for ' +
        'example, call configureFirestoreStateStore.'
    );
  }
  const fr = new FlowRunner<I, O>({
    name: config.name,
    input: config.input,
    output: config.output,
    stateStore,
    steps,
    dispatcher: {
      async dispatch(flow, msg) {
        // TODO: this doesn't make sense, separate dispatcher configs into separate runners.
        if (config.local) {
          // Local dispatcher
          await flow.run(msg);
        } else {
          // Cloud Task dispatcher
          await dispatchCloudTask(config.name, msg);
        }
      },
    },
  });
  const taskQueue = tqWrapper(fr, config, async (req) => {
    const envMsg = FlowInvokeEnvelopeMessageSchema.parse(req.data);
    await fr.run(envMsg);
  }) as TaskQueueWithMetadata<I, O>;
  taskQueue.__metadata = {
    name: fr.name,
    inputSchema: fr.input,
    outputSchema: fr.output,
  };
  taskQueue.__flow = fr;
  return taskQueue;
}

function tqWrapper<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  fr: FlowRunner<I, O>,
  config: any,
  tqf: (tqReq: TaskRequest) => void
): HttpsFunction {
  const tq = onTaskDispatched<FlowInvokeEnvelopeMessage>(
    {
      memory: config.memory || '512MiB',
      retryConfig: {
        maxAttempts: 2,
        minBackoffSeconds: 10,
      },
    },
    tqf
  );
  return createControlAPI(fr, tq);
}

/**
 * Start the flow asyncronously. Will always return an operation that's not complete.
 * The flow will get executed asyncronously, check flow operation status (e.g. `getFlowState`)
 * to see when it completes.
 */
export async function startFlowAsync<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny
>(flow: ConfiguredFlow<I, O>, payload: z.infer<I>): Promise<Operation> {
  // TODO: this currently does async call by using the dispatcher, which is wrong.
  //       Instead this needs to use the remote control API.
  const flowId = generateFlowId();
  const newState = flow.__flow.createNewState(flowId, {
    flowId,
    input: flow.__metadata.inputSchema?.parse(payload),
  });
  await flow.__flow.stateStore.save(flowId, newState);
  await flow.__flow.dispatcher.dispatch(flow.__flow, { flowId });
  return newState.operation;
}

/**
 * Starts the flow remotely by waits for the flow to execute (or interupt). Will return an operation
 * and the operation may be completed, always check before trying to read the result.
 */
export async function startFlowSync<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
>(flow: ConfiguredFlow<I, O>, payload: z.infer<I>): Promise<Operation> {
  throw new Error('working on it...');
}

/**
 * Runs the flow locally. If the flow does not get interrupted may return a completed (done=true) operation.
 */
export async function runFlow<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  flow: ConfiguredFlow<I, O>,
  payload: z.infer<I>
): Promise<Operation> {
  const flowId = generateFlowId();
  const state = await flow.__flow.run({
    flowId,
    input: flow.__metadata.inputSchema?.parse(payload),
  });
  return state.operation;
}

/**
 * Resumes an interrupted flow.
 */
export async function resumeFlow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny
>(flow: ConfiguredFlow<I, O>, flowId: string, payload: any) {
  await flow.__flow.dispatcher.dispatch(flow.__flow, {
    flowId,
    resume: {
      payload,
    },
  });
}

/**
 * Returns an operation representing current state of the flow.
 */
export async function getFlowState<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny
>(flow: ConfiguredFlow<I, O> | undefined, flowId: string): Promise<Operation> {
  const state = await flow?.__flow.stateStore.load(flowId);
  if (!state) {
    throw new FlowNotFoundError(`flow state ${flowId} not found`);
  }
  return state.operation;
}

/**
 * Retrieves flow state and returns the response. If flow errored then a
 * {@link FlowExecutionError} will be thrown. If flows has not finished execution
 * then {@link FlowStillRunningError} error will be thrown.
 */
export async function getFlowOutput<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny
>(flow: ConfiguredFlow<I, O> | undefined, flowId: string): Promise<z.infer<O>> {
  const state = await getFlowState(flow, flowId);
  if (!state.done) {
    throw new FlowStillRunningError(flowId);
  }
  if (state.result?.error) {
    throw new FlowExecutionError(
      flowId,
      `flow ${flowId} failed: ${state.result.error}`,
      state.result.error,
      state.result.stacktrace
    );
  }
  return state.result?.response;
}

/**
 * A local utility that waits for the flow execution to complete. If flow errored then a
 * {@link FlowExecutionError} will be thrown.
 */
export async function waitForFlowToComplete<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny
>(flow: ConfiguredFlow<I, O>, flowId: string): Promise<z.infer<O>> {
  let state: Operation | undefined = undefined;
  try {
    state = await getFlowState(flow, flowId);
  } catch (e) {
    console.log(e);
    // TODO: add timeout
    if (!(e instanceof FlowNotFoundError)) {
      throw e;
    }
  }
  if (state && state.done) {
    return getFlowOutput(flow, flowId);
  } else {
    await asyncSleep(1000);
    return await waitForFlowToComplete(flow, flowId);
  }
}

/**
 * Exception thrown when flow is not found in the flow state store.
 */
export class FlowNotFoundError extends Error {
  constructor(msg: string) {
    super(msg);
  }
}

/**
 * Exception thrown when flow execution is not completed yet.
 */
export class FlowStillRunningError extends Error {
  constructor(readonly flowId: string) {
    super(
      `flow ${flowId} is not done execution. Consider using waitForFlowToComplete to wait for ` +
        'completion before calling getOutput.'
    );
  }
}

/**
 * Exception thrown when flow execution resulted in an error.
 */
export class FlowExecutionError extends Error {
  constructor(
    readonly flowId: string,
    message: string,
    readonly originalMessage: string,
    readonly originalStacktrace?: any
  ) {
    super(message);
  }
}
