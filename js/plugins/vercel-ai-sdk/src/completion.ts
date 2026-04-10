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

import {
  createTextStreamResponse,
  createUIMessageStream,
  createUIMessageStreamResponse,
} from 'ai';
import { z, type Action } from 'genkit/beta';
import { type ContextProvider } from 'genkit/context';
import {
  closeOpenBlocks,
  createDispatchState,
  dispatchChunk,
} from './dispatch.js';
import { FlowOutputSchema } from './schema.js';
import {
  headersToRecord,
  normalizeFinishReason,
  resolveStatus,
} from './utils.js';

/**
 * Options for `completionHandler`.
 */
export interface CompletionHandlerOptions {
  /** Called on unhandled error; return the text to surface to the client. */
  onError?: (err: unknown) => string;
  /**
   * Extract auth/session context from the incoming request.
   * Throw to reject the request; status is derived via `getHttpStatus()`.
   */
  contextProvider?: ContextProvider<any, any>;
  /**
   * Stream protocol to use in the response.
   *
   * - **`'data'`** (default) — Vercel AI SDK data-stream format (SSE).
   *   Use with the default `useCompletion()` configuration.
   * - **`'text'`** — Raw `text/plain` streaming.
   *   Use when `useCompletion` is configured with `streamProtocol: 'text'`.
   *   In this mode only plain string chunks and `{ type: 'text', delta }` chunks
   *   are forwarded; other typed chunks are ignored.
   */
  streamProtocol?: 'data' | 'text';
}

/**
 * Wraps a Genkit streaming flow and returns a Fetch API-compatible route
 * handler that speaks the Vercel AI SDK `useCompletion()` protocol.
 *
 * The flow must accept `z.string()` as `inputSchema`.  For `streamSchema`:
 *
 * - **`z.string()`** — emit plain text deltas (works in both `'data'` and
 *   `'text'` stream protocols).
 * - **`AiSdkChunkSchema`** — emit typed chunks for the full protocol (only
 *   meaningful in `'data'` mode).
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
 * - Response: SSE stream (`'data'`) or plain text stream (`'text'`)
 */
export function completionHandler(
  flow: Action<z.ZodString, any, any>,
  opts?: CompletionHandlerOptions
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
          input: prompt,
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
            let text: string | undefined;
            if (typeof chunk === 'string') {
              text = chunk;
            } else if (
              chunk !== null &&
              typeof chunk === 'object' &&
              (chunk as any).type === 'text'
            ) {
              text = (chunk as any).delta;
            }
            if (text) await writer.write(text);
          }
        } catch (err) {
          const message = opts?.onError
            ? opts.onError(err)
            : 'An error occurred.';
          await writer.write(message);
        } finally {
          await writer.close();
        }
      })();

      return createTextStreamResponse({ textStream: readable });
    }

    // ---- SSE mode (default) -----------------------------------------------
    const stream = createUIMessageStream({
      execute: async ({ writer }) => {
        const { stream: chunkStream, output } = flow.stream(prompt, {
          context,
          abortSignal: req.signal,
        });

        const state = createDispatchState();
        for await (const chunk of chunkStream) {
          dispatchChunk(writer, chunk, state);
        }
        closeOpenBlocks(writer, state);

        const finalOutput = await output.catch(() => undefined);
        const parsed = FlowOutputSchema.safeParse(finalOutput);
        if (parsed.success) {
          const finishReason = normalizeFinishReason(parsed.data.finishReason);
          const usage = parsed.data.usage;
          writer.write({
            type: 'finish',
            ...(finishReason ? { finishReason } : {}),
            ...(usage ? { messageMetadata: { usage } } : {}),
          });
        }
      },
      onError: opts?.onError,
    });

    return createUIMessageStreamResponse({ stream });
  };
}
