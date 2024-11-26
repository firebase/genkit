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

import { SpanStatusCode } from '@opentelemetry/api';
import * as bodyParser from 'body-parser';
import cors, { CorsOptions } from 'cors';
import express from 'express';
import { Server } from 'http';
import { z } from 'zod';
import {
  Action,
  defineAction,
  getStreamingCallback,
  StreamingCallback,
} from './action.js';
import { runWithAuthContext } from './auth.js';
import { getErrorMessage, getErrorStack } from './error.js';
import { FlowActionInputSchema } from './flowTypes.js';
import { logger } from './logging.js';
import { Registry } from './registry.js';
import { toJsonSchema } from './schema.js';
import {
  newTrace,
  runInNewSpan,
  setCustomMetadataAttribute,
  setCustomMetadataAttributes,
  SPAN_TYPE_ATTR,
} from './tracing.js';
import { flowMetadataPrefix } from './utils.js';

const streamDelimiter = '\n\n';

/**
 * Flow Auth policy. Consumes the authorization context of the flow and
 * performs checks before the flow runs. If this throws, the flow will not
 * be executed.
 */
export interface FlowAuthPolicy<I extends z.ZodTypeAny = z.ZodTypeAny> {
  (auth: any | undefined, input: z.infer<I>): void | Promise<void>;
}

/**
 * For express-based flows, req.auth should contain the value to bepassed into
 * the flow context.
 */
export interface __RequestWithAuth extends express.Request {
  auth?: unknown;
}

/**
 * Configuration for a flow.
 */
export interface FlowConfig<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
> {
  /** Name of the flow. */
  name: string;
  /** Schema of the input to the flow. */
  inputSchema?: I;
  /** Schema of the output from the flow. */
  outputSchema?: O;
  /** Auth policy. */
  authPolicy?: FlowAuthPolicy<I>;
  /** Middleware for HTTP requests. Not called for direct invocations. */
  middleware?: express.RequestHandler[];
}

/**
 * Configuration for a streaming flow.
 */
export interface StreamingFlowConfig<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> extends FlowConfig<I, O> {
  /** Schema of the streaming chunks from the flow. */
  streamSchema?: S;
}

export interface FlowCallOptions {
  /** @deprecated use {@link context} instead. */
  withLocalAuthContext?: unknown;
  context?: unknown;
}

/**
 * Non-streaming flow that can be called directly like a function.
 */
export interface CallableFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> {
  (input?: z.infer<I>, opts?: FlowCallOptions): Promise<z.infer<O>>;

  stream(input?: z.infer<I>, opts?: FlowCallOptions): StreamingResponse<O, S>;

  flow: Flow<I, O, z.ZodVoid>;
}

/**
 * Streaming flow that can be called directly like a function.
 * @deprecated use {@link CallableFlow}
 */
export interface StreamableFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> {
  (input?: z.infer<I>, opts?: FlowCallOptions): StreamingResponse<O, S>;
  flow: Flow<I, O, S>;
}

/**
 * Response from a streaming flow.
 */
interface StreamingResponse<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> {
  /** Iterator over the streaming chunks. */
  stream: AsyncGenerator<z.infer<S>>;
  /** Final output of the flow. */
  output: Promise<z.infer<O>>;
}

/**
 * Function to be executed in the flow.
 */
export type FlowFn<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> = (
  /** Input to the flow. */
  input: z.infer<I>,
  /** Callback for streaming functions only. */
  streamingCallback: StreamingCallback<z.infer<S>>
) => Promise<z.infer<O>> | z.infer<O>;

/**
 * Represents the result of a flow execution.
 */
interface FlowResult<O> {
  /** The result of the flow execution. */
  result: O;
  /** The trace ID associated with the flow execution. */
  traceId: string;
  /** The root span ID of the associated trace. */
  spanId: string;
}

export class Flow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> {
  readonly name: string;
  readonly inputSchema?: I;
  readonly outputSchema?: O;
  readonly streamSchema?: S;
  readonly authPolicy?: FlowAuthPolicy<I>;
  readonly middleware?: express.RequestHandler[];
  readonly flowFn: FlowFn<I, O, S>;

