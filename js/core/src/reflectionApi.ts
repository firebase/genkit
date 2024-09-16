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
import z from 'zod';
import { runWithStreamingCallback, Status, StatusCodes } from './action.js';
import { config } from './config.js';
import { logger } from './logging.js';
import * as registry from './registry.js';
import { toJsonSchema } from './schema.js';
import {
  cleanUpTracing,
  flushTracing,
  newTrace,
  setCustomMetadataAttribute,
} from './tracing.js';

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

let server;

const GLOBAL_REFLECTION_API_PORT_KEY = 'genkit__reflectionApiPort';

/**
 * Starts a Reflection API that will be used by the Runner to call and control actions and flows.
 * @param port port on which to listen
 */
export async function startReflectionApi(port?: number | undefined) {
  if (global[GLOBAL_REFLECTION_API_PORT_KEY] !== undefined) {
    logger.warn(
      `Reflection API is already running on port ${global[GLOBAL_REFLECTION_API_PORT_KEY]}`
    );
    return;
  }

  if (!port) {
    port = Number(process.env.GENKIT_REFLECTION_PORT) || 3100;
  }
  global[GLOBAL_REFLECTION_API_PORT_KEY] = port;

  const api = express();

  api.use(express.json({ limit: '30mb' }));

  api.get('/api/__health', async (_, response) => {
    await registry.listActions();
    response.status(200).send('OK');
  });

  api.get('/api/__quitquitquit', async (_, response) => {
    logger.debug('Received quitquitquit');
    response.status(200).send('OK');
    await stopReflectionApi();
  });

  api.get('/api/actions', async (_, response, next) => {
    logger.debug('Fetching actions.');
    const actions = await registry.listActions();
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
    // TODO: Remove try/catch when upgrading to Express 5; error is sent to `next` automatically
    // in that version
    try {
      response.send(convertedActions);
    } catch (err) {
      const { message, stack } = err as Error;
      next({ message, stack });
    }
  });

  api.post('/api/runAction', async (request, response, next) => {
    const { key, input } = request.body;
    const { stream } = request.query;
    logger.debug(`Running action \`${key}\`...`);
    let traceId;
    try {
      const action = await registry.lookupAction(key);
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
    response.json(config.configuredEnvs);
  });

  api.get('/api/envs/:env/traces/:traceId', async (request, response) => {
    const { env, traceId } = request.params;
    logger.debug(`Fetching trace \`${traceId}\` for env \`${env}\`.`);
    const tracestore = await registry.lookupTraceStore(env);
    if (!tracestore) {
      return response.status(500).send({
        code: StatusCodes.FAILED_PRECONDITION,
        message: `${env} trace store not found`,
      });
    }
    // TODO: Remove try/catch when upgrading to Express 5; error is sent to `next` automatically
    // in that version
    try {
      const trace = await tracestore?.load(traceId);
      return trace
        ? response.json(trace)
        : response.status(404).send({
            code: StatusCodes.NOT_FOUND,
            message: `Trace with traceId=${traceId} not found.`,
          });
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

  api.get('/api/envs/:env/traces', async (request, response, next) => {
    const { env } = request.params;
    const { limit, continuationToken } = request.query;
    logger.debug(`Fetching traces for env \`${env}\`.`);
    const tracestore = await registry.lookupTraceStore(env);
    if (!tracestore) {
      return response.status(500).send({
        code: StatusCodes.FAILED_PRECONDITION,
        message: `${env} trace store not found`,
      });
    }
    // TODO: Remove try/catch when upgrading to Express 5; error is sent to `next` automatically
    // in that version
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

  api.get(
    '/api/envs/:env/flowStates/:flowId',
    async (request, response, next) => {
      const { env, flowId } = request.params;
      logger.debug(`Fetching flow state \`${flowId}\` for env \`${env}\`.`);
      const flowStateStore = await registry.lookupFlowStateStore(env);
      if (!flowStateStore) {
        return response.status(500).send({
          code: StatusCodes.FAILED_PRECONDITION,
          message: `${env} flow state store not found`,
        });
      }
      // TODO: Remove try/catch when upgrading to Express 5; error is sent to `next` automatically
      // in that version
      try {
        response.json(await flowStateStore?.load(flowId));
      } catch (err) {
        const { message, stack } = err as Error;
        next({ message, stack });
      }
    }
  );

  api.get('/api/envs/:env/flowStates', async (request, response, next) => {
    const { env } = request.params;
    const { limit, continuationToken } = request.query;
    logger.debug(`Fetching traces for env \`${env}\`.`);
    const flowStateStore = await registry.lookupFlowStateStore(env);
    if (!flowStateStore) {
      return response.status(500).send({
        code: StatusCodes.FAILED_PRECONDITION,
        message: `${env} flow state store not found`,
      });
    }
    // TODO: Remove try/catch when upgrading to Express 5; error is sent to `next` automatically
    // in that version
    try {
      response.json(
        await flowStateStore?.list({
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

  server = api.listen(port, () => {
    console.log(`Reflection API running on http://localhost:${port}`);
  });

  server.on('error', (error) => {
    if (process.env.GENKIT_REFLECTION_ON_STARTUP_FAILURE === 'ignore') {
      logger.warn(
        `Failed to start the Reflection API on port ${port}, ignoring the error.`
      );
      logger.debug(error);
    } else {
      throw error;
    }
  });

  process.on('SIGTERM', async () => await stopReflectionApi());
}

/**
 * Stops Reflection API and any running dependencies.
 */
async function stopReflectionApi() {
  await Promise.all([
    new Promise<void>((resolve) => {
      if (server) {
        server.close(() => {
          logger.info('Reflection API has succesfully shut down.');
          resolve();
        });
      } else {
        resolve();
      }
    }),
    cleanUpTracing(),
  ]);
  process.exit(0);
}
