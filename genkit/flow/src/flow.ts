import {
  Action,
  action,
  asyncSleep,
  FlowError,
  FlowState,
  FlowStateSchema,
  FlowStateStore,
  Operation
} from '@google-genkit/common';
import { config as globalConfig } from '@google-genkit/common/config';
import * as registry from '@google-genkit/common/registry';
import { newTrace, setCustomMetadataAttribute, SPAN_TYPE_ATTR } from '@google-genkit/common/tracing';
import { logger } from 'firebase-functions/v1';
import * as z from 'zod';
import zodToJsonSchema from 'zod-to-json-schema';
import { Context } from './context';
import { FlowExecutionError, FlowNotFoundError, FlowStillRunningError, getErrorMessage, getErrorStack, InterruptError } from './errors';
import {
  Dispatcher,
  FlowInvokeEnvelopeMessage,
  FlowInvokeEnvelopeMessageSchema,
  RetryConfig,
} from './types';
import { generateFlowId, metadataPrefix, runWithActiveContext } from './utils';

/**
 * Step configuration for retries, etc.
 */
export interface RunStepConfig {
  name: string;
  retryConfig?: RetryConfig;
}

/**
 * Defines the flow.
 */
export function flow<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  config: {
    name: string;
    input: I;
    output: O;
    dispatcher?: Dispatcher<I, O>,
  },
  steps: (input: z.infer<I>) => Promise<z.infer<O>>
): Flow<I, O> {
  const f = new Flow({
    name: config.name,
    input: config.input,
    output: config.output,
    stateStore: globalConfig.getFlowStateStore(),
    dispatcher: config.dispatcher || {
      async deliver(flow, msg) {
        const state = await flow.runEnvelope(msg);
        return state.operation;
      },
      async schedule(flow, msg, delay = 0) {
        setTimeout(() => flow.runEnvelope(msg), delay * 1000)
      },
    }
  }, steps)
  registry.registerAction('flow', config.name, wrapAsAction(f));
  return f;
}

export interface FlowWrapper<I extends z.ZodTypeAny, O extends z.ZodTypeAny> {
  flow: Flow<I, O>;
}

export class Flow<I extends z.ZodTypeAny, O extends z.ZodTypeAny> {
  readonly name: string;
  readonly input: I;
  readonly output: O;
  readonly stateStore: FlowStateStore;
  readonly dispatcher: Dispatcher<I, O>;

  constructor(config: {
    name: string,
    input: I,
    output: O,
    stateStore: FlowStateStore,
    dispatcher: Dispatcher<I, O>,
  }, private steps: StepsFunction<I, O>
  ) {
    this.name = config.name;
    this.input = config.input;
    this.output = config.output;
    this.stateStore = config.stateStore;
    this.dispatcher = config.dispatcher;
  }

  /**
   * Executes the flow with the input in the envelope format.
   */
  async runEnvelope(req: FlowInvokeEnvelopeMessage): Promise<FlowState> {
    console.log("runEnvelope", req)
    if (req.start) {
      // First time, create new state.
      const flowId = generateFlowId();
      const state = createNewState(flowId, this.name, req.start.input);
      const ctx = new Context(flowId, state, this.stateStore);
      try {
        await this.executeSteps(ctx, this.steps, "start");
      } finally {
        await this.stateStore.save(flowId, state);
      }
      return state;
    }
    if (req.schedule) {
      // First time, create new state.
      const flowId = generateFlowId();
      const state = createNewState(flowId, this.name, req.schedule.input);
      try {
        await this.stateStore.save(flowId, state);
        await this.dispatcher.schedule(this, { runScheduled: { flowId } } as FlowInvokeEnvelopeMessage, req.schedule.delay);
      } catch (e) {
        state.operation.done = true;
        state.operation.result = {
          error: getErrorMessage(e),
          stacktrace: getErrorStack(e)
        }
        await this.stateStore.save(flowId, state);
      }
      return state;
    }
    if (req.state) {
      const flowId = req.state.flowId;
      const state = await this.stateStore.load(flowId);
      if (state === undefined) {
        throw new Error(`Unable to find flow state for ${flowId}`);
      }
      return state;
    }
    if (req.runScheduled) {
      const flowId = req.runScheduled.flowId;
      const state = await this.stateStore.load(flowId);
      if (state === undefined) {
        throw new Error(`Unable to find flow state for ${flowId}`);
      }
      const ctx = new Context(flowId, state, this.stateStore);
      try {
        await this.executeSteps(ctx, this.steps, "runScheduled");
      } finally {
        await ctx.saveState();
      }
      return state;
    }
    if (req.resume) {
      const flowId = req.resume.flowId;
      const state = await this.stateStore.load(flowId);
      if (state === undefined) {
        throw new Error(`Unable to find flow state for ${flowId}`);
      }
      if (!state.blockedOnStep) {
        throw new Error(
          "Unable to resume flow that's currently not interrupted"
        );
      }
      const ctx = new Context(flowId, state, this.stateStore);
      try {
        await this.executeSteps(ctx, this.steps, "resume");
      } finally {
        await ctx.saveState();
      }
      return state;
    }
    // TODO: add retry

    throw new Error("Unexpected envelope message case, must set one of: " +
      "start, schedule, runScheduled, resume, retry, state")
  }

