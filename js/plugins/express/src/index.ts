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

import * as bodyParser from 'body-parser';
import cors, { CorsOptions } from 'cors';
import express from 'express';
import { Action, Flow, runWithStreamingCallback, z } from 'genkit';
import * as authPolicy from 'genkit/authPolicy';
import { logger } from 'genkit/logging';
import { Server } from 'http';

const streamDelimiter = '\n\n';

/**
 * Exposes provided flow or an action as express handler.
 */
export function expressHandler<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  action: Action<I, O, S>,
  opts?: {
    authPolicy?: authPolicy.AuthPolicy<I>;
  }
): express.RequestHandler {
  return async (
    request: express.Request,
    response: express.Response
  ): Promise<void> => {
    const { stream } = request.query;
    let input = request.body.data as z.infer<I>;
    let context: Record<string, any>;

    try {
      context =
        (await opts?.authPolicy?.({
          method: request.method as authPolicy.Request['method'],
          headers: Object.fromEntries(
            Object.entries(request.headers).map(([key, value]) => [
              key.toLowerCase(),
              Array.isArray(value) ? value.join(' ') : String(value),
            ])
          ),
          body: input,
        })) || {};
    } catch (e: any) {
      logger.error(
        `Auth policy failed with error: ${(e as Error).message}\n${(e as Error).stack}`
      );
      if (!(e instanceof authPolicy.UserFacingError)) {
        e = new authPolicy.UserFacingError('internal', 'Internal');
      } else {
        response.status(e.httpErrorCode.status).json(e.toJSON()).end();
      }
      return;
    }

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
        const result = await runWithStreamingCallback(
          action.__registry,
          onChunk,
          () =>
            action.run(input, {
              onChunk,
              context,
            })
        );
        response.write(
          'data: ' + JSON.stringify({ result: result.result }) + streamDelimiter
        );
        response.end();
      } catch (e) {
        logger.error(
          `Streaming request failed with error: ${(e as Error).message}\n${(e as Error).stack}`
        );
        if (!(e instanceof authPolicy.UserFacingError)) {
          e = new authPolicy.UserFacingError('internal', 'Internal error');
        }
        response.write(
          `error: ${JSON.stringify({ error: (e as authPolicy.UserFacingError).toJSON() })}${streamDelimiter}`
        );
        response.end();
      }
    } else {
      try {
        const result = await action.run(input, { context });
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
        if (!(e instanceof authPolicy.UserFacingError)) {
          e = new authPolicy.UserFacingError('internal', 'Internal error');
        }
        response
          .status((e as authPolicy.UserFacingError).httpErrorCode.status)
          .json((e as authPolicy.UserFacingError).toJSON())
          .end();
      }
    }
  };
}

/**
 * A wrapper object containing a flow with its associated auth policy.
 */
export type FlowWithAuthPolicy<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> = {
  flow: Flow<I, O, S>;
  authPolicy: authPolicy.AuthPolicy<I>;
};

/**
 * Adds an auth policy to the flow.
 */
export function withAuth<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  flow: Flow<I, O, S>,
  authPolicy: authPolicy.AuthPolicy<I>
): FlowWithAuthPolicy<I, O, S> {
  return {
    flow,
    authPolicy,
  };
}

/**
 * Options to configure the flow server.
 */
export interface FlowServerOptions {
  /** List of flows to expose via the flow server. */
  flows: (Flow<any, any, any> | FlowWithAuthPolicy<any, any, any>)[];
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
      if ('authPolicy' in flow) {
        const flowPath = `/${pathPrefix}${flow.flow.__action.name}`;
        logger.debug(` - ${flowPath}`);
        server.post(
          flowPath,
          expressHandler(flow.flow, {
            authPolicy: flow.authPolicy,
          })
        );
      } else {
        const flowPath = `/${pathPrefix}${flow.__action.name}`;
        logger.debug(` - ${flowPath}`);
        server.post(flowPath, expressHandler(flow));
      }
    });
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
