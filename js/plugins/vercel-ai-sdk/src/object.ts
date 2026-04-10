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

import { z, type Action } from 'genkit/beta';
import { type ContextProvider } from 'genkit/context';
import { headersToRecord, resolveStatus } from './utils.js';

/**
 * Options for `objectHandler`.
 *
 * @typeParam Ctx - Shape of the context object returned by `contextProvider`.
 *   TypeScript infers this from your `contextProvider` implementation.
 */
export interface ObjectHandlerOptions<
  Ctx extends Record<string, unknown> = Record<string, unknown>,
> {
  /**
   * Called on mid-stream error for logging/reporting.  The stream is closed
   * immediately after — unlike `chatHandler`, any return value is ignored
   * because appending text to a partial JSON stream would corrupt it.
   */
  onError?: (err: unknown) => string | void;
  /**
   * Extract auth/session context from the incoming request.
   * Throw to reject the request before the stream opens; status is derived
   * via `getHttpStatus()`.  Mid-stream errors cannot be cleanly signaled due
   * to the `useObject()` protocol using raw text/plain — this is a protocol
   * constraint, not a Genkit limitation.
   */
  contextProvider?: ContextProvider<any, Ctx>;
}

/**
 * Wraps a Genkit streaming flow and returns a Fetch API-compatible route
 * handler that speaks the Vercel AI SDK
 * {@link https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-object `useObject()`}
 * protocol.
 *
 * The flow must have `streamSchema: z.string()` — each chunk emitted via
 * `streamingCallback` should be a fragment of the JSON string being produced.
 * The flow's `outputSchema` should describe the full object shape for
 * client-side type safety with
 * {@link https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-object#schema `useObject({ schema })`}.
 *
 * Unlike `chatHandler` and `completionHandler`, the response is raw
 * `text/plain` streaming partial JSON.  `useObject()` reassembles fragments
 * incrementally — each chunk does not need to be valid JSON on its own.
 *
 * Note: mid-stream errors cannot be surfaced to the client via a dedicated
 * error channel — this is a
 * {@link https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol protocol constraint}
 * of the `useObject()` text stream format.  Pre-stream errors (auth failures,
 * bad input) still return a non-2xx HTTP status.
 *
 * ```ts
 * // src/app/api/notifications/route.ts
 * export const POST = objectHandler(notificationsFlow);
 * ```
 *
 * - Request:  `POST` with any JSON body (passed verbatim as flow input)
 * - Response: `text/plain` streaming partial JSON
 *
 * @see {@link https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-object useObject() reference}
 * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/object-generation Object generation guide}
 */
export function objectHandler<
  Ctx extends Record<string, unknown> = Record<string, unknown>,
>(
  flow: Action<z.ZodTypeAny, z.ZodTypeAny, z.ZodString>,
  opts?: ObjectHandlerOptions<Ctx>
): (req: Request) => Promise<Response> {
  return async (req: Request): Promise<Response> => {
    // ---- Parse request body -----------------------------------------------
    let input: unknown;
    try {
      input = await req.json();
    } catch {
      return new Response(
        JSON.stringify({ error: 'Invalid JSON in request body' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // ---- Auth context -----------------------------------------------------
    let context: Record<string, unknown> = {};
    if (opts?.contextProvider) {
      try {
        context = (await opts.contextProvider({
          method: 'POST',
          headers: headersToRecord(req.headers),
          input,
        })) as Record<string, unknown>;
      } catch (err) {
        return new Response(JSON.stringify({ error: String(err) }), {
          status: resolveStatus(err),
          headers: { 'Content-Type': 'application/json' },
        });
      }
    }

    // ---- Stream -----------------------------------------------------------
    const encoder = new TextEncoder();
    const { readable, writable } = new TransformStream<
      Uint8Array,
      Uint8Array
    >();
    const writer = writable.getWriter();

    (async () => {
      try {
        const { stream } = flow.stream(input, {
          context,
          abortSignal: req.signal,
        });

        for await (const chunk of stream) {
          if (chunk) {
            await writer.write(encoder.encode(chunk));
          }
        }
      } catch (err) {
        // Do not write to the stream — any appended text would corrupt the
        // partial JSON already sent. Close the stream so useObject fires onError.
        console.error('[objectHandler]', err);
        opts?.onError?.(err);
      } finally {
        await writer.close();
      }
    })();

    return new Response(readable, {
      status: 200,
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-cache',
        'Transfer-Encoding': 'chunked',
      },
    });
  };
}