  constructor(
    private registry: Registry,
    config: FlowConfig<I, O> | StreamingFlowConfig<I, O, S>,
    flowFn: FlowFn<I, O, S>
  ) {
    this.name = config.name;
    this.inputSchema = config.inputSchema;
    this.outputSchema = config.outputSchema;
    this.streamSchema =
      'streamSchema' in config ? config.streamSchema : undefined;
    this.authPolicy = config.authPolicy;
    this.middleware = config.middleware;
    this.flowFn = flowFn;
  }

  /**
   * Executes the flow with the input directly.
   */
  async invoke(
    input: unknown,
    opts: {
      streamingCallback?: StreamingCallback<z.infer<S>>;
      labels?: Record<string, string>;
      auth?: unknown;
    }
  ): Promise<FlowResult<z.infer<O>>> {
    await this.registry.initializeAllPlugins();
    return await runWithAuthContext(opts.auth, () =>
      newTrace(
        {
          name: this.name,
          labels: {
            [SPAN_TYPE_ATTR]: 'flow',
          },
        },
        async (metadata, rootSpan) => {
          if (opts.labels) {
            const labels = opts.labels;
            Object.keys(opts.labels).forEach((label) => {
              setCustomMetadataAttribute(
                flowMetadataPrefix(`label:${label}`),
                labels[label]
              );
            });
          }

          setCustomMetadataAttributes({
            [flowMetadataPrefix('name')]: this.name,
          });
          try {
            metadata.input = input;
            const output = await this.flowFn(
              input,
              opts.streamingCallback ?? (() => {})
            );
            metadata.output = JSON.stringify(output);
            setCustomMetadataAttribute(flowMetadataPrefix('state'), 'done');
            return {
              result: output,
              traceId: rootSpan.spanContext().traceId,
              spanId: rootSpan.spanContext().spanId,
            };
          } catch (e) {
            metadata.state = 'error';
            rootSpan.setStatus({
              code: SpanStatusCode.ERROR,
              message: getErrorMessage(e),
            });
            if (e instanceof Error) {
              rootSpan.recordException(e);
            }

            setCustomMetadataAttribute(flowMetadataPrefix('state'), 'error');
            throw e;
          }
        }
      )
    );
  }

  /**
   * Runs the flow. This is used when calling a flow from another flow.
   */
  async run(payload?: z.infer<I>, opts?: FlowCallOptions): Promise<z.infer<O>> {
    const input = this.inputSchema ? this.inputSchema.parse(payload) : payload;
    await this.authPolicy?.(opts?.withLocalAuthContext, payload);

    if (this.middleware) {
      logger.warn(
        `Flow (${this.name}) middleware won't run when invoked with runFlow.`
      );
    }

    const result = await this.invoke(input, {
      auth: opts?.context || opts?.withLocalAuthContext,
    });
    return result.result;
  }

  /**
   * Runs the flow and streams results. This is used when calling a flow from another flow.
   */
  stream(
    payload?: z.infer<I>,
    opts?: FlowCallOptions
  ): StreamingResponse<O, S> {
    let chunkStreamController: ReadableStreamController<z.infer<S>>;
    const chunkStream = new ReadableStream<z.infer<S>>({
      start(controller) {
        chunkStreamController = controller;
      },
      pull() {},
      cancel() {},
    });

    const authPromise =
      this.authPolicy?.(opts?.context || opts?.withLocalAuthContext, payload) ??
      Promise.resolve();

    const invocationPromise = authPromise
      .then(() =>
        this.invoke(
          this.inputSchema ? this.inputSchema.parse(payload) : payload,
          {
            streamingCallback: ((chunk: z.infer<S>) => {
              chunkStreamController.enqueue(chunk);
            }) as S extends z.ZodVoid
              ? undefined
              : StreamingCallback<z.infer<S>>,
            auth: opts?.context || opts?.withLocalAuthContext,
          }
        ).then((s) => s.result)
      )
      .finally(() => {
        chunkStreamController.close();
      });

    return {
      output: invocationPromise,
      stream: (async function* () {
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
        return await invocationPromise;
      })(),
    };
  }

