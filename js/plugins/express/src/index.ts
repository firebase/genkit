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

import bodyParser from 'body-parser';
import cors, { type CorsOptions } from 'cors';
import express from 'express';
import { type Action, type ActionContext, type Flow, type z } from 'genkit';
import {
  getCallableJSON,
  getHttpStatus,
  type ContextProvider,
  type RequestData,
} from 'genkit/context';
import { logger } from 'genkit/logging';
import type { Server } from 'http';

const streamDelimiter = '\n\n';

/**
 * Exposes provided flow or an action as express handler.
 */
export function expressHandler<
  C extends ActionContext = ActionContext,
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  action: Action<I, O, S>,
  opts?: {
    contextProvider?: ContextProvider<C, I>;
  }
): express.RequestHandler {
  return async (
    request: express.Request,
    response: express.Response
  ): Promise<void> => {
    const { stream } = request.query;
    if (!request.body) {
      const errMsg =
        `Error: request.body is undefined. ` +
        `Possible reasons: missing 'content-type: application/json' in request ` +
        `headers or misconfigured JSON middleware ('app.use(express.json()')? `;
      logger.error(errMsg);
      response
        .status(400)
        .json({ message: errMsg, status: 'INVALID ARGUMENT' })
        .end();
      return;
    }

    const input = request.body.data as z.infer<I>;
    let context: Record<string, any>;

    try {
      context =
        (await opts?.contextProvider?.({
          method: request.method as RequestData['method'],
          headers: Object.fromEntries(
            Object.entries(request.headers).map(([key, value]) => [
              key.toLowerCase(),
              Array.isArray(value) ? value.join(' ') : String(value),
            ])
          ),
          input,
        })) || {};
    } catch (e: any) {
      logger.error(
        `Auth policy failed with error: ${(e as Error).message}\n${(e as Error).stack}`
      );
      response.status(getHttpStatus(e)).json(getCallableJSON(e)).end();
      return;
    }

    const abortController = new AbortController();
    request.on('close', () => {
      abortController.abort();
    });
    // when/if using timeout middleware, it will emit 'timeout' event.
    request.on('timeout', () => {
      abortController.abort();
    });

    if (request.get('Accept') === 'text/event-stream' || stream === 'true') {
      response.writeHead(200, {
        'Content-Type': 'text/plain',
        'Transfer-Encoding': 'chunked',
      });
      try {
        const onChunk = (chunk: z.infer<S>) => {
          response.write(
            'data: ' + JSON.stringify({ message: chunk }) + streamDelimiter
          );
        };
        const result = await action.run(input, {
          onChunk,
          context,
          abortSignal: abortController.signal,
        });
        response.write(
          'data: ' + JSON.stringify({ result: result.result }) + streamDelimiter
        );
        response.end();
      } catch (e) {
        logger.error(
          `Streaming request failed with error: ${(e as Error).message}\n${(e as Error).stack}`
        );
        response.write(
          `error: ${JSON.stringify({ error: getCallableJSON(e) })}${streamDelimiter}`
        );
        response.end();
      }
    } else {
      try {
        const result = await action.run(input, {
          context,
          abortSignal: abortController.signal,
        });
        response.setHeader('x-genkit-trace-id', result.telemetry.traceId);
        response.setHeader('x-genkit-span-id', result.telemetry.spanId);
        // Responses for non-streaming flows are passed back with the flow result stored in a field called "result."
        response
          .status(200)
          .json({
            result: result.result,
          })
          .end();
      } catch (e) {
        // Errors for non-streaming flows are passed back as standard API errors.
        logger.error(
          `Non-streaming request failed with error: ${(e as Error).message}\n${(e as Error).stack}`
        );
        response.status(getHttpStatus(e)).json(getCallableJSON(e)).end();
      }
    }
  };
}

/**
 * A wrapper object containing a flow with its associated auth policy.
 */
export type FlowWithContextProvider<
  C extends ActionContext = ActionContext,
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> = {
  flow: Flow<I, O, S>;
  context: ContextProvider<C, I>;
};

/**
 * Adds an auth policy to the flow.
 */
export function withContextProvider<
  C extends ActionContext = ActionContext,
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  flow: Flow<I, O, S>,
  context: ContextProvider<C, I>
): FlowWithContextProvider<C, I, O, S> {
  return {
    flow,
    context,
  };
}

/**
 * Options to configure the flow server.
 */
export interface FlowServerOptions {
  /** List of flows to expose via the flow server. */
  flows: (Flow<any, any, any> | FlowWithContextProvider<any, any, any>)[];
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
 * Starts an express server with the provided flows and options.
 */
export function startFlowServer(options: FlowServerOptions): FlowServer {
  const server = new FlowServer(options);
  server.start();
  return server;
}

/**
 * Flow server exposes registered flows as HTTP endpoints.
 *
 * This is for use in production environments.
 *
 * @hidden
 */
export class FlowServer {
  /** List of all running servers needed to be cleaned up on process exit. */
  private static RUNNING_SERVERS: FlowServer[] = [];

  /** Options for the flow server configured by the developer. */
  private options: FlowServerOptions;
  /** Port the server is actually running on. This may differ from `options.port` if the original was occupied. Null is server is not running. */
  private port: number | null = null;
  /** Express server instance. Null if server is not running. */
  private server: Server | null = null;

  constructor(options: FlowServerOptions) {
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

    logger.debug('Running flow server with flow paths:');
    const pathPrefix = this.options.pathPrefix ?? '';
    this.options.flows?.forEach((flow) => {
      if ('context' in flow) {
        const flowPath = `/${pathPrefix}${flow.flow.__action.name}`;
        logger.debug(` - ${flowPath}`);
        server.post(
          flowPath,
          expressHandler(flow.flow, { contextProvider: flow.context })
        );
      } else {
        const flowPath = `/${pathPrefix}${flow.__action.name}`;
        logger.debug(` - ${flowPath}`);
        server.post(flowPath, expressHandler(flow));
      }
    });
    this.port =
      this.options?.port ||
      (process.env.PORT ? Number.parseInt(process.env.PORT) : 0) ||
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
