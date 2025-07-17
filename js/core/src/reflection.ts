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

import express from 'express';
import fs from 'fs/promises';
import getPort, { makeRange } from 'get-port';
import type { Server } from 'http';
import path from 'path';
import * as z from 'zod';
import { StatusCodes, type Status } from './action.js';
import { GENKIT_REFLECTION_API_SPEC_VERSION, GENKIT_VERSION } from './index.js';
import { logger } from './logging.js';
import type { Registry } from './registry.js';
import { toJsonSchema } from './schema.js';
import { flushTracing, setTelemetryServerUrl } from './tracing.js';

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
 *
 * @hidden
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
  /** Path to the runtime file. Null if server is not running. */
  private runtimeFilePath: string | null = null;

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
    server.use((req, res, next) => {
      res.header('x-genkit-version', GENKIT_VERSION);
      next();
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
        const actions = await this.registry.listResolvableActions();
        const convertedActions = {};
        Object.keys(actions).forEach((key) => {
          const action = actions[key];
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
      const { key, input, context, telemetryLabels } = request.body;
      const { stream } = request.query;
      logger.debug(`Running action \`${key}\` with stream=${stream}...`);
      try {
        const action = await this.registry.lookupAction(key);
        if (!action) {
          response.status(404).send(`action ${key} not found`);
          return;
        }
        if (stream === 'true') {
          try {
            const callback = (chunk) => {
              response.write(JSON.stringify(chunk) + '\n');
            };
            const result = await action.run(input, {
              context,
              onChunk: callback,
              telemetryLabels,
            });
            await flushTracing();
            response.write(
              JSON.stringify({
                result: result.result,
                telemetry: {
                  traceId: result.telemetry.traceId,
                },
              } as RunActionResponse)
            );
            response.end();
          } catch (err) {
            const { message, stack } = err as Error;
            // since we're streaming, we must do special error handling here -- the headers are already sent.
            const errorResponse: Status = {
              code: StatusCodes.INTERNAL,
              message,
              details: {
                stack,
              },
            };
            if ((err as any).traceId) {
              errorResponse.details.traceId = (err as any).traceId;
            }
            response.write(
              JSON.stringify({
                error: errorResponse,
              } as RunActionResponse)
            );
            response.end();
          }
        } else {
          const result = await action.run(input, { context, telemetryLabels });
          await flushTracing();
          response.send({
            result: result.result,
            telemetry: {
              traceId: result.telemetry.traceId,
            },
          } as RunActionResponse);
        }
      } catch (err) {
        const { message, stack, traceId } = err as any;
        next({ message, stack, traceId });
      }
    });

    server.get('/api/envs', async (_, response) => {
      response.json(this.options.configuredEnvs);
    });

    server.post('/api/notify', async (request, response) => {
      const { telemetryServerUrl, reflectionApiSpecVersion } = request.body;
      if (!process.env.GENKIT_TELEMETRY_SERVER) {
        if (typeof telemetryServerUrl === 'string') {
          setTelemetryServerUrl(telemetryServerUrl);
          logger.debug(
            `Connected to telemetry server on ${telemetryServerUrl}`
          );
        }
      }
      if (reflectionApiSpecVersion !== GENKIT_REFLECTION_API_SPEC_VERSION) {
        if (
          !reflectionApiSpecVersion ||
          reflectionApiSpecVersion < GENKIT_REFLECTION_API_SPEC_VERSION
        ) {
          logger.warn(
            'WARNING: Genkit CLI version may be outdated. Please update `genkit-cli` to the latest version.'
          );
        } else {
          logger.warn(
            'Genkit CLI is newer than runtime library. Some feature may not be supported. ' +
              'Consider upgrading your runtime library version (debug info: expected ' +
              `${GENKIT_REFLECTION_API_SPEC_VERSION}, got ${reflectionApiSpecVersion}).`
          );
        }
      }
      response.status(200).send('OK');
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
    this.server = server.listen(this.port, async () => {
      logger.debug(
        `Reflection server (${process.pid}) running on http://localhost:${this.port}`
      );
      ReflectionServer.RUNNING_SERVERS.push(this);
      await this.writeRuntimeFile();
    });
  }

  /**
   * Stops the server and removes it from the list of running servers to clean up on exit.
   */
  async stop(): Promise<void> {
    if (!this.server) {
      return;
    }
    return new Promise<void>(async (resolve, reject) => {
      await this.cleanupRuntimeFile();
      this.server!.close(async (err) => {
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
        logger.debug(
          `Reflection server on port ${this.port} has successfully shut down.`
        );
        this.port = null;
        this.server = null;
        resolve();
      });
    });
  }

  /**
   * Writes the runtime file to the project root.
   */
  private async writeRuntimeFile() {
    try {
      const rootDir = await findProjectRoot();
      const runtimesDir = path.join(rootDir, '.genkit', 'runtimes');
      const date = new Date();
      const time = date.getTime();
      const timestamp = date.toISOString();
      const runtimeId = `${process.pid}${
        this.port !== null ? `-${this.port}` : ''
      }`;
      this.runtimeFilePath = path.join(
        runtimesDir,
        `${runtimeId}-${time}.json`
      );
      const fileContent = JSON.stringify(
        {
          id: process.env.GENKIT_RUNTIME_ID || runtimeId,
          pid: process.pid,
          reflectionServerUrl: `http://localhost:${this.port}`,
          timestamp,
          genkitVersion: `nodejs/${GENKIT_VERSION}`,
          reflectionApiSpecVersion: GENKIT_REFLECTION_API_SPEC_VERSION,
        },
        null,
        2
      );
      await fs.mkdir(runtimesDir, { recursive: true });
      await fs.writeFile(this.runtimeFilePath, fileContent, 'utf8');
      logger.debug(`Runtime file written: ${this.runtimeFilePath}`);
    } catch (error) {
      logger.error(`Error writing runtime file: ${error}`);
    }
  }

  /**
   * Cleans up the port file.
   */
  private async cleanupRuntimeFile() {
    if (!this.runtimeFilePath) {
      return;
    }
    try {
      const fileContent = await fs.readFile(this.runtimeFilePath, 'utf8');
      const data = JSON.parse(fileContent);
      if (data.pid === process.pid) {
        await fs.unlink(this.runtimeFilePath);
        logger.debug(`Runtime file cleaned up: ${this.runtimeFilePath}`);
      }
    } catch (error) {
      logger.error(`Error cleaning up runtime file: ${error}`);
    }
  }

  /**
   * Stops all running reflection servers.
   */
  static async stopAll() {
    return Promise.all(
      ReflectionServer.RUNNING_SERVERS.map((server) => server.stop())
    );
  }
}

/**
 * Finds the project root by looking for a `package.json` file.
 */
async function findProjectRoot(): Promise<string> {
  let currentDir = process.cwd();
  while (currentDir !== path.parse(currentDir).root) {
    const packageJsonPath = path.join(currentDir, 'package.json');
    try {
      await fs.access(packageJsonPath);
      return currentDir;
    } catch {
      currentDir = path.dirname(currentDir);
    }
  }
  throw new Error('Could not find project root (package.json not found)');
}

// TODO: Verify that this works.
if (typeof module !== 'undefined' && 'hot' in module) {
  (module as any).hot.accept();
  (module as any).hot.dispose(async () => {
    logger.debug('Cleaning up reflection server(s) before module reload...');
    await ReflectionServer.stopAll();
  });
}