  async expressHandler(
    request: __RequestWithAuth,
    response: express.Response
  ): Promise<void> {
    const { stream } = request.query;
    const auth = request.auth;

    let input = request.body.data;

    try {
      await this.authPolicy?.(auth, input);
    } catch (e: any) {
      const respBody = {
        error: {
          status: 'PERMISSION_DENIED',
          message: e.message || 'Permission denied to resource',
        },
      };
      response.status(403).send(respBody).end();
      return;
    }

    if (request.get('Accept') === 'text/event-stream' || stream === 'true') {
      response.writeHead(200, {
        'Content-Type': 'text/plain',
        'Transfer-Encoding': 'chunked',
      });
      try {
        const result = await this.invoke(input, {
          streamingCallback: (chunk: z.infer<S>) => {
            response.write(
              'data: ' + JSON.stringify({ message: chunk }) + streamDelimiter
            );
          },
          auth,
        });
        response.write(
          'data: ' + JSON.stringify({ result: result.result }) + streamDelimiter
        );
        response.end();
      } catch (e) {
        console.log(e);
        response.write(
          'data: ' +
            JSON.stringify({
              error: {
                status: 'INTERNAL',
                message: getErrorMessage(e),
                details: getErrorStack(e),
              },
            }) +
            streamDelimiter
        );
        response.end();
      }
    } else {
      try {
        const result = await this.invoke(input, { auth });
        response.setHeader('x-genkit-trace-id', result.traceId);
        response.setHeader('x-genkit-span-id', result.spanId);
        // Responses for non-streaming flows are passed back with the flow result stored in a field called "result."
        response
          .status(200)
          .send({
            result: result.result,
          })
          .end();
      } catch (e) {
        // Errors for non-streaming flows are passed back as standard API errors.
        response
          .status(500)
          .send({
            error: {
              status: 'INTERNAL',
              message: getErrorMessage(e),
              details: getErrorStack(e),
            },
          })
          .end();
      }
    }
  }
}

/**
 * Options to configure the flow server.
 */
export interface FlowServerOptions {
  /** List of flows to expose via the flow server. */
  flows: (CallableFlow<any, any> | StreamableFlow<any, any>)[];
  /** Port to run the server on. Defaults to env.PORT or 3400. */
  port?: number;
  /** CORS options for the server. */
  cors?: CorsOptions;
  /** HTTP method path prefix for the exposed flows. */
  pathPrefix?: string;
  /** JSON body parser options. */
  jsonParserOptions?: bodyParser.OptionsJson;
}

/**
 * Flow server exposes registered flows as HTTP endpoints.
 *
 * This is for use in production environments.
 */
export class FlowServer {
  /** List of all running servers needed to be cleaned up on process exit. */
  private static RUNNING_SERVERS: FlowServer[] = [];

  /** Registry instance to be used for API calls. */
  private registry: Registry;
  /** Options for the flow server configured by the developer. */
  private options: FlowServerOptions;
  /** Port the server is actually running on. This may differ from `options.port` if the original was occupied. Null is server is not running. */
  private port: number | null = null;
  /** Express server instance. Null if server is not running. */
  private server: Server | null = null;

  constructor(registry: Registry, options: FlowServerOptions) {
    this.registry = registry;
    this.options = {
      ...options,
    };
  }

  /**
   * Starts the server and adds it to the list of running servers to clean up on exit.
   */
  async start() {
    const server = express();

    server.use(bodyParser.json(this.options.jsonParserOptions));
    server.use(cors(this.options.cors));

    if (!!this.options.flows) {
      logger.debug('Running flow server with flow paths:');
      const pathPrefix = this.options.pathPrefix ?? '';
      this.options.flows?.forEach((flow) => {
        const flowPath = `/${pathPrefix}${flow.flow.name}`;
        logger.debug(` - ${flowPath}`);
        flow.flow.middleware?.forEach((middleware) =>
          server.post(flowPath, middleware)
        );
        server.post(flowPath, (req, res) => flow.flow.expressHandler(req, res));
      });
    } else {
      logger.warn('No flows registered in flow server.');
    }
    this.port =
      this.options?.port ||
      (process.env.PORT ? parseInt(process.env.PORT) : 0) ||
      3400;
    this.server = server.listen(this.port, () => {
      logger.debug(`Flow server running on http://localhost:${this.port}`);
      FlowServer.RUNNING_SERVERS.push(this);
    });
  }

  /**
   * Stops the server and removes it from the list of running servers to clean up on exit.
   */
  async stop(): Promise<void> {
    if (!this.server) {
      return;
    }
    return new Promise<void>((resolve, reject) => {
      this.server!.close((err) => {
        if (err) {
          logger.error(
            `Error shutting down flow server on port ${this.port}: ${err}`
          );
          reject(err);
        }
        const index = FlowServer.RUNNING_SERVERS.indexOf(this);
        if (index > -1) {
          FlowServer.RUNNING_SERVERS.splice(index, 1);
        }
        logger.debug(
          `Flow server on port ${this.port} has successfully shut down.`
        );
        this.port = null;
        this.server = null;
        resolve();
      });
    });
  }

