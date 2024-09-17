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

/**
 * Reflection server exposes an API for inspecting and interacting with Genkit in development.
 */
export class ReflectionServer {
  /** List of all running servers needed to be cleaned up on process exit. */
  private static runningServers: ReflectionServer[] = [];

  /** Registry instance to be used for API calls. */
  private registry: Registry;
  /** Express server instance. May be null if the server is not running. */
  private server: Server | null = null;
  /** Body size limit. */
  private bodyLimit: string;
  /** Configured environments. */
  private configuredEnvs: string[];

  /** Port allocated to the server. */
  port: number;

  constructor(args: {
    /** Registry instance to be used for API calls. */
    registry: Registry;
    /** Port to run the server on. If it's not available, it will be incremented until an available port is found. */
    port?: number;
    /** Body size limit for the server. */
    bodyLimit?: string;
    /** Configured environments. */
    configuredEnvs?: string[];
  }) {
    this.registry = args.registry;
    this.port = args.port || 3100;
    this.bodyLimit = args.bodyLimit || '30mb';
    this.configuredEnvs = args.configuredEnvs || ['dev'];
  }

  /**
   * Starts the reflection server.
   *
   * The server will be registered to be shut down on process exit.
   */
  async start() {
    // TODO: Better way to do this?
    const getPort = await import('get-port').then((module) => module.default);
    const portNumbers = await import('get-port').then(
      (module) => module.portNumbers
    );

    this.port = await getPort({
      port: portNumbers(this.port, this.port + 100),
    });

    const api = express();
    api.use(express.json({ limit: this.bodyLimit }));

    const registryMiddleware = (
      req: Request,
      res: Response,
      next: NextFunction
    ) => {
      runWithRegistry(this.registry, async () => {
        try {
          next();
        } catch (err) {
          next(err);
        }
      });
    };
    api.use(registryMiddleware);

    api.get('/api/__health', async (_, response) => {
      await this.registry.listActions();
      response.status(200).send('OK');
    });

    api.get('/api/__quitquitquit', async (_, response) => {
      logger.debug('Received quitquitquit');
      response.status(200).send('OK');
      await this.stop();
    });

    api.get('/api/actions', async (_, response, next) => {
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

    api.post('/api/runAction', async (request, response, next) => {
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

    api.get('/api/envs', async (_, response) => {
      response.json(this.configuredEnvs);
    });

    api.get('/api/envs/:env/traces/:traceId', async (request, response) => {
      runWithRegistry(this.registry, async () => {
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
    });

    api.get('/api/envs/:env/traces', async (request, response, next) => {
      runWithRegistry(this.registry, async () => {
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
    });

    api.use((err, req, res, next) => {
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

    this.server = api.listen(this.port, () => {
      logger.info(`Reflection API running on http://localhost:${this.port}`);
      ReflectionServer.runningServers.push(this);
    });
  }

  /**
   * Stops the reflection server.
   */
  async stop(): Promise<void> {
    if (this.server) {
      await new Promise<void>((resolve) => {
        this.server!.close(() => {
          logger.info(
            `Reflection API on port ${this.port} has successfully shut down.`
          );
          resolve();
        });
      });
      const index = ReflectionServer.runningServers.indexOf(this);
      if (index > -1) {
        ReflectionServer.runningServers.splice(index, 1);
      }
    }
  }

  /**
   * Stops all running reflection servers.
   */
  static async stopAll() {
    await Promise.all(
      ReflectionServer.runningServers.map((server) => server.stop())
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
