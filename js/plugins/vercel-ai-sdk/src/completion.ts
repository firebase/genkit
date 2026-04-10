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

import { createTextStreamResponse } from 'ai';
import { type ContextProvider } from 'genkit/context';
import { StreamChunkSchema } from './schema.js';
import { createSSEResponse } from './stream.js';
import { headersToRecord, resolveStatus } from './utils.js';

/**
 * A Genkit flow compatible with `completionHandler`.
 *
 * Your flow must use:
 * - `inputSchema: z.string()`
 * - `streamSchema: StreamChunkSchema`
 *
 * The `outputSchema` is unconstrained (use `FlowOutputSchema` to populate
 * `finishReason` and `usage` in the finish SSE event, or omit it).
 */
export type CompletionFlow = {
  stream(
    input?: string,
    opts?: any
  ): { stream: AsyncIterable<unknown>; output: Promise<unknown> };
};

/**
 * Options for `completionHandler`.
 *
 * @typeParam Ctx - Shape of the context object returned by `contextProvider`.
 *   TypeScript infers this from your `contextProvider` implementation.
 */
export interface CompletionHandlerOptions<
  Ctx extends Record<string, unknown> = Record<string, unknown>,
> {
  /**
   * Called on unhandled errors thrown by the flow.  Return a string to surface
   * a message to the client; return `void` (or nothing) to use the default
   * "An error occurred." message.
   */
  onError?: (err: unknown) => string | void;
  /**
   * Extract auth/session context from the incoming request.
   * Throw to reject the request; status is derived via `getHttpStatus()`.
   */
  contextProvider?: ContextProvider<Ctx, any>;
  /**
   * Stream protocol to use in the response.
   *
   * - **`'data'`** (default) — Vercel AI SDK
   *   {@link https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#ui-message-stream-protocol UI Message Stream}
   *   format (SSE). Use with the default `useCompletion()` configuration.
   * - **`'text'`** — Raw `text/plain` streaming.
   *   Use when `useCompletion` is configured with
   *   {@link https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-completion#streamProtocol `streamProtocol: 'text'`}.
   *   In this mode only `{ type: 'text', delta }` chunks are forwarded;
   *   other typed chunks are ignored.
   */
  streamProtocol?: 'data' | 'text';
}

/**
 * Wraps a Genkit streaming flow and returns a Fetch API-compatible route
 * handler that speaks the Vercel AI SDK
 * {@link https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-completion `useCompletion()`}
 * protocol.
 *
 * The flow must accept `z.string()` as `inputSchema` and use
 * `StreamChunkSchema` as `streamSchema`.  In `'data'` mode all chunk types
 * are forwarded; in `'text'` mode only `{ type: 'text', delta }` chunks are
 * forwarded and all others are silently skipped.
 *
 * ## Client-supplied context
 *
 * Extra fields sent by the client via
 * {@link https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-completion#body `useCompletion({ body: {...} })`}
 * are available in `contextProvider` as `input.fieldName`.  Place anything
 * the flow needs (session ID, user preferences, etc.) into the returned
 * context object — Genkit stores it in async-local storage so `ai.generate()`
 * calls and tools within the flow can access it automatically.
 *
 * ```ts
 * export const POST = completionHandler(completionFlow, {
 *   contextProvider: async ({ headers, input }) => {
 *     const userId = await verifyToken(headers['authorization']?.slice(7));
 *     return { userId, sessionId: input.sessionId };
 *   },
 * });
 * ```
 *
 * ```ts
 * // src/app/api/completion/route.ts  (default SSE mode)
 * export const POST = completionHandler(completionFlow);
 *
 * // src/app/api/completion/route.ts  (text mode)
 * export const POST = completionHandler(completionFlow, { streamProtocol: 'text' });
 * ```
 *
 * - Request:  `POST` with `{ prompt: string }`
 * - Response: {@link https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#ui-message-stream-protocol UI Message Stream} (`'data'`) or `text/plain` (`'text'`)
 *
 * @see {@link https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-completion useCompletion() reference}
 */
export function completionHandler<
  Ctx extends Record<string, unknown> = Record<string, unknown>,
>(
  flow: CompletionFlow,
  opts?: CompletionHandlerOptions<Ctx>
): (req: Request) => Promise<Response> {
  return async (req: Request): Promise<Response> => {
    // ---- Parse & validate request body ------------------------------------
    let body: Record<string, unknown>;
    try {
      body = await req.json();
    } catch {
      return new Response(
        JSON.stringify({ error: 'Invalid JSON in request body' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    if (typeof body.prompt !== 'string') {
      return new Response(
        JSON.stringify({ error: 'Invalid request: prompt string required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const prompt = body.prompt;

    // ---- Auth context -----------------------------------------------------
    let context: Record<string, unknown> = {};
    if (opts?.contextProvider) {
      try {
        context = await opts.contextProvider({
          method: 'POST',
          headers: headersToRecord(req.headers),
          input: body,
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: String(err) }), {
          status: resolveStatus(err),
          headers: { 'Content-Type': 'application/json' },
        });
      }
    }

    // ---- Text mode --------------------------------------------------------
    if (opts?.streamProtocol === 'text') {
      const { readable, writable } = new TransformStream<string, string>();
      const writer = writable.getWriter();

      (async () => {
        try {
          const { stream } = flow.stream(prompt, {
            context,
            abortSignal: req.signal,
          });
          for await (const chunk of stream) {
            const parsed = StreamChunkSchema.safeParse(chunk);
            if (
              parsed.success &&
              parsed.data.type === 'text' &&
              parsed.data.delta
            ) {
              await writer.write(parsed.data.delta);
            }
          }
        } catch (err) {
          const message =
            (opts?.onError ? opts.onError(err) : undefined) ??
            'An error occurred.';
          await writer.write(message);
        } finally {
          await writer.close();
        }
      })();

      return createTextStreamResponse({ textStream: readable });
    }

    // ---- SSE mode (default) -----------------------------------------------
    return createSSEResponse({
      flow,
      input: prompt,
      context,
      request: req,
      onError: opts?.onError,
    });
  };
}
