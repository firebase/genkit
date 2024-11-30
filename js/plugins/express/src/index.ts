import express from 'express';
import { CallableFlow, z } from 'genkit';
import { getErrorMessage, getErrorStack } from './utils';

const streamDelimiter = '\n\n';

/**
 * Flow Auth policy. Consumes the authorization context of the flow and
 * performs checks before the flow runs. If this throws, the flow will not
 * be executed.
 */
export interface FlowAuthPolicy<I> {
  (auth: any | undefined, input: I): void | Promise<void>;
}

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
 */
export interface __RequestWithAuth extends express.Request {
  auth?: unknown;
}

export function handler<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  flow: CallableFlow<I, O, S>,
  opts?: {
    authPolicy?: FlowAuthPolicy<I>;
  }
): express.RequestHandler {
  return async (
    request: __RequestWithAuth,
    response: express.Response
  ): Promise<void> => {
    const { stream } = request.query;
    let input = request.body.data;
    const auth = request.auth;

    try {
      await opts?.authPolicy?.(auth, input);
    } catch (e: any) {
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
        const result = await flow.flow.invoke(input, {
          onChunk: (chunk: z.infer<S>) => {
            response.write(
              'data: ' + JSON.stringify({ message: chunk }) + streamDelimiter
            );
          },
          context: auth,
        });
        response.write(
          'data: ' + JSON.stringify({ result: result.result }) + streamDelimiter
        );
        response.end();
      } catch (e) {
        console.log(e);
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
        const result = await flow.flow.invoke(input, { context: auth });
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
