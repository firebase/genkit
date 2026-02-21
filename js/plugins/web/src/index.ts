/**
 * Copyright 2025 Google LLC
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

import { randomUUID } from 'crypto';
import {
  Action,
  ActionStreamInput,
  AsyncTaskQueue,
  Flow,
  StreamNotFoundError,
  type ActionContext,
  type StreamManager,
  type z,
} from 'genkit/beta';
import {
  getCallableJSON,
  getHttpStatus,
  type ContextProvider,
  type RequestData,
} from 'genkit/context';
import { logger } from 'genkit/logging';

const streamDelimiter = '\n\n';

/**
 * A wrapper object containing a flow with its associated options.
 */
export type FlowWithOptions<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> = {
  flow: Flow<I, O, S>;
  options: {
    contextProvider?: ContextProvider<any, I>;
    streamManager?: StreamManager;
    path?: string;
  };
};

/**
 * Options for handling a flow request.
 */
export interface HandleFlowOptions<
  C extends ActionContext = ActionContext,
  I extends z.ZodTypeAny = z.ZodTypeAny,
> {
  contextProvider?: ContextProvider<C, I>;
  streamManager?: StreamManager;
}

/**
 * Wraps a flow with options (e.g. contextProvider, streamManager, path) for use with {@link handleFlows}.
 */
export function withFlowOptions<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny,
>(
  flow: Flow<I, O, S>,
  options: {
    contextProvider?: ContextProvider<any, I>;
    streamManager?: StreamManager;
    path?: string;
  }
): FlowWithOptions<I, O, S> {
  return {
    flow,
    options,
  };
}

/**
 * Converts Headers object to a plain object with lowercase keys.
 */
function headersToObject(headers: Headers): Record<string, string> {
  const result: Record<string, string> = {};
  headers.forEach((value, key) => {
    result[key.toLowerCase()] = value;
  });
  return result;
}

/**
 * Gets context from the request using the context provider if available.
 */
async function getContext<C extends ActionContext, I extends z.ZodTypeAny>(
  request: Request,
  input: z.infer<I>,
  provider?: ContextProvider<C, I>
): Promise<C> {
  const context = {} as C;
  if (!provider) {
    return context;
  }

  const requestData: RequestData = {
    method: request.method as RequestData['method'],
    headers: headersToObject(request.headers),
    input,
  };

  return await provider(requestData);
}

/**
 * Subscribes to an existing stream using StreamManager.
 */
async function subscribeToStream(
  streamManager: StreamManager,
  streamId: string
): Promise<Response | null> {
  try {
    const encoder = new TextEncoder();
    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();

    await streamManager.subscribe(streamId, {
      onChunk: (chunk) => {
        writer.write(
          encoder.encode(
            'data: ' + JSON.stringify({ message: chunk }) + streamDelimiter
          )
        );
      },
      onDone: (output) => {
        writer.write(
          encoder.encode(
            'data: ' + JSON.stringify({ result: output }) + streamDelimiter
          )
        );
        writer.close();
      },
      onError: (err) => {
        logger.error(
          `Streaming request failed with error: ${(err as Error).message}\n${
            (err as Error).stack
          }`
        );
        writer.write(
          encoder.encode(
            `error: ${JSON.stringify({
              error: getCallableJSON(err),
            })}${streamDelimiter}`
          )
        );
        writer.close();
      },
    });

    return new Response(readable, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
        'Transfer-Encoding': 'chunked',
        'x-genkit-stream-id': streamId,
      },
    });
  } catch (e: any) {
    if (e instanceof StreamNotFoundError) {
      return new Response(null, { status: 204 });
    }
    if (e.status === 'DEADLINE_EXCEEDED') {
      const encoder = new TextEncoder();
      const { readable, writable } = new TransformStream();
      const writer = writable.getWriter();
      writer.write(
        encoder.encode(
          `error: ${JSON.stringify({
            error: getCallableJSON(e),
          })}${streamDelimiter}`
        )
      );
      writer.close();
      return new Response(readable, {
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          Connection: 'keep-alive',
          'Transfer-Encoding': 'chunked',
        },
      });
    }
    throw e;
  }
}

