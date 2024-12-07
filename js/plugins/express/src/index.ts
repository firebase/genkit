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
import {
  Action,
  CallableFlow,
  Flow,
  runWithStreamingCallback,
  z,
} from 'genkit';
import { logger } from 'genkit/logging';
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
  flow?: Flow<I, O, S>;
  action?: Action<I, O, S>;
  input: z.infer<I>;
  auth: any | undefined;
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
  auth?: unknown;
}

/**
 * Exposes provided flow or an action as express handler.
 */
export function handler<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  f: CallableFlow<I, O, S> | Flow<I, O, S> | Action<I, O, S>,
  opts?: {
    authPolicy?: AuthPolicy<I, O, S>;
  }
): express.RequestHandler {
  const flow: Flow<I, O, S> | undefined = (f as Flow<I, O, S>).invoke
    ? (f as Flow<I, O, S>)
    : (f as CallableFlow<I, O, S>).flow
      ? (f as CallableFlow<I, O, S>).flow
      : undefined;
  const action: Action<I, O, S> = flow ? flow.action : (f as Action<I, O, S>);
  return async (
    request: RequestWithAuth,
    response: express.Response
  ): Promise<void> => {
    const { stream } = request.query;
    let input = request.body.data;
    const auth = request.auth;

    try {
      await opts?.authPolicy?.({
        flow,
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
        const result = await runWithStreamingCallback(onChunk, () =>
          action.run(input, {
            onChunk,
            context: auth,
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
        const result = await action.run(input, { context: auth });
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
