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
import express, { RequestHandler } from 'express';
import { Action, Flow, runWithStreamingCallback, z } from 'genkit';
import { logger } from 'genkit/logging';
import { Server } from 'http';
import { getErrorMessage, getErrorStack } from './utils';

const streamDelimiter = '\n\n';

/**
 * Auth policy context is an object passed to the auth policy providing details necessary for auth.
 */
export interface AuthPolicyContext<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> {
  action?: Action<I, O, S>;
  input: z.infer<I>;
  auth?: Record<string, any>;
  request: RequestWithAuth;
}

/**
 * Flow Auth policy. Consumes the authorization context of the flow and
 * performs checks before the flow runs. If this throws, the flow will not
 * be executed.
 */
export interface AuthPolicy<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> {
  (ctx: AuthPolicyContext<I, O, S>): void | Promise<void>;
}

/**
 * For express-based flows, req.auth should contain the value to bepassed into
 * the flow context.
 */
export interface RequestWithAuth extends express.Request {
  auth?: Record<string, any>;
}

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
    authPolicy?: AuthPolicy<I, O, S>;
  }
): express.RequestHandler {
  return async (
    request: RequestWithAuth,
    response: express.Response
  ): Promise<void> => {
    const { stream } = request.query;
    let input = request.body.data;
    const auth = request.auth;

    try {
      await opts?.authPolicy?.({
        action,
        auth,
        input,
        request,
      });
    } catch (e: any) {
      logger.debug(e);
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
              context: { auth },
            })
        );
        response.write(
          'data: ' + JSON.stringify({ result: result.result }) + streamDelimiter
        );
        response.end();
      } catch (e) {
        logger.error(e);
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
        const result = await action.run(input, { context: { auth } });
        response.setHeader('x-genkit-trace-id', result.telemetry.traceId);
        response.setHeader('x-genkit-span-id', result.telemetry.spanId);
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
  authProvider: RequestHandler;
  authPolicy: AuthPolicy;
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
  authProvider: RequestHandler,
  authPolicy: AuthPolicy
): FlowWithAuthPolicy<I, O, S> {
  return {
    flow,
    authProvider,
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
      if ((flow as FlowWithAuthPolicy).authPolicy) {
        const flowWithPolicy = flow as FlowWithAuthPolicy;
        const flowPath = `/${pathPrefix}${flowWithPolicy.flow.__action.name}`;
        logger.debug(` - ${flowPath}`);
        server.post(
          flowPath,
          flowWithPolicy.authProvider,
          expressHandler(flowWithPolicy.flow, {
            authPolicy: flowWithPolicy.authPolicy,
          })
        );
      } else {
        const resolvedFlow = flow as Flow;
        const flowPath = `/${pathPrefix}${resolvedFlow.__action.name}`;
        logger.debug(` - ${flowPath}`);
        server.post(flowPath, expressHandler(resolvedFlow));
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
