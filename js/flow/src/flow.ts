import {
  Action,
  action,
  FlowError,
  FlowState,
  FlowStateSchema,
  FlowStateStore,
  getStreamingCallback,
  Operation,
  StreamingCallback,
} from '@google-genkit/common';
import { config as globalConfig, isDevEnv } from '@google-genkit/common/config';
import logging from '@google-genkit/common/logging';
import * as registry from '@google-genkit/common/registry';
import {
  newTrace,
  setCustomMetadataAttribute,
  setCustomMetadataAttributes,
  SPAN_TYPE_ATTR,
} from '@google-genkit/common/tracing';
import * as bodyParser from 'body-parser';
import { default as cors, CorsOptions } from 'cors';
import express from 'express';
import * as z from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';
import { Context } from './context';
import {
  FlowExecutionError,
  FlowStillRunningError,
  getErrorMessage,
  getErrorStack,
  InterruptError,
} from './errors.js';
import {
  FlowInvokeEnvelopeMessage,
  FlowInvokeEnvelopeMessageSchema,
  Invoker,
  RetryConfig,
  Scheduler,
} from './types.js';
import {
  generateFlowId,
  metadataPrefix,
  runWithActiveContext,
} from './utils.js';

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
    invoker?: Invoker<I, O, S>;
    experimentalDurable?: boolean;
    experimentalScheduler?: Scheduler<I, O, S>;
  },
  steps: StepsFunction<I, O, S>
): Flow<I, O, S> {
  const f = new Flow(
    {
      name: config.name,
      input: config.input,
      output: config.output,
      experimentalDurable: !!config.experimentalDurable,
      stateStore: globalConfig.getFlowStateStore(),
      // We always use local dispatcher in dev mode or when one is not provided.
      invoker: async (flow, msg, streamingCallback) => {
        if (!isDevEnv() && config.invoker) {
          return config.invoker(flow, msg, streamingCallback);
        }
        const state = await flow.runEnvelope(msg, streamingCallback);
        return state.operation;
      },
      scheduler: async (flow, msg, delay = 0) => {
        if (!config.experimentalDurable) {
          throw new Error(
            'This flow is not durable, cannot use scheduling features.'
          );
        }
        if (!isDevEnv() && config.experimentalScheduler) {
          return config.experimentalScheduler(flow, msg, delay);
        }
        setTimeout(() => flow.runEnvelope(msg), delay * 1000);
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
  readonly invoker: Invoker<I, O, S>;
  readonly scheduler: Scheduler<I, O, S>;
  readonly experimentalDurable: boolean;

  constructor(
    config: {
      name: string;
      input: I;
      output: O;
      stateStore: Promise<FlowStateStore>;
      invoker: Invoker<I, O, S>;
      scheduler: Scheduler<I, O, S>;
      experimentalDurable: boolean;
    },
    private steps: StepsFunction<I, O, S>
  ) {
    this.name = config.name;
    this.input = config.input;
    this.output = config.output;
    this.stateStore = config.stateStore;
    this.invoker = config.invoker;
    this.scheduler = config.scheduler;
    this.experimentalDurable = config.experimentalDurable;
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
        if (isDevEnv() || this.experimentalDurable) {
          await ctx.saveState();
        }
      }
      return state;
    }
    if (req.schedule) {
      if (!this.experimentalDurable) {
        throw new Error('Cannot schedule a non-durable flow');
      }
      // First time, create new state.
      const flowId = generateFlowId();
      const state = createNewState(flowId, this.name, req.schedule.input);
      try {
        await (await this.stateStore).save(flowId, state);
        await this.scheduler(
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
      if (!this.experimentalDurable) {
        throw new Error('Cannot state check a non-durable flow');
      }
      const flowId = req.state.flowId;
      const state = await (await this.stateStore).load(flowId);
      if (state === undefined) {
        throw new Error(`Unable to find flow state for ${flowId}`);
      }
      return state;
    }
    if (req.runScheduled) {
      if (!this.experimentalDurable) {
        throw new Error('Cannot run scheduled non-durable flow');
      }
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
      if (!this.experimentalDurable) {
        throw new Error('Cannot resume a non-durable flow');
      }
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
      let ctxLinks = traceContext ? [{ context: traceContext }] : [];
      let errored = false;
      const output = await newTrace(
        {
          name: ctx.flowId,
          labels: {
            [SPAN_TYPE_ATTR]: 'flow',
          },
          links: ctxLinks,
        },
        async (metadata, rootSpan) => {
          ctx.state.executions.push({
            startTime: Date.now(),
            traceIds: [],
          });
          setCustomMetadataAttribute(
            metadataPrefix(`execution`),
            (ctx.state.executions.length - 1).toString()
          );
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
            metadata.output = JSON.stringify(output);
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
): Promise<z.infer<O>> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  const state = await flow.invoker(flow, {
    start: {
      input: payload ? flow.input.parse(payload) : undefined,
    },
  });
  if (!state.done) {
    throw new FlowStillRunningError(
      `flow ${state.name} did not finish execution`
    );
  }
  if (state.result?.error) {
    throw new FlowExecutionError(
      state.name,
      state.result?.error,
      state.result?.stacktrace
    );
  }
  return state.result?.response;
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

  const operationPromise = flow.invoker(
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
        experimentalDurable: !!flow.experimentalDurable,
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
