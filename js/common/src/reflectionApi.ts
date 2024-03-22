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
import { zodToJsonSchema } from 'zod-to-json-schema';
import { config } from './config';
import { logger } from './logging';
import * as registry from './registry';
import { StatusCodes, StatusResponse } from './statusTypes';
import {
  flushTracing,
  newTrace,
  setCustomMetadataAttribute,
} from './tracing.js';
import { runWithStreamingCallback } from './types';

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
 * Starts a Reflection API that will be used by the Runner to call and control actions and flows.
 * @param port port on which to listen
 */
export async function startReflectionApi(port?: number | undefined) {
  if (!port) {
    port = Number(process.env.GENKIT_REFLECTION_PORT) || 3100;
  }

  const api = express();

  api.use(express.json());
  /*
  api.use(
    validator.middleware({
      apiSpec: path.join(__dirname, '../../api/reflectionApi.yaml'),
      validateRequests: true,
      validateResponses: true,
      ignoreUndocumented: true,
    })
  );
  */

  api.get('/api/__health', async (_, response) => {
    await registry.listActions();
    response.status(200).send('OK');
  });

  api.get('/api/actions', async (_, response) => {
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
        convertedActions[key].inputSchema =
          action.inputJsonSchema || zodToJsonSchema(action.inputSchema!);
      }
      if (action.outputSchema || action.outputJsonSchema) {
        convertedActions[key].outputSchema =
          action.outputJsonSchema || zodToJsonSchema(action.outputSchema!);
      }
    });
    response.send(convertedActions);
  });

  api.post('/api/runAction', async (request, response) => {
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
          async (_, span) =>
            await runWithStreamingCallback(
              (chunk) => {
                setCustomMetadataAttribute('genkit-dev-internal', 'true');
                traceId = span.spanContext().traceId;
                response.write(JSON.stringify(chunk) + '\n');
              },
              async () => await action(input)
            )
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
      const error = err as Error;
      const { message, stack } = error;
      const errorResponse: StatusResponse = {
        code: StatusCodes.INTERNAL,
        message,
        details: {
          traceId,
          stack,
        },
      };
      logger.error(message);
      return response.status(500).json(errorResponse);
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
      response.status(500).send(`${env} trace store not found`);
      return;
    }
    response.json(await tracestore?.load(traceId));
  });

  api.get('/api/envs/:env/traces', async (request, response) => {
    const { env } = request.params;
    const { limit, continuationToken } = request.query;
    logger.debug(`Fetching traces for env \`${env}\`.`);
    const tracestore = await registry.lookupTraceStore(env);
    if (!tracestore) {
      response.status(500).send(`${env} trace store not found`);
      return;
    }
    response.json(
      await tracestore.list({
        limit: limit ? parseInt(limit.toString()) : undefined,
        continuationToken: continuationToken
          ? continuationToken.toString()
          : undefined,
      })
    );
  });

  api.get('/api/envs/:env/flowStates/:flowId', async (request, response) => {
    const { env, flowId } = request.params;
    logger.debug(`Fetching flow state \`${flowId}\` for env \`${env}\`.`);
    const flowStateStore = await registry.lookupFlowStateStore(env);
    if (!flowStateStore) {
      response.status(500).send(`${env} flow state store not found`);
      return;
    }
    response.json(await flowStateStore?.load(flowId));
  });

  api.get('/api/envs/:env/flowStates', async (request, response) => {
    const { env } = request.params;
    const { limit, continuationToken } = request.query;
    logger.debug(`Fetching traces for env \`${env}\`.`);
    const flowStateStore = await registry.lookupFlowStateStore(env);
    if (!flowStateStore) {
      response.status(500).send(`${env} flow state store not found`);
      return;
    }
    response.json(
      await flowStateStore?.list({
        limit: limit ? parseInt(limit.toString()) : undefined,
        continuationToken: continuationToken
          ? continuationToken.toString()
          : undefined,
      })
    );
  });

  api.listen(port, () => {
    console.log(`Reflection API running on http://localhost:${port}`);
  });
}
