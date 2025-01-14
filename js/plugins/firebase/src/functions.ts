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

import { expressHandler } from '@genkit-ai/express';
import * as express from 'express';
import { getAppCheck } from 'firebase-admin/app-check';
import {
  HttpsFunction,
  HttpsOptions,
  onRequest,
} from 'firebase-functions/v2/https';
import { Flow, FlowFn, Genkit, z } from 'genkit';
import { logger } from 'genkit/logging';
import { initializeAppIfNecessary } from './helpers.js';

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
 *
 * @hidden
 */
export interface RequestWithAuth extends express.Request {
  auth?: unknown;
}

export type FunctionFlow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny,
> = HttpsFunction & { flow: Flow<I, O, S> };

export interface FunctionFlowAuth<I extends z.ZodTypeAny> {
  provider: express.RequestHandler;
  policy: FlowAuthPolicy<I>;
}

interface FunctionFlowConfig<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny,
> {
  name: string;
  inputSchema?: I;
  outputSchema?: O;
  authPolicy: FunctionFlowAuth<I>;
  streamSchema?: S;
  httpsOptions?: HttpsOptions;
  enforceAppCheck?: boolean;
  consumeAppCheckToken?: boolean;
}

/**
 * Creates a flow backed by Cloud Functions for Firebase gen2 HTTPS function.
 */
export function onFlow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny,
>(
  genkit: Genkit,
  config: FunctionFlowConfig<I, O, S>,
  steps: FlowFn<I, O, S>
): FunctionFlow<I, O, S> {
  const flow = genkit.defineFlow(
    {
      ...config,
    },
    steps
  );

  const wrapped = wrapHttpsFlow(genkit, flow, config);

  const funcFlow = wrapped as FunctionFlow<I, O, S>;
  funcFlow.flow = flow;
  return funcFlow;
}

function wrapHttpsFlow<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny,
>(
  genkit: Genkit,
  flow: Flow<I, O, S>,
  config: FunctionFlowConfig<I, O, S>
): HttpsFunction {
  return onRequest(
    {
      ...config.httpsOptions,
      memory: config.httpsOptions?.memory || '512MiB',
    },
    async (req, res) => {
      if (config.enforceAppCheck) {
        if (
          !(await appCheckValid(
            req.headers['x-firebase-appcheck'],
            !!config.consumeAppCheckToken
          ))
        ) {
          const respBody = {
            error: {
              status: 'UNAUTHENTICATED',
              message: 'Unauthorized',
            },
          };
          logger.logStructured(`Response[/${flow.name}]`, {
            path: `/${flow.name}`,
            code: 401,
            body: respBody,
          });
          res.status(401).send(respBody).end();
          return;
        }
      }

      await config.authPolicy.provider(req, res, () =>
        expressHandler(flow, {
          authPolicy: (context) =>
            config.authPolicy.policy(context.auth, context.input),
        })(req, res, () => {})
      );
    }
  );
}

async function appCheckValid(
  tok: string | string[] | undefined,
  consume: boolean
): Promise<boolean> {
  if (typeof tok !== 'string') return false;
  initializeAppIfNecessary();
  try {
    const appCheckClaims = await getAppCheck().verifyToken(tok, { consume });

    if (consume && appCheckClaims.alreadyConsumed) return false;
    return true;
  } catch (e) {
    return false;
  }
}

/**
 * Indicates that no authorization is in effect.
 *
 * WARNING: If you are using Cloud Functions for Firebase with no IAM policy,
 * this will allow anyone on the internet to execute this flow.
 */
export function noAuth(): FunctionFlowAuth<any> {
  return {
    provider: (req, res, next) => next(),
    policy: () => {},
  };
}
