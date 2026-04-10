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
 */
export interface ObjectHandlerOptions {
  /** Called on mid-stream error; return the text to emit (best-effort). */
  onError?: (err: unknown) => string;
  /**
   * Extract auth/session context from the incoming request.
   * Throw to reject the request before the stream opens; status is derived
   * via `getHttpStatus()`.  Mid-stream errors cannot be cleanly signaled due
   * to the `useObject()` protocol using raw text/plain — this is a protocol
   * constraint, not a Genkit limitation.
   */
  contextProvider?: ContextProvider<any, any>;
}

/**
 * Wraps a Genkit streaming flow and returns a Fetch API-compatible route
 * handler that speaks the Vercel AI SDK `useObject()` protocol.
 *
 * The flow must have `streamSchema: z.string()` — each chunk emitted via
 * `streamingCallback` should be a fragment of the JSON string being produced.
 * The flow's `outputSchema` should describe the full object shape for
 * client-side type safety with `useObject({ schema })`.
 *
 * Unlike `chatHandler` and `completionHandler`, the response is raw
 * `text/plain` streaming partial JSON.  `useObject()` reassembles fragments
 * incrementally — each chunk does not need to be valid JSON on its own.
 *
 * ```ts
 * // src/app/api/notifications/route.ts
 * export const POST = objectHandler(notificationsFlow);
 * ```
 *
 * - Request:  `POST` with any JSON body (passed verbatim as flow input)
 * - Response: `text/plain` streaming partial JSON
 */
export function objectHandler(
  flow: Action<z.ZodTypeAny, z.ZodTypeAny, z.ZodString>,
  opts?: ObjectHandlerOptions
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
        context = await opts.contextProvider({
          method: 'POST',
          headers: headersToRecord(req.headers),
          input,
        });
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
        const message = opts?.onError
          ? opts.onError(err)
          : 'An error occurred.';
        console.error('[objectHandler]', err);
        await writer.write(encoder.encode(JSON.stringify({ error: message })));
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
