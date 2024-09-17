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
import express from 'express';
import * as z from 'zod';
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
import {
  getRegistryInstance,
  initializeAllPlugins,
  Registry,
  runWithRegistry,
} from './registry.js';
import { toJsonSchema } from './schema.js';
import {
  newTrace,
  runInNewSpan,
  setCustomMetadataAttribute,
  setCustomMetadataAttributes,
  SPAN_TYPE_ATTR,
} from './tracing.js';

const streamDelimiter = '\n';

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

/**
 * Non-streaming flow that can be called directly like a function.
 */
export interface CallableFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
> {
  (
    input?: z.infer<I>,
    opts?: { withLocalAuthContext?: unknown }
  ): Promise<z.infer<O>>;
  flow: Flow<I, O, z.ZodVoid>;
}

/**
 * Streaming flow that can be called directly like a function.
 */
export interface StreamableFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> {
  (
    input?: z.infer<I>,
    opts?: { withLocalAuthContext?: unknown }
  ): StreamingResponse<O, S>;
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
  stream: AsyncGenerator<unknown, z.infer<O>, z.infer<S> | undefined>;
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
  streamingCallback?: S extends z.ZodVoid
    ? undefined
    : StreamingCallback<z.infer<S>>
) => Promise<z.infer<O>>;

/**
 * Represents the result of a flow execution.
 */
interface FlowResult<O> {
  /** The result of the flow execution. */
  result: O;
  /** The trace ID associated with the flow execution. */
  traceId: string;
}

/**
 * Defines a non-streaming flow. This operates on the currently active registry.
 */
export function defineFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
>(config: FlowConfig<I, O>, fn: FlowFn<I, O, z.ZodVoid>): CallableFlow<I, O> {
  const flow = new Flow<I, O, z.ZodVoid>(config, fn);
  registerFlowAction(flow);
  const registry = getRegistryInstance();
  const callableFlow: CallableFlow<I, O> = async (input, opts) => {
    return runWithRegistry(registry, () => flow.run(input, opts));
  };
  callableFlow.flow = flow;
  return callableFlow;
}

/**
 * Defines a streaming flow. This operates on the currently active registry.
 */
export function defineStreamingFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  config: StreamingFlowConfig<I, O, S>,
  fn: FlowFn<I, O, S>
): StreamableFlow<I, O, S> {
  const flow = new Flow(config, fn);
  registerFlowAction(flow);
  const registry = getRegistryInstance();
  const streamableFlow: StreamableFlow<I, O, S> = (input, opts) => {
    return runWithRegistry(registry, () => flow.stream(input, opts));
  };
  streamableFlow.flow = flow;
  return streamableFlow;
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
      streamingCallback?: S extends z.ZodVoid
        ? undefined
        : StreamingCallback<z.infer<S>>;
      labels?: Record<string, string>;
      auth?: unknown;
    }
  ): Promise<FlowResult<z.infer<O>>> {
    await initializeAllPlugins();
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
                metadataPrefix(`label:${label}`),
                labels[label]
              );
            });
          }

          setCustomMetadataAttributes({
            [metadataPrefix('name')]: this.name,
          });
          try {
            metadata.input = input;
            const output = await this.flowFn(input, opts.streamingCallback);
            metadata.output = JSON.stringify(output);
            setCustomMetadataAttribute(metadataPrefix('state'), 'done');
            return {
              result: output,
              traceId: rootSpan.spanContext().traceId,
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

            setCustomMetadataAttribute(metadataPrefix('state'), 'error');
            throw e;
          }
        }
      )
    );
  }

  /**
   * Runs the flow. This is used when calling a flow from another flow.
   */
  async run(
    payload?: z.infer<I>,
    opts?: { withLocalAuthContext?: unknown }
  ): Promise<z.infer<O>> {
    const input = this.inputSchema ? this.inputSchema.parse(payload) : payload;
    await this.authPolicy?.(opts?.withLocalAuthContext, payload);

    if (this.middleware) {
      logger.warn(
        `Flow (${this.name}) middleware won't run when invoked with runFlow.`
      );
    }

    const result = await this.invoke(input, {
      auth: opts?.withLocalAuthContext,
    });
    return result.result;
  }

  /**
   * Runs the flow and streams results. This is used when calling a flow from another flow.
   */
  stream(
    payload?: z.infer<I>,
    opts?: { withLocalAuthContext?: unknown }
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
      this.authPolicy?.(opts?.withLocalAuthContext, payload) ??
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
    registry: Registry,
    request: __RequestWithAuth,
    response: express.Response
  ): Promise<void> {
    await runWithRegistry(registry, async () => {
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

      if (stream === 'true') {
        response.writeHead(200, {
          'Content-Type': 'text/plain',
          'Transfer-Encoding': 'chunked',
        });
        try {
          const result = await this.invoke(input, {
            streamingCallback: ((chunk: z.infer<S>) => {
              response.write(JSON.stringify(chunk) + streamDelimiter);
            }) as S extends z.ZodVoid
              ? undefined
              : StreamingCallback<z.infer<S>>,
            auth,
          });
          response.write({
            result: result.result, // Need more results!!!!
          });
          response.end();
        } catch (e) {
          response.write({
            error: {
              status: 'INTERNAL',
              message: getErrorMessage(e),
              details: getErrorStack(e),
            },
          });
          response.end();
        }
      } else {
        try {
          const result = await this.invoke(input, { auth });
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
    });
  }
}

/**
 * Registers a flow as an action in the registry.
 */
function registerFlowAction<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(flow: Flow<I, O, S>): Action<typeof FlowActionInputSchema, O> {
  return defineAction(
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
      setCustomMetadataAttribute(metadataPrefix('wrapperAction'), 'true');
      const response = await flow.invoke(envelope.start?.input, {
        streamingCallback: getStreamingCallback() as S extends z.ZodVoid
          ? undefined
          : StreamingCallback<z.infer<S>>,
        auth: envelope.auth,
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

/**
 * Adds flow-specific prefix for OpenTelemetry span attributes.
 */
export function metadataPrefix(name: string) {
  return `flow:${name}`;
}
