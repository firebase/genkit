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

import {
  Action,
  defineAction,
  getStreamingCallback,
  StreamingCallback,
  z,
} from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import { initializeAllPlugins } from '@genkit-ai/core/registry';
import { toJsonSchema } from '@genkit-ai/core/schema';
import {
  newTrace,
  setCustomMetadataAttribute,
  setCustomMetadataAttributes,
  SPAN_TYPE_ATTR,
} from '@genkit-ai/core/tracing';
import { SpanStatusCode } from '@opentelemetry/api';
import * as bodyParser from 'body-parser';
import { default as cors, CorsOptions } from 'cors';
import express from 'express';
import { getErrorMessage, getErrorStack } from './errors.js';
import { FlowActionInputSchema } from './types.js';
import { metadataPrefix, runWithAuthContext } from './utils.js';

const streamDelimiter = '\n';

const CREATED_FLOWS = 'genkit__CREATED_FLOWS';

function createdFlows(): Flow<any, any, any>[] {
  if (global[CREATED_FLOWS] === undefined) {
    global[CREATED_FLOWS] = [];
  }
  return global[CREATED_FLOWS];
}

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
 * Base configuration for a flow.
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

interface FlowResult<O> {
  result: O;
  traceId: string;
}

/**
 * Defines a non-streaming flow.
 */
export function defineFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
>(config: FlowConfig<I, O>, fn: FlowFn<I, O, z.ZodVoid>): CallableFlow<I, O> {
  const f = new Flow<I, O, z.ZodVoid>(config, fn);
  createdFlows().push(f);
  wrapAsAction(f);
  const callableFlow: CallableFlow<I, O> = async (input, opts) => {
    return f.run(input, opts);
  };
  callableFlow.flow = f;
  return callableFlow;
}

/**
 * Defines a streaming flow.
 */
export function defineStreamingFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  config: StreamingFlowConfig<I, O, S>,
  steps: FlowFn<I, O, S>
): StreamableFlow<I, O, S> {
  const f = new Flow(config, steps);
  createdFlows().push(f);
  wrapAsAction(f);
  const streamableFlow: StreamableFlow<I, O, S> = (input, opts) => {
    return f.stream(input, opts);
  };
  streamableFlow.flow = f;
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

  constructor(
    config: {
      name: string;
      inputSchema?: I;
      outputSchema?: O;
      streamSchema?: S;
      authPolicy?: FlowAuthPolicy<I>;
      middleware?: express.RequestHandler[];
    },
    private flowFn: FlowFn<I, O, S>
  ) {
    this.name = config.name;
    this.inputSchema = config.inputSchema;
    this.outputSchema = config.outputSchema;
    this.streamSchema = config.streamSchema;
    this.authPolicy = config.authPolicy;
    this.middleware = config.middleware;
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
    req: __RequestWithAuth,
    res: express.Response
  ): Promise<void> {
    const { stream } = req.query;
    const auth = req.auth;

    let input = req.body.data;

    try {
      await this.authPolicy?.(auth, input);
    } catch (e: any) {
      const respBody = {
        error: {
          status: 'PERMISSION_DENIED',
          message: e.message || 'Permission denied to resource',
        },
      };
      res.status(403).send(respBody).end();
      return;
    }

    if (stream === 'true') {
      res.writeHead(200, {
        'Content-Type': 'text/plain',
        'Transfer-Encoding': 'chunked',
      });
      try {
        const result = await this.invoke(input, {
          streamingCallback: ((chunk: z.infer<S>) => {
            res.write(JSON.stringify(chunk) + streamDelimiter);
          }) as S extends z.ZodVoid ? undefined : StreamingCallback<z.infer<S>>,
          auth,
        });
        res.write({
          result: result.result, // Need more results!!!!
        });
        res.end();
      } catch (e) {
        res.write({
          error: {
            status: 'INTERNAL',
            message: getErrorMessage(e),
            details: getErrorStack(e),
          },
        });
        res.end();
      }
    } else {
      try {
        const result = await this.invoke(input, { auth });
        // Responses for non-streaming flows are passed back with the flow result stored in a field called "result."
        res
          .status(200)
          .send({
            result: result.result,
          })
          .end();
      } catch (e) {
        // Errors for non-streaming flows are passed back as standard API errors.
        res
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

function wrapAsAction<
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

/**
 * Start the flows server.
 */
export function startFlowsServer(params?: {
  flows?: Flow<any, any, any>[];
  port?: number;
  cors?: CorsOptions;
  pathPrefix?: string;
  jsonParserOptions?: bodyParser.OptionsJson;
}) {
  const port =
    params?.port || (process.env.PORT ? parseInt(process.env.PORT) : 0) || 3400;
  const pathPrefix = params?.pathPrefix ?? '';
  const app = express();
  app.use(bodyParser.json(params?.jsonParserOptions));
  app.use(cors(params?.cors));

  const flows = params?.flows || createdFlows();
  logger.info(`Starting flows server on port ${port}`);
  flows.forEach((f) => {
    const flowPath = `/${pathPrefix}${f.name}`;
    logger.info(` - ${flowPath}`);
    // Add middlware
    f.middleware?.forEach((m) => {
      app.post(flowPath, m);
    });
    app.post(flowPath, f.expressHandler);
  });

  app.listen(port, () => {
    console.log(`Flows server listening on port ${port}`);
  });
}
