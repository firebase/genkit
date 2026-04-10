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

import { createUIMessageStream, createUIMessageStreamResponse } from 'ai';
import { type Action } from 'genkit/beta';
import { type ContextProvider } from 'genkit/context';
import { toGenkitMessages, type UIMessage } from './convert.js';
import {
  closeOpenBlocks,
  createDispatchState,
  dispatchChunk,
} from './dispatch.js';
import { FlowOutputSchema, MessagesSchema } from './schema.js';
import {
  headersToRecord,
  normalizeFinishReason,
  resolveStatus,
} from './utils.js';

/**
 * Options for `chatHandler`.
 */
export interface ChatHandlerOptions {
  /** Called on unhandled error; return the text to surface to the client. */
  onError?: (err: unknown) => string;
  /**
   * Extract auth/session context from the incoming request.  The derived
   * context is forwarded to the flow via `ActionRunOptions.context`.
   *
   * Throw from this function to reject the request — the HTTP status is
   * derived from the error using Genkit's standard `getHttpStatus()`.
   */
  contextProvider?: ContextProvider<any, any>;
}

/**
 * Wraps a Genkit streaming flow and returns a Fetch API-compatible route
 * handler that speaks the Vercel AI SDK
 * {@link https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-chat `useChat()`}
 * protocol.
 *
 * ## Flow contract
 *
 * The flow must use `MessagesSchema` as `inputSchema`.  For `streamSchema`:
 *
 * - **`z.string()`** — emit plain text deltas (backward-compatible).
 * - **`StreamChunkSchema`** — emit typed chunks for the full protocol (tools,
 *   reasoning, file output, source citations, step markers, custom data).
 *
 * The optional `body` field in `MessagesSchema` carries any extra fields the
 * client sends via
 * {@link https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-chat#body `useChat({ body: {...} })`},
 * accessible as `input.body`.
 *
 * ## Client-side tool execution
 *
 * When `useChat` is configured with
 * {@link https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot-with-tool-calling client-side tools},
 * the browser executes each tool and submits results via `addToolOutput()`.
 * This triggers a new POST with the tool results already folded into the
 * `messages` array as `tool-invocation` parts (`state: 'result'`).
 * `chatHandler` converts these automatically to Genkit tool-response messages
 * via `toGenkitMessages()`, so no special handling is required in your flow.
 *
 * ```ts
 * // src/app/api/chat/route.ts
 * export const POST = chatHandler(chatFlow, {
 *   contextProvider: async ({ headers }) => {
 *     const token = headers['authorization']?.slice(7);
 *     if (!token) throw Object.assign(new Error('Unauthorized'), { status: 401 });
 *     return { userId: await verifyToken(token) };
 *   },
 * });
 * ```
 *
 * - Request:  `POST` with `{ messages: UIMessage[], ...extraFields }`
 * - Response: {@link https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#ui-message-stream-protocol UI Message Stream} (SSE)
 *
 * @see {@link https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-chat useChat() reference}
 * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot Chatbot guide}
 */
export function chatHandler(
  flow: Action<typeof MessagesSchema, any, any>,
  opts?: ChatHandlerOptions
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

    if (!Array.isArray(body.messages)) {
      return new Response(
        JSON.stringify({ error: 'Invalid request: messages array required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const uiMessages: UIMessage[] = body.messages as UIMessage[];
    const genkitMessages = toGenkitMessages(uiMessages);

    // Extra request body fields → forwarded as input.body
    const { messages: _messages, ...extraBody } = body;
    const flowInput = {
      messages: genkitMessages,
      ...(Object.keys(extraBody).length ? { body: extraBody } : {}),
    };

    // ---- Auth context -----------------------------------------------------
    let context: Record<string, unknown> = {};
    if (opts?.contextProvider) {
      try {
        context = await opts.contextProvider({
          method: 'POST',
          headers: headersToRecord(req.headers),
          input: flowInput,
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: String(err) }), {
          status: resolveStatus(err),
          headers: { 'Content-Type': 'application/json' },
        });
      }
    }

    // ---- Stream -----------------------------------------------------------
    const stream = createUIMessageStream({
      execute: async ({ writer }) => {
        const { stream: chunkStream, output } = flow.stream(flowInput, {
          context,
          abortSignal: req.signal,
        });

        const state = createDispatchState();
        for await (const chunk of chunkStream) {
          dispatchChunk(writer, chunk, state);
        }
        closeOpenBlocks(writer, state);

        // Surface finishReason + usage from the flow's return value
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
