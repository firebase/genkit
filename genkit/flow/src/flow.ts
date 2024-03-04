import {
  Action,
  action,
  asyncSleep,
  FlowError,
  FlowState,
  FlowStateSchema,
  FlowStateStore,
  Operation,
  StreamingCallback,
} from '@google-genkit/common';
import {
  getCurrentEnv,
  config as globalConfig,
} from '@google-genkit/common/config';
import logging from '@google-genkit/common/logging';
import * as registry from '@google-genkit/common/registry';
import {
  newTrace,
  setCustomMetadataAttribute,
  setCustomMetadataAttributes,
  SPAN_TYPE_ATTR,
} from '@google-genkit/common/tracing';
import * as z from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';
import { Context } from './context.js';
import {
  FlowExecutionError,
  FlowNotFoundError,
  FlowStillRunningError,
  getErrorMessage,
  getErrorStack,
  InterruptError,
} from './errors.js';
import {
  Dispatcher,
  FlowInvokeEnvelopeMessage,
  FlowInvokeEnvelopeMessageSchema,
  RetryConfig,
} from './types.js';
import {
  generateFlowId,
  metadataPrefix,
  runWithActiveContext,
} from './utils.js';
import express from 'express';
import * as bodyParser from 'body-parser';
import { default as cors, CorsOptions } from 'cors';
import { getStreamingCallback } from '@google-genkit/common';

const streamDelimiter = '\n';
const createdFlows = [] as Flow<any, any, any>[];

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
export function flow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
>(
  config: {
    name: string;
    input: I;
    output: O;
    streamType?: S;
    durable?: boolean;
    dispatcher?: Dispatcher<I, O, S>;
  },
  steps: StepsFunction<I, O, S>
): Flow<I, O, S> {
  const f = new Flow(
    {
      name: config.name,
      input: config.input,
      output: config.output,
      durable: !!config.durable,
      stateStore: globalConfig.getFlowStateStore(),
      // We always use local dispatcher in dev mode or when one is not provided.
      dispatcher: (getCurrentEnv() !== 'dev' && config.dispatcher) || {
        async deliver(flow, msg, streamingCallback) {
          const state = await flow.runEnvelope(msg, streamingCallback);
          return state.operation;
        },
        async schedule(flow, msg, delay = 0) {
          if (!config.durable) {
            throw new Error(
              'This flow is not durable, cannot use scheduling features. ' +
                'Set durable to true and follow task queue setup instructions.'
            );
          }
          setTimeout(() => flow.runEnvelope(msg), delay * 1000);
        },
      },
    },
    steps
  );
  createdFlows.push(f);
  registry.registerAction('flow', config.name, wrapAsAction(f));
  return f;
}

export interface FlowWrapper<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
> {
  flow: Flow<I, O, S>;
}

