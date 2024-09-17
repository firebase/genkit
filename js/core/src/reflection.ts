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

import express, { NextFunction, Request, Response } from 'express';
import { Server } from 'http';
import z from 'zod';
import { Status, StatusCodes, runWithStreamingCallback } from './action.js';
import { logger } from './logging.js';
import { Registry, runWithRegistry } from './registry.js';
import { toJsonSchema } from './schema.js';
import {
  flushTracing,
  newTrace,
  setCustomMetadataAttribute,
} from './tracing.js';

// TODO: Move this to common location for schemas.
export const RunActionResponseSchema = z.object({
  result: z.unknown().optional(),
  error: z.unknown().optional(),
  telemetry: z
    .object({
      traceId: z.string().optional(),
    })
    .optional(),
});
export type RunActionResponse = z.infer<typeof RunActionResponseSchema>;

export interface ReflectionServerOptions {
  /** Port to run the server on. Actual port may be different if chosen port is occupied. Defaults to 3100. */
  port?: number;
  /** Body size limit for the server. Defaults to `30mb`. */
  bodyLimit?: string;
  /** Configured environments. Defaults to `dev`. */
  configuredEnvs?: string[];
}

/**
 * Reflection server exposes an API for inspecting and interacting with Genkit in development.
 *
 * This is for use in development environments.
 */
export class ReflectionServer {
  /** List of all running servers needed to be cleaned up on process exit. */
  private static RUNNING_SERVERS: ReflectionServer[] = [];

  /** Registry instance to be used for API calls. */
  private registry: Registry;
  /** Options for the reflection server. */
  private options: ReflectionServerOptions;
  /** Port the server is actually running on. This may differ from `options.port` if the original was occupied. Null if server is not running. */
  private port: number | null = null;
  /** Express server instance. Null if server is not running. */
  private server: Server | null = null;

  constructor(registry: Registry, options?: ReflectionServerOptions) {
    this.registry = registry;
    this.options = {
      port: 3100,
      bodyLimit: '30mb',
      configuredEnvs: ['dev'],
      ...options,
    };
  }

  /**
   * Finds a free port to run the server on based on the original chosen port and environment.
   */
  async findPort(): Promise<number> {
    const chosenPort = this.options.port!;
    const freePort = await getPort({
      port: makeRange(chosenPort, chosenPort + 100),
    });
    if (freePort !== chosenPort) {
      logger.warn(
        `Port ${chosenPort} is already in use, using next available port ${freePort} instead.`
      );
    }
    return freePort;
  }