/**
 * Runs an action with durable streaming support.
 */
async function runActionWithDurableStreaming<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny,
>(
  action: Action<I, O, S>,
  streamManager: StreamManager | undefined,
  streamId: string,
  input: z.infer<I>,
  context: ActionContext,
  writer: WritableStreamDefaultWriter<Uint8Array>,
  abortSignal: AbortSignal
): Promise<void> {
  const encoder = new TextEncoder();
  let taskQueue: AsyncTaskQueue | undefined;
  let durableStream: ActionStreamInput<any, any> | undefined;

  if (streamManager) {
    taskQueue = new AsyncTaskQueue();
    durableStream = await streamManager.open(streamId);
  }

  try {
    let onChunk = (chunk: z.infer<S>) => {
      writer.write(
        encoder.encode(
          'data: ' + JSON.stringify({ message: chunk }) + streamDelimiter
        )
      );
    };

    if (streamManager && durableStream) {
      const originalOnChunk = onChunk;
      onChunk = (chunk: z.infer<S>) => {
        originalOnChunk(chunk);
        taskQueue!.enqueue(() => durableStream!.write(chunk));
      };
    }

    const result = await action.run(input, {
      onChunk,
      context,
      abortSignal,
    });

    if (streamManager && durableStream) {
      taskQueue!.enqueue(() => durableStream!.done(result.result));
      await taskQueue!.merge();
    }

    writer.write(
      encoder.encode(
        'data: ' + JSON.stringify({ result: result.result }) + streamDelimiter
      )
    );
    writer.close();
  } catch (e) {
    if (durableStream) {
      taskQueue!.enqueue(() => durableStream!.error(e));
      await taskQueue!.merge();
    }
    logger.error(
      `Streaming request failed with error: ${(e as Error).message}\n${
        (e as Error).stack
      }`
    );
    writer.write(
      encoder.encode(
        `error: ${JSON.stringify({
          error: getCallableJSON(e),
        })}${streamDelimiter}`
      )
    );
    writer.close();
  }
}

/**
 * Handles a single flow request and returns a Response.
 *
 * @param request - The Web API Request object
 * @param action - The Genkit Action/Flow to execute
 * @param options - Optional configuration including contextProvider and streamManager
 * @returns A Promise that resolves to a Response object
 *
 * @example
 * ```typescript
 * import { handleFlow } from '@genkit-ai/web';
 *
 * app.all('/myFlow', async (c) => {
 *   return handleFlow(c.req.raw, myFlow);
 * });
 * ```
 */