export class Flow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
> {
  readonly name: string;
  readonly input: I;
  readonly output: O;
  readonly stateStore: Promise<FlowStateStore>;
  readonly dispatcher: Dispatcher<I, O, S>;
  readonly durable: boolean;

  constructor(
    config: {
      name: string;
      input: I;
      output: O;
      stateStore: Promise<FlowStateStore>;
      dispatcher: Dispatcher<I, O, S>;
      durable: boolean;
    },
    private steps: StepsFunction<I, O, S>
  ) {
    this.name = config.name;
    this.input = config.input;
    this.output = config.output;
    this.stateStore = config.stateStore;
    this.dispatcher = config.dispatcher;
    this.durable = config.durable;
  }

  /**
   * Executes the flow with the input in the envelope format.
   */
  async runEnvelope(
    req: FlowInvokeEnvelopeMessage,
    streamingCallback?: StreamingCallback<any>
  ): Promise<FlowState> {
    logging.debug(req, 'runEnvelope');
    if (req.start) {
      // First time, create new state.
      const flowId = generateFlowId();
      const state = createNewState(flowId, this.name, req.start.input);
      const ctx = new Context(this, flowId, state);
      try {
        await this.executeSteps(
          ctx,
          this.steps,
          'start',
          streamingCallback,
          req.start.labels
        );
      } finally {
        await (await this.stateStore).save(flowId, state);
      }
      return state;
    }
    if (req.schedule) {
      // First time, create new state.
      const flowId = generateFlowId();
      const state = createNewState(flowId, this.name, req.schedule.input);
      try {
        await (await this.stateStore).save(flowId, state);
        await this.dispatcher.schedule(
          this,
          { runScheduled: { flowId } } as FlowInvokeEnvelopeMessage,
          req.schedule.delay
        );
      } catch (e) {
        state.operation.done = true;
        state.operation.result = {
          error: getErrorMessage(e),
          stacktrace: getErrorStack(e),
        };
        await (await this.stateStore).save(flowId, state);
      }
      return state;
    }
    if (req.state) {
      const flowId = req.state.flowId;
      const state = await (await this.stateStore).load(flowId);
      if (state === undefined) {
        throw new Error(`Unable to find flow state for ${flowId}`);
      }
      return state;
    }
    if (req.runScheduled) {
      const flowId = req.runScheduled.flowId;
      const state = await (await this.stateStore).load(flowId);
      if (state === undefined) {
        throw new Error(`Unable to find flow state for ${flowId}`);
      }
      const ctx = new Context(this, flowId, state);
      try {
        await this.executeSteps(
          ctx,
          this.steps,
          'runScheduled',
          undefined,
          undefined
        );
      } finally {
        await ctx.saveState();
      }
      return state;
    }
    if (req.resume) {
      const flowId = req.resume.flowId;
      const state = await (await this.stateStore).load(flowId);
      if (state === undefined) {
        throw new Error(`Unable to find flow state for ${flowId}`);
      }
      if (!state.blockedOnStep) {
        throw new Error(
          "Unable to resume flow that's currently not interrupted"
        );
      }
      state.eventsTriggered[state.blockedOnStep.name] = req.resume.payload;
      const ctx = new Context(this, flowId, state);
      try {
        await this.executeSteps(
          ctx,
          this.steps,
          'resume',
          undefined,
          undefined
        );
      } finally {
        await ctx.saveState();
      }
      return state;
    }
    // TODO: add retry

    throw new Error(
      'Unexpected envelope message case, must set one of: ' +
        'start, schedule, runScheduled, resume, retry, state'
    );
  }

  // TODO: refactor me... this is a mess!
  private async executeSteps(
    ctx: Context<I, O, S>,
    handler: StepsFunction<I, O, S>,
    dispatchType: string,
    streamingCallback: StreamingCallback<any> | undefined,
    labels: Record<string, string> | undefined
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

          if (labels) {
            Object.keys(labels).forEach((label) => {
              setCustomMetadataAttribute(
                metadataPrefix(`label:${label}`),
                labels[label]
              );
            });
          }

          setCustomMetadataAttributes({
            [metadataPrefix('name')]: this.name,
            [metadataPrefix('id')]: ctx.flowId,
          });
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
            const output = await handler(input, streamingCallback);
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

  get expressHandler(): (req: express.Request, res: express.Response) => any {
    return async (req: express.Request, res: express.Response) => {
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
          const state = await this.runEnvelope(envMsg, (chunk) => {
            res.write(JSON.stringify(chunk) + streamDelimiter);
          });
          res.write(JSON.stringify(state.operation));
          res.end();
        } catch (e) {
          logging.error(e);
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
          const state = await this.runEnvelope(envMsg);
          res.status(200).send(state.operation).end();
        } catch (e) {
          logging.error(e);
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
  }
}

/**
 * Runs the flow. If the flow does not get interrupted may return a completed (done=true) operation.
 */
export async function runFlow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
>(
  flow: Flow<I, O, S> | FlowWrapper<I, O, S>,
  payload?: z.infer<I>
): Promise<Operation> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  const state = await flow.dispatcher.deliver(flow, {
    start: {
      input: payload ? flow.input.parse(payload) : undefined,
    },
  });
  return state;
}

interface StreamingResponse<S extends z.ZodTypeAny> {
  stream(): AsyncGenerator<unknown, Operation, z.infer<S> | undefined>;
  operation(): Promise<Operation>;
}

/**
 * Runs the flow and streams results. If the flow does not get interrupted may return a completed (done=true) operation.
 */
export function streamFlow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
>(
  flow: Flow<I, O, S> | FlowWrapper<I, O, S>,
  payload?: z.infer<I>
): StreamingResponse<S> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }

  var chunkStreamController: ReadableStreamController<z.infer<S>>;
  const chunkStream = new ReadableStream<z.infer<S>>({
    start(controller) {
      chunkStreamController = controller;
    },
    pull() {},
    cancel() {},
  });

  const operationPromise = flow.dispatcher.deliver(
    flow,
    {
      start: {
        input: payload ? flow.input.parse(payload) : undefined,
      },
    },
    (c) => {
      chunkStreamController.enqueue(c);
    }
  );
  operationPromise.then((o) => {
    chunkStreamController.close();
    return o;
  });

  return {
    operation() {
      return operationPromise;
    },
    async *stream() {
      const reader = chunkStream.getReader();
      while (true) {
        const chunk = await reader.read();
        if (chunk.value) {
          yield chunk.value;
        }
        if (chunk.done) {
          break;
        }
      }
      return await operationPromise;
    },
  };
}