  /**
   * Starts the server.
   *
   * The server will be registered to be shut down on process exit.
   */
  async start() {
    const server = express();

    server.use(express.json({ limit: this.options.bodyLimit }));
    server.use((req: Request, res: Response, next: NextFunction) => {
      runWithRegistry(this.registry, async () => {
        try {
          next();
        } catch (err) {
          next(err);
        }
      });
    });

    server.get('/api/__health', async (_, response) => {
      await this.registry.listActions();
      response.status(200).send('OK');
    });

    server.get('/api/__quitquitquit', async (_, response) => {
      logger.debug('Received quitquitquit');
      response.status(200).send('OK');
      await this.stop();
    });

    server.get('/api/actions', async (_, response, next) => {
      logger.debug('Fetching actions.');
      try {
        const actions = await this.registry.listActions();
        const convertedActions = {};
        Object.keys(actions).forEach((key) => {
          const action = actions[key].__action;
          convertedActions[key] = {
            key,
            name: action.name,
            description: action.description,
            metadata: action.metadata,
          };
          if (action.inputSchema || action.inputJsonSchema) {
            convertedActions[key].inputSchema = toJsonSchema({
              schema: action.inputSchema,
              jsonSchema: action.inputJsonSchema,
            });
          }
          if (action.outputSchema || action.outputJsonSchema) {
            convertedActions[key].outputSchema = toJsonSchema({
              schema: action.outputSchema,
              jsonSchema: action.outputJsonSchema,
            });
          }
        });
        response.send(convertedActions);
      } catch (err) {
        const { message, stack } = err as Error;
        next({ message, stack });
      }
    });

    server.post('/api/runAction', async (request, response, next) => {
      const { key, input } = request.body;
      const { stream } = request.query;
      logger.debug(`Running action \`${key}\` with stream=${stream}...`);
      let traceId;
      try {
        const action = await this.registry.lookupAction(key);
        if (!action) {
          response.status(404).send(`action ${key} not found`);
          return;
        }
        if (stream === 'true') {
          const result = await newTrace(
            { name: 'dev-run-action-wrapper' },
            async (_, span) => {
              setCustomMetadataAttribute('genkit-dev-internal', 'true');
              traceId = span.spanContext().traceId;
              return await runWithStreamingCallback(
                (chunk) => {
                  response.write(JSON.stringify(chunk) + '\n');
                },
                async () => await action(input)
              );
            }
          );
          await flushTracing();
          response.write(
            JSON.stringify({
              result,
              telemetry: traceId
                ? {
                    traceId,
                  }
                : undefined,
            } as RunActionResponse)
          );
          response.end();
        } else {
          const result = await newTrace(
            { name: 'dev-run-action-wrapper' },
            async (_, span) => {
              setCustomMetadataAttribute('genkit-dev-internal', 'true');
              traceId = span.spanContext().traceId;
              return await action(input);
            }
          );
          response.send({
            result,
            telemetry: traceId
              ? {
                  traceId,
                }
              : undefined,
          } as RunActionResponse);
        }
      } catch (err) {
        const { message, stack } = err as Error;
        next({ message, stack, traceId });
      }
    });

    server.get('/api/envs', async (_, response) => {
      response.json(this.options.configuredEnvs);
    });

    server.get('/api/envs/:env/traces/:traceId', async (request, response) => {
      const { env, traceId } = request.params;
      logger.debug(`Fetching trace \`${traceId}\` for env \`${env}\`.`);
      const tracestore = await this.registry.lookupTraceStore(env);
      if (!tracestore) {
        return response.status(500).send({
          code: StatusCodes.FAILED_PRECONDITION,
          message: `${env} trace store not found`,
        });
      }
      try {
        response.json(await tracestore?.load(traceId));
      } catch (err) {
        const error = err as Error;
        const { message, stack } = error;
        const errorResponse: Status = {
          code: StatusCodes.INTERNAL,
          message,
          details: {
            stack,
          },
        };
        return response.status(500).json(errorResponse);
      }
    });

    server.get('/api/envs/:env/traces', async (request, response, next) => {
      const { env } = request.params;
      const { limit, continuationToken } = request.query;
      logger.debug(`Fetching traces for env \`${env}\`.`);
      const tracestore = await this.registry.lookupTraceStore(env);
      if (!tracestore) {
        return response.status(500).send({
          code: StatusCodes.FAILED_PRECONDITION,
          message: `${env} trace store not found`,
        });
      }
      try {
        response.json(
          await tracestore.list({
            limit: limit ? parseInt(limit.toString()) : undefined,
            continuationToken: continuationToken
              ? continuationToken.toString()
              : undefined,
          })
        );
      } catch (err) {
        const { message, stack } = err as Error;
        next({ message, stack });
      }
    });

    server.use((err, req, res, next) => {
      logger.error(err.stack);
      const error = err as Error;
      const { message, stack } = error;
      const errorResponse: Status = {
        code: StatusCodes.INTERNAL,
        message,
        details: {
          stack,
        },
      };
      if (err.traceId) {
        errorResponse.details.traceId = err.traceId;
      }
      res.status(500).json(errorResponse);
    });

    this.port = await this.findPort();
    this.server = server.listen(this.port, () => {
      logger.info(`Reflection server running on http://localhost:${this.port}`);
      ReflectionServer.RUNNING_SERVERS.push(this);
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
            `Error shutting down reflection server on port ${this.port}: ${err}`
          );
          reject(err);
        }
        const index = ReflectionServer.RUNNING_SERVERS.indexOf(this);
        if (index > -1) {
          ReflectionServer.RUNNING_SERVERS.splice(index, 1);
        }
        this.port = null;
        this.server = null;
        logger.info(
          `Reflection server on port ${this.port} has successfully shut down.`
        );
        resolve();
      });
    });
  }

  /**
   * Stops all running reflection servers.
   */
  static async stopAll() {
    await Promise.all(
      ReflectionServer.RUNNING_SERVERS.map((server) => server.stop())
    );
  }
}

// TODO: Verify that this works.
if (typeof module !== 'undefined' && 'hot' in module) {
  (module as any).hot.accept();
  (module as any).hot.dispose(async () => {
    logger.debug('Cleaning up reflection server(s) before module reload...');
    await ReflectionServer.stopAll();
  });
}