  /**
   * Stops all running servers.
   */
  static async stopAll() {
    return Promise.all(
      FlowServer.RUNNING_SERVERS.map((server) => server.stop())
    );
  }
}

/**
 * Defines a non-streaming flow. This operates on the currently active registry.
 */
export function defineFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  config: StreamingFlowConfig<I, O> | string,
  fn: FlowFn<I, O, S>
): CallableFlow<I, O, S> {
  const resolvedConfig: FlowConfig<I, O> =
    typeof config === 'string' ? { name: config } : config;

  const flow = new Flow<I, O, S>(registry, resolvedConfig, fn);
  registerFlowAction(registry, flow);
  const callableFlow = async (
    input: z.infer<I>,
    opts: FlowCallOptions
  ): Promise<z.infer<O>> => {
    return flow.run(input, opts);
  };
  (callableFlow as CallableFlow<I, O, S>).flow = flow;
  (callableFlow as CallableFlow<I, O, S>).stream = (
    input: z.infer<I>,
    opts: FlowCallOptions
  ): StreamingResponse<O, S> => {
    return flow.stream(input, opts);
  };
  return callableFlow as CallableFlow<I, O, S>;
}

/**
 * Defines a streaming flow. This operates on the currently active registry.
 */
export function defineStreamingFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  config: StreamingFlowConfig<I, O, S>,
  fn: FlowFn<I, O, S>
): StreamableFlow<I, O, S> {
  const flow = new Flow(registry, config, fn);
  registerFlowAction(registry, flow);
  const streamableFlow: StreamableFlow<I, O, S> = (input, opts) => {
    return flow.stream(input, opts);
  };
  streamableFlow.flow = flow;
  return streamableFlow;
}

/**
 * Registers a flow as an action in the registry.
 */
function registerFlowAction<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  flow: Flow<I, O, S>
): Action<typeof FlowActionInputSchema, O> {
  return defineAction(
    registry,
    {
      actionType: 'flow',
      name: flow.name,
      inputSchema: FlowActionInputSchema,
      outputSchema: flow.outputSchema,
      metadata: {
        inputSchema: toJsonSchema({ schema: flow.inputSchema }),
        outputSchema: toJsonSchema({ schema: flow.outputSchema }),
        requiresAuth: !!flow.authPolicy,
      },
    },
    async (envelope) => {
      await flow.authPolicy?.(
        envelope.auth,
        envelope.start?.input as I | undefined
      );
      setCustomMetadataAttribute(flowMetadataPrefix('wrapperAction'), 'true');
      const response = await flow.invoke(envelope.start?.input, {
        streamingCallback: getStreamingCallback() as S extends z.ZodVoid
          ? undefined
          : StreamingCallback<z.infer<S>>,
        auth: envelope.auth,
        labels: envelope.start?.labels,
      });
      return response.result;
    }
  );
}

export function run<T>(name: string, func: () => Promise<T>): Promise<T>;
export function run<T>(
  name: string,
  input: any,
  func: (input?: any) => Promise<T>
): Promise<T>;

/**
 * A flow step that executes the provided function. Each run step is recorded separately in the trace.
 */
export function run<T>(
  name: string,
  funcOrInput: () => Promise<T>,
  fn?: (input?: any) => Promise<T>
): Promise<T> {
  const func = arguments.length === 3 ? fn : funcOrInput;
  const input = arguments.length === 3 ? funcOrInput : undefined;
  if (!func) {
    throw new Error('unable to resolve run function');
  }
  return runInNewSpan(
    {
      metadata: { name },
      labels: {
        [SPAN_TYPE_ATTR]: 'flowStep',
      },
    },
    async (meta) => {
      meta.input = input;
      const output = arguments.length === 3 ? await func(input) : await func();
      meta.output = JSON.stringify(output);
      return output;
    }
  );
}

// TODO: Verify that this works.
if (typeof module !== 'undefined' && 'hot' in module) {
  (module as any).hot.accept();
  (module as any).hot.dispose(async () => {
    logger.debug('Cleaning up flow server(s) before module reload...');
    await FlowServer.stopAll();
  });
}