export async function handleFlow<
  C extends ActionContext = ActionContext,
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  request: Request,
  action: Action<I, O, S>,
  options?: HandleFlowOptions<C, I>
): Promise<Response> {
  // Parse query parameters
  const url = new URL(request.url);
  const streamParam = url.searchParams.get('stream');
  const shouldStream = streamParam === 'true';

  // Get stream ID from headers
  const streamIdHeader = request.headers.get('x-genkit-stream-id');
  const streamId = streamIdHeader || undefined;

  // Parse request body
  let body: any;
  try {
    body = await request.json();
  } catch (e) {
    const errMsg =
      `Error: Failed to parse request body as JSON. ` +
      `Make sure the request has 'Content-Type: application/json' header.`;
    logger.error(errMsg);
    return new Response(
      JSON.stringify({ message: errMsg, status: 'INVALID_ARGUMENT' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    );
  }

  if (!body || typeof body !== 'object' || !('data' in body)) {
    const errMsg =
      `Error: Request body must be a JSON object with a 'data' field. ` +
      `Expected format: {"data": ...}`;
    logger.error(errMsg);
    return new Response(
      JSON.stringify({ message: errMsg, status: 'INVALID_ARGUMENT' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    );
  }

  const input = body.data as z.infer<I>;

  // Get context from context provider
  let context: C;
  try {
    context = await getContext(request, input, options?.contextProvider);
  } catch (e: any) {
    logger.error(
      `Context provider failed with error: ${(e as Error).message}\n${
        (e as Error).stack
      }`
    );
    return new Response(JSON.stringify(getCallableJSON(e)), {
      status: getHttpStatus(e),
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // Check if streaming is requested
  const acceptHeader = request.headers.get('Accept') || '';
  const isStreaming = acceptHeader === 'text/event-stream' || shouldStream;

  if (isStreaming) {
    const streamManager = options?.streamManager;
    if (streamManager && streamId) {
      const response = await subscribeToStream(streamManager, streamId);
      if (response) {
        return response;
      }
    }

    const streamIdToUse = randomUUID();
    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();

    // Start streaming in the background
    runActionWithDurableStreaming(
      action,
      streamManager,
      streamIdToUse,
      input,
      context,
      writer,
      request.signal
    ).catch((err) => {
      logger.error(`Error in streaming handler: ${err}`);
    });

    const headers: Record<string, string> = {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      'Transfer-Encoding': 'chunked',
    };

    if (streamManager) {
      headers['x-genkit-stream-id'] = streamIdToUse;
    }

    return new Response(readable, {
      status: 200,
      headers,
    });
  }

  // Non-streaming request
  try {
    const result = await action.run(input, {
      context,
      abortSignal: request.signal,
    });

    const headers: Record<string, string> = {
      'x-genkit-trace-id': result.telemetry.traceId,
      'x-genkit-span-id': result.telemetry.spanId,
    };

    return new Response(JSON.stringify({ result: result.result }), {
      status: 200,
      headers: { 'Content-Type': 'application/json', ...headers },
    });
  } catch (e) {
    logger.error(
      `Non-streaming request failed with error: ${(e as Error).message}\n${
        (e as Error).stack
      }`
    );
    return new Response(JSON.stringify(getCallableJSON(e)), {
      status: getHttpStatus(e),
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * Handles multiple flows by routing based on the URL path.
 *
 * @param request - The Web API Request object
 * @param flows - Array of flows with their options
 * @param pathPrefix - Optional path prefix to strip from the URL (e.g., '/api/genkit')
 * @returns A Promise that resolves to a Response (200 for success, 404 if no flow matches)
 *
 * @example
 * ```typescript
 * import { handleFlows } from '@genkit-ai/web';
 *
 * app.all('/api/genkit/*', async (c) => {
 *   return handleFlows(c.req.raw, [flow1, flow2], '/api/genkit');
 * });
 * ```
 */
export async function handleFlows(
  request: Request,
  flows: (Flow<any, any, any> | FlowWithOptions<any, any, any>)[],
  pathPrefix?: string
): Promise<Response> {
  const url = new URL(request.url);
  let pathname = url.pathname;

  // Remove path prefix if provided
  if (pathPrefix) {
    if (pathname.startsWith(pathPrefix)) {
      pathname = pathname.slice(pathPrefix.length);
    } else {
      return new Response(
        JSON.stringify({
          status: 'NOT_FOUND',
          message: 'No flow matched the request path.',
        }),
        { status: 404, headers: { 'Content-Type': 'application/json' } }
      );
    }
  }

  // Remove leading slash
  pathname = pathname.replace(/^\//, '');

  // Find matching flow
  let matchedFlow: Flow<any, any, any> | null = null;
  let flowOptions: HandleFlowOptions<any, any> | undefined = undefined;

  for (const flow of flows) {
    if ('flow' in flow) {
      const options = flow.options;
      const flowPath = options.path || flow.flow.__action.name;
      if (pathname === flowPath) {
        matchedFlow = flow.flow;
        flowOptions = {
          contextProvider: options.contextProvider,
          streamManager: options.streamManager,
        };
        break;
      }
    } else {
      // Plain Flow
      if (pathname === flow.__action.name) {
        matchedFlow = flow;
        break;
      }
    }
  }

  if (!matchedFlow) {
    return new Response(
      JSON.stringify({
        status: 'NOT_FOUND',
        message: 'No flow matched the request path.',
      }),
      { status: 404, headers: { 'Content-Type': 'application/json' } }
    );
  }

  return handleFlow(request, matchedFlow, flowOptions);
}