  // TODO: refactor me... this is a mess!
  private async executeSteps(
    ctx: Context,
    handler: StepsFunction<I, O>,
    dispatchType: string
  ) {
    await runWithActiveContext(ctx, async () => {
      let traceContext;
      if (ctx.state.traceContext) {
        traceContext = JSON.parse(ctx.state.traceContext);
      }
      let errored = false;
      const output = await newTrace(
        {
          name: ctx.flowId,
          labels: {
            [SPAN_TYPE_ATTR]: 'flow',
          },
          links: [{ context: traceContext }],
        },
        async (metadata, rootSpan) => {
          ctx.state.executions.push({
            startTime: Date.now(),
            traceIds: [],
          });

          setCustomMetadataAttribute(metadataPrefix('id'), ctx.flowId);
          ctx
            .getCurrentExecution()
            .traceIds.push(rootSpan.spanContext().traceId);
          // Save the trace in the state so that we can tie subsequent invocation together.
          if (!traceContext) {
            ctx.state.traceContext = JSON.stringify(rootSpan.spanContext());
          }
          setCustomMetadataAttribute(
            metadataPrefix('dispatchType'),
            dispatchType
          );
          try {
            const input = this.input
              ? this.input.parse(ctx.state.input)
              : ctx.state.input;
            metadata.input = input;
            const output = await handler(input);
            metadata.output = output;
            metadata.state = 'success';
            setCustomMetadataAttribute(metadataPrefix('state'), 'done');
            return output;
          } catch (e) {
            if (e instanceof InterruptError) {
              setCustomMetadataAttribute(
                metadataPrefix('state'),
                'interrupted'
              );
            } else {
              metadata.state = 'error';
              setCustomMetadataAttribute(metadataPrefix('state'), 'error');
              ctx.state.operation.done = true;
              ctx.state.operation.result = {
                error: getErrorMessage(e),
                stacktrace: getErrorStack(e),
              } as FlowError;
            }
            errored = true;
          }
        }
      );
      if (!errored) {
        // flow done, set response.
        ctx.state.operation.done = true;
        ctx.state.operation.result = { response: output };
      }
    });
  }
}

/**
 * Runs the flow locally. If the flow does not get interrupted may return a completed (done=true) operation.
 */
export async function runFlow<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(flow: Flow<I, O> | FlowWrapper<I, O>, payload: z.infer<I>): Promise<Operation> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  const state = await flow.dispatcher.deliver(flow, {
    start: {
      input: flow.input.parse(payload),
    }
  });
  return state;
}

/**
 * Schedules a flow run. This is always return an operation that's not completed (done=false).
 */
export async function scheduleFlow<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(flow: Flow<I, O> | FlowWrapper<I, O>, payload: z.infer<I>, delaySeconds?: number): Promise<Operation> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  const state = await flow.dispatcher.deliver(flow, {
    schedule: {
      input: flow.input.parse(payload),
      delay: delaySeconds,
    }
  });
  return state;
}


/**
 * Resumes an interrupted flow.
 */
export async function resumeFlow<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(flow: Flow<I, O> | FlowWrapper<I, O>, flowId: string, payload: any) {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  await flow.dispatcher.deliver(flow, {
    resume: {
      flowId,
      payload,
    },
  });
}

/**
 * Returns an operation representing current state of the flow.
 */
export async function getFlowState<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(flow: Flow<I, O> | FlowWrapper<I, O>, flowId: string): Promise<Operation> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  const state = await flow.stateStore.load(flowId);
  if (!state) {
    throw new FlowNotFoundError(`flow state ${flowId} not found`);
  }
  return state.operation;
}

function parseOutput<O extends z.ZodTypeAny>(flowId: string, state: Operation): z.infer<O> {
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
export async function waitFlowToComplete<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(flow: Flow<I, O> | FlowWrapper<I, O>, flowId: string): Promise<z.infer<O>> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  let state: Operation | undefined = undefined;
  try {
    state = await getFlowState(flow, flowId);
  } catch (e) {
    logger.error(e);
    // TODO: add timeout
    if (!(e instanceof FlowNotFoundError)) {
      throw e;
    }
  }
  if (state && state.done) {
    return parseOutput(flowId, state);
  } else {
    await asyncSleep(1000);
    return await waitFlowToComplete(flow, flowId);
  }
}

function createNewState(flowId: string, name: string, input: unknown): FlowState {
  return {
    flowId: flowId,
    name: name,
    startTime: Date.now(),
    input: input,
    cache: {},
    eventsTriggered: {},
    blockedOnStep: null,
    executions: [],
    operation: {
      name: flowId,
      done: false,
    },
  };
}

type StepsFunction<I extends z.ZodTypeAny, O extends z.ZodTypeAny> = (
  input: z.infer<I>
) => Promise<z.infer<O>>;


function wrapAsAction<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  flow: Flow<I, O>
): Action<typeof FlowInvokeEnvelopeMessageSchema, typeof FlowStateSchema> {
  return action(
    {
      name: flow.name,
      input: FlowInvokeEnvelopeMessageSchema,
      output: FlowStateSchema,
      metadata: {
        inputSchema: zodToJsonSchema(flow.input),
        outputSchema: zodToJsonSchema(flow.output),
      }
    },
    async (envelope) => {
      return await flow.runEnvelope(envelope);
    }
  );
}