/**
 * Schedules a flow run. This is always return an operation that's not completed (done=false).
 */
export async function scheduleFlow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
>(
  flow: Flow<I, O, S> | FlowWrapper<I, O, S>,
  payload: z.infer<I>,
  delaySeconds?: number
): Promise<Operation> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  const state = await flow.dispatcher.deliver(flow, {
    schedule: {
      input: flow.input.parse(payload),
      delay: delaySeconds,
    },
  });
  return state;
}

/**
 * Resumes an interrupted flow.
 */
export async function resumeFlow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
>(
  flow: Flow<I, O, S> | FlowWrapper<I, O, S>,
  flowId: string,
  payload: any
): Promise<Operation> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  return await flow.dispatcher.deliver(flow, {
    resume: {
      flowId,
      payload,
    },
  });
}

/**
 * Returns an operation representing current state of the flow.
 */
export async function getFlowState<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
>(
  flow: Flow<I, O, S> | FlowWrapper<I, O, S>,
  flowId: string
): Promise<Operation> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  const state = await (await flow.stateStore).load(flowId);
  if (!state) {
    throw new FlowNotFoundError(`flow state ${flowId} not found`);
  }
  return state.operation;
}

function parseOutput<O extends z.ZodTypeAny>(
  flowId: string,
  state: Operation
): z.infer<O> {
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
export async function waitFlowToComplete<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
>(
  flow: Flow<I, O, S> | FlowWrapper<I, O, S>,
  flowId: string
): Promise<z.infer<O>> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  let state: Operation | undefined = undefined;
  try {
    state = await getFlowState(flow, flowId);
  } catch (e) {
    logging.error(e);
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

function createNewState(
  flowId: string,
  name: string,
  input: unknown
): FlowState {
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

export type StepsFunction<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
> = (
  input: z.infer<I>,
  streamingCallback: StreamingCallback<z.infer<S>> | undefined
) => Promise<z.infer<O>>;

function wrapAsAction<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny
>(
  flow: Flow<I, O, S>
): Action<typeof FlowInvokeEnvelopeMessageSchema, typeof FlowStateSchema> {
  return action(
    {
      name: flow.name,
      input: FlowInvokeEnvelopeMessageSchema,
      output: FlowStateSchema,
      metadata: {
        inputSchema: zodToJsonSchema(flow.input),
        outputSchema: zodToJsonSchema(flow.output),
      },
    },
    async (envelope) => {
      return await flow.runEnvelope(envelope, getStreamingCallback());
    }
  );
}

export function startFlowsServer(params?: {
  flows?: Flow<any, any, any>[];
  port?: number;
  cors: CorsOptions;
}) {
  const port =
    params?.port || (process.env.PORT ? parseInt(process.env.PORT) : 0) || 5000;
  const app = express();
  app.use(bodyParser.json());
  if (params?.cors) {
    app.use(cors(params.cors));
  }

  const flows = params?.flows || createdFlows;
  logging.info(`Starting flows server on port ${port}`);
  flows.forEach((f) => {
    logging.info(` - /${f.name}`);
    app.post(`/${f.name}`, f.expressHandler);
  });

  app.listen(port, () => {
    console.log(`Flows server listening on port ${port}`);
  });
}
