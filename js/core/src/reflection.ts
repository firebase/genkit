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

import { serve } from '@hono/node-server';
import fs from 'fs/promises';
import { Hono } from 'hono';
import { bodyLimit } from 'hono/body-limit';
import getPort, { makeRange } from 'get-port';
import type { Server } from 'http';
import path from 'path';
import * as z from 'zod';
import { StatusCodes, type Status } from './action.js';
import { getGenkitRuntimeConfig } from './config.js';
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
  /** Display name that will be shown in developer tooling. */
  name?: string;
}

/** Parses body limit string (e.g. '30mb') to bytes. */
function parseBodyLimitToBytes(limit: string): number {
  const match = limit.toLowerCase().match(/^(\d+)\s*(kb|mb|gb)?$/);
  if (!match) return 30 * 1024 * 1024; // default 30mb
  const n = parseInt(match[1], 10);
  const unit = match[2] || '';
  if (unit === 'kb') return n * 1024;
  if (unit === 'mb') return n * 1024 * 1024;
  if (unit === 'gb') return n * 1024 * 1024 * 1024;
  return n; // bytes
}

/**
 * Checks if an error is an AbortError (from AbortController.abort()).
 */
function isAbortError(err: any): boolean {
  return (
    err?.name === 'AbortError' ||
    (typeof DOMException !== 'undefined' &&
      err instanceof DOMException &&
      err.name === 'AbortError')
  );
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
  /** HTTP server instance. Null if server is not running. */
  private server: Server | null = null;
  /** Path to the runtime file. Null if server is not running. */
  private runtimeFilePath: string | null = null;
  /** Map of active actions indexed by trace ID for cancellation support. */
  private activeActions = new Map<
    string,
    {
      abortController: AbortController;
      startTime: Date;
    }
  >();

  constructor(registry: Registry, options?: ReflectionServerOptions) {
    this.registry = registry;
    this.options = {
      port: 3100,
      bodyLimit: '30mb',
      configuredEnvs: ['dev'],
      ...options,
    };
  }

  get runtimeId() {
    return `${process.pid}${this.port !== null ? `-${this.port}` : ''}`;
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
    if (getGenkitRuntimeConfig().sandboxedRuntime) {
      logger.debug(
        'Skipping ReflectionServer start: not supported in sandboxed runtime.'
      );
      return;
    }

    const bodyLimitBytes = parseBodyLimitToBytes(this.options.bodyLimit!);
    const app = new Hono();

    app.use('*', bodyLimit({ maxSize: bodyLimitBytes }));
    app.use('*', async (c, next) => {
      c.header('x-genkit-version', GENKIT_VERSION);
      await next();
    });

    app.get('/api/__health', async (c) => {
      const id = c.req.query('id');
      if (id && id !== this.runtimeId) {
        return c.text('Invalid runtime ID', 503);
      }
      await this.registry.listActions();
      return c.text('OK', 200);
    });

    app.get('/api/__quitquitquit', async (c) => {
      logger.debug('Received quitquitquit');
      void this.stop();
      return c.text('OK', 200);
    });

    app.get('/api/values', async (c) => {
      logger.debug('Fetching values.');
      const type = c.req.query('type');
      if (!type) {
        return c.text('Query parameter "type" is required.', 400);
      }
      if (type !== 'defaultModel') {
        return c.text(
          `'type' ${type} is not supported. Only 'defaultModel' is supported`,
          400
        );
      }
      const values = await this.registry.listValues(type);
      return c.json(values);
    });

    app.get('/api/actions', async (c) => {
      logger.debug('Fetching actions.');
      const actions = await this.registry.listResolvableActions();
      const convertedActions: Record<string, unknown> = {};
      for (const key of Object.keys(actions)) {
        const action = actions[key];
        const entry: Record<string, unknown> = {
          key,
          name: action.name,
          description: action.description,
          metadata: action.metadata,
        };
        if (action.inputSchema || action.inputJsonSchema) {
          entry.inputSchema = toJsonSchema({
            schema: action.inputSchema,
            jsonSchema: action.inputJsonSchema,
          });
        }
        if (action.outputSchema || action.outputJsonSchema) {
          entry.outputSchema = toJsonSchema({
            schema: action.outputSchema,
            jsonSchema: action.outputJsonSchema,
          });
        }
        convertedActions[key] = entry;
      }
      return c.json(convertedActions);
    });

    app.post('/api/runAction', async (c) => {
      let body: { key?: string; input?: unknown; context?: unknown; telemetryLabels?: unknown };
      try {
        body = await c.req.json();
      } catch {
        return c.json({ error: 'Invalid JSON body' }, 400);
      }
      const { key, input, context, telemetryLabels } = body;
      const stream = c.req.query('stream');
      logger.debug(`Running action \`${key}\` with stream=${stream}...`);
      const abortController = new AbortController();
      let traceId: string | undefined;
      const env = c.env as { outgoing?: import('http').ServerResponse };
      const response = env.outgoing;
      if (!response) {
        return c.json({ error: 'Missing Node response' }, 500);
      }
      if (!key || typeof key !== 'string') {
        return c.text('action key is required', 400);
      }
      try {
        const action = await this.registry.lookupAction(key);
        if (!action) {
          return c.text(`action ${key} not found`, 404);
        }
        const onTraceStartCallback = ({
          traceId: tid,
          spanId,
        }: {
          traceId: string;
          spanId: string;
        }) => {
          traceId = tid;
          this.activeActions.set(tid, {
            abortController,
            startTime: new Date(),
          });
          response.setHeader('X-Genkit-Trace-Id', tid);
          response.setHeader('X-Genkit-Span-Id', spanId);
          response.setHeader('X-Genkit-Version', GENKIT_VERSION);
          if (stream === 'true') {
            response.setHeader('Content-Type', 'text/plain');
            response.setHeader('Transfer-Encoding', 'chunked');
          } else {
            response.setHeader('Content-Type', 'application/json');
            response.setHeader('Transfer-Encoding', 'chunked');
          }
          response.statusCode = 200;
          if ('flushHeaders' in response && typeof response.flushHeaders === 'function') {
            response.flushHeaders();
          }
        };
        if (stream === 'true') {
          try {
            const callback = (chunk: unknown) => {
              response.write(JSON.stringify(chunk) + '\n');
            };
            const result = await action.run(input, {
              context: context as import('./context.js').ActionContext | undefined,
              onChunk: callback,
              telemetryLabels: telemetryLabels as Record<string, string> | undefined,
              onTraceStart: onTraceStartCallback,
              abortSignal: abortController.signal,
            });
            await flushTracing();
            response.write(
              JSON.stringify({
                result: result.result,
                telemetry: { traceId: result.telemetry.traceId },
              } as RunActionResponse)
            );
            response.end();
          } catch (err) {
            const { message, stack } = err as Error;
            const errorResponse: Status = {
              code: isAbortError(err) ? StatusCodes.CANCELLED : StatusCodes.INTERNAL,
              message: isAbortError(err) ? 'Action was cancelled' : message,
              details: { stack, ...((err as any).traceId && { traceId: (err as any).traceId }) },
            };
            response.write(JSON.stringify({ error: errorResponse } as RunActionResponse));
            response.end();
          }
        } else {
          const result = await action.run(input, {
            context: context as import('./context.js').ActionContext | undefined,
            telemetryLabels: telemetryLabels as Record<string, string> | undefined,
            onTraceStart: onTraceStartCallback,
            abortSignal: abortController.signal,
          });
          await flushTracing();
          response.end(
            JSON.stringify({
              result: result.result,
              telemetry: { traceId: result.telemetry.traceId },
            } as RunActionResponse)
          );
        }
      } catch (err) {
        const { message, stack } = err as Error;
        const errorResponse: Status = {
          code: isAbortError(err) ? StatusCodes.CANCELLED : StatusCodes.INTERNAL,
          message: isAbortError(err) ? 'Action was cancelled' : message,
          details: { stack, traceId: (err as any).traceId || traceId },
        };
        if (response.headersSent) {
          response.end(JSON.stringify({ error: errorResponse } as RunActionResponse));
        } else {
          throw err;
        }
      } finally {
        if (traceId) {
          this.activeActions.delete(traceId);
        }
      }
      return new Response(null, {
        status: 200,
        headers: { 'x-hono-already-sent': '1' },
      });
    });

    app.post('/api/cancelAction', async (c) => {
      let body: { traceId?: string };
      try {
        body = await c.req.json();
      } catch {
        return c.json({ error: 'traceId is required' }, 400);
      }
      const { traceId } = body;
      if (!traceId || typeof traceId !== 'string') {
        return c.json({ error: 'traceId is required' }, 400);
      }
      const activeAction = this.activeActions.get(traceId);
      if (activeAction) {
        activeAction.abortController.abort();
        this.activeActions.delete(traceId);
        return c.json({ message: 'Action cancelled' }, 200);
      }
      return c.json(
        { message: 'Action not found or already completed' },
        404
      );
    });

    app.get('/api/envs', (c) => c.json(this.options.configuredEnvs));

    app.post('/api/notify', async (c) => {
      let body: { telemetryServerUrl?: string; reflectionApiSpecVersion?: string };
      try {
        body = await c.req.json();
      } catch {
        return c.text('OK', 200);
      }
      const { telemetryServerUrl, reflectionApiSpecVersion } = body;
      if (!process.env.GENKIT_TELEMETRY_SERVER && typeof telemetryServerUrl === 'string') {
        setTelemetryServerUrl(telemetryServerUrl);
        logger.debug(`Connected to telemetry server on ${telemetryServerUrl}`);
      }
      const version = Number(reflectionApiSpecVersion);
      if (Number.isNaN(version) || version !== GENKIT_REFLECTION_API_SPEC_VERSION) {
        if (!reflectionApiSpecVersion || version < GENKIT_REFLECTION_API_SPEC_VERSION) {
          logger.warn(
            'WARNING: Genkit CLI version may be outdated. Please update `genkit-cli` to the latest version.'
          );
        } else {
          logger.warn(
            'Genkit CLI is newer than runtime library. Some feature may not be supported. ' +
              `Consider upgrading your runtime library version (debug info: expected ${GENKIT_REFLECTION_API_SPEC_VERSION}, got ${reflectionApiSpecVersion}).`
          );
        }
      }
      return c.text('OK', 200);
    });

    app.onError((err, c) => {
      logger.error(err.stack);
      const errorResponse: Status = {
        code: StatusCodes.INTERNAL,
        message: err.message,
        details: { stack: err.stack },
      };
      return (c as { json: (body: unknown, status?: number) => Response }).json(
        { error: errorResponse },
        200
      );
    });

    this.port = await this.findPort();
    this.server = serve(
      { fetch: app.fetch, port: this.port },
      async () => {
        logger.debug(
          `Reflection server (${process.pid}) running on http://localhost:${this.port}`
        );
        ReflectionServer.RUNNING_SERVERS.push(this);
        try {
          await this.registry.listActions();
          await this.writeRuntimeFile();
        } catch (e) {
          logger.error(`Error initializing plugins: ${e}`);
          try {
            await this.stop();
          } catch (stopErr) {
            logger.error(`Failed to stop server gracefully: ${stopErr}`);
          }
        }
      }
    ) as Server;
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
      this.runtimeFilePath = path.join(
        runtimesDir,
        `${this.runtimeId}-${time}.json`
      );
      const fileContent = JSON.stringify(
        {
          id: process.env.GENKIT_RUNTIME_ID || this.runtimeId,
          pid: process.pid,
          name: this.options.name,
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
