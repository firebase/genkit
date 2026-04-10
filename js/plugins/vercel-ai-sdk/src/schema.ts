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

import { MessageSchema, z } from 'genkit/beta';

// ---------------------------------------------------------------------------
// StreamChunkSchema
// ---------------------------------------------------------------------------

/**
 * Discriminated union of all chunk types a flow can emit via
 * `streamingCallback` to drive the full Vercel AI SDK
 * {@link https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#ui-message-stream-protocol UI Message Stream}
 * protocol.  Use this as `streamSchema` in `ai.defineFlow(...)`.
 *
 * Each variant maps to one or more wire events understood by
 * {@link https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-chat `useChat()`} and
 * {@link https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-completion `useCompletion()`}.
 *
 * ```ts
 * import { StreamChunkSchema } from '@genkit-ai/vercel-ai-sdk';
 *
 * const chatFlow = ai.defineFlow(
 *   { name: 'chat', inputSchema: MessagesSchema, streamSchema: StreamChunkSchema },
 *   async (input, sc) => {
 *     const { stream, response } = ai.generateStream({ messages: input.messages });
 *     for await (const chunk of stream) {
 *       if (chunk.text)  sc({ type: 'text', delta: chunk.text });
 *       for (const tr of chunk.toolRequests) {
 *         sc({ type: 'tool-request', toolCallId: tr.toolRequest.ref ?? tr.toolRequest.name,
 *              toolName: tr.toolRequest.name, input: tr.toolRequest.input });
 *       }
 *     }
 *     return (await response).text;
 *   }
 * );
 * ```
 */
export const StreamChunkSchema = z.discriminatedUnion('type', [
  /** A text delta — maps to `text-start` (lazy) + `text-delta` wire events. */
  z.object({
    type: z.literal('text'),
    delta: z.string(),
  }),

  /**
   * A reasoning/thinking delta — maps to `reasoning-start` (lazy) +
   * `reasoning-delta` wire events.
   * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot#reasoning Reasoning guide}
   */
  z.object({
    type: z.literal('reasoning'),
    delta: z.string(),
  }),

  /**
   * A tool invocation.  Supply either `inputDelta` (streaming partial JSON
   * input) or `input` (full input object) — not both.
   *
   * - `inputDelta` → `tool-input-start` (first time) + `tool-input-delta`
   * - `input`      → `tool-input-start` (if not already open) + `tool-input-available`
   *
   * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot-with-tool-calling Tool calling guide}
   */
  z.object({
    type: z.literal('tool-request'),
    toolCallId: z.string(),
    toolName: z.string(),
    inputDelta: z.string().optional(),
    input: z.unknown().optional(),
  }),

  /**
   * A tool result — maps to `tool-output-available`.
   * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot-with-tool-calling Tool calling guide}
   */
  z.object({
    type: z.literal('tool-result'),
    toolCallId: z.string(),
    output: z.unknown(),
  }),

  /**
   * A tool input parsing error — maps to `tool-input-error`.
   * Emitted when a tool's input fails validation or parsing.
   * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot-with-tool-calling Tool calling guide}
   */
  z.object({
    type: z.literal('tool-input-error'),
    toolCallId: z.string(),
    toolName: z.string(),
    input: z.unknown(),
    errorText: z.string(),
  }),

  /**
   * A tool execution error — maps to `tool-output-error`.
   * Emitted when a tool call fails during execution.
   * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot-with-tool-calling Tool calling guide}
   */
  z.object({
    type: z.literal('tool-output-error'),
    toolCallId: z.string(),
    errorText: z.string(),
  }),

  /**
   * A tool output denied — maps to `tool-output-denied`.
   * Emitted when a tool's output is blocked or denied.
   * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot-with-tool-calling Tool calling guide}
   */
  z.object({
    type: z.literal('tool-output-denied'),
    toolCallId: z.string(),
  }),

  /**
   * A tool approval request — maps to `tool-approval-request`.
   * Emitted to request human-in-the-loop approval before executing a tool.
   * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot-with-tool-calling Tool calling guide}
   */
  z.object({
    type: z.literal('tool-approval-request'),
    approvalId: z.string(),
    toolCallId: z.string(),
  }),

  /**
   * Arbitrary custom data — maps to a `data-${id}` wire event.
   * Accessible on the client via the `onData` callback in `useChat`.
   * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#ui-message-stream-protocol UI Message Stream protocol}
   */
  z.object({
    type: z.literal('data'),
    id: z.string(),
    value: z.unknown(),
  }),

  /**
   * A file or image to surface in the chat UI — maps to a `file` wire event.
   * Note: the AI SDK wire format does not support a filename field.
   * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot#file-attachments File attachments}
   */
  z.object({
    type: z.literal('file'),
    url: z.string(),
    mediaType: z.string(),
  }),

  /**
   * A web source citation — maps to a `source-url` wire event.
   * Renders as a clickable source card alongside the response.
   * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot#sources Sources}
   */
  z.object({
    type: z.literal('source-url'),
    sourceId: z.string(),
    url: z.string(),
    title: z.string().optional(),
  }),

  /**
   * A document source citation — maps to a `source-document` wire event.
   * Use for RAG responses where the source is a local/retrieved document
   * rather than a live web URL.
   * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot#sources Sources}
   */
  z.object({
    type: z.literal('source-document'),
    sourceId: z.string(),
    mediaType: z.string(),
    title: z.string(),
    filename: z.string().optional(),
  }),

  /**
   * Begin a logical step (e.g. one LLM call in a multi-step agent loop).
   * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot#multi-step-generation Multi-step generation}
   */
  z.object({ type: z.literal('step-start') }),

  /**
   * End the current logical step. Closes any open text/reasoning blocks.
   * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot#multi-step-generation Multi-step generation}
   */
  z.object({ type: z.literal('step-end') }),
]);

export type StreamChunk = z.infer<typeof StreamChunkSchema>;

// ---------------------------------------------------------------------------
// MessagesSchema (extended)
// ---------------------------------------------------------------------------

/**
 * Zod schema for the multi-turn chat input accepted by `chatHandler()`.
 * Use this as the `inputSchema` of your chat flow.
 *
 * Uses Genkit's own `MessageSchema` directly, so `input.messages` can be
 * passed straight to `ai.generateStream({ messages: input.messages })`
 * without type casts.
 *
 * The optional `body` field carries any extra fields the client sends via
 * {@link https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-chat#body `useChat({ body: {...} })`},
 * so flows can access per-request metadata (e.g. a session ID, selected
 * persona, or RAG filter) via `input.body`.
 *
 * @see {@link https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-chat useChat() reference}
 */
export const MessagesSchema = z.object({
  messages: z.array(MessageSchema),
  /** Extra fields sent by the client via useChat({ body: {...} }). */
  body: z.record(z.unknown()).optional(),
});

export type Messages = z.infer<typeof MessagesSchema>;

// ---------------------------------------------------------------------------
// FlowOutputSchema
// ---------------------------------------------------------------------------

/**
 * Optional structured output schema for chat and completion flows.  When a
 * flow returns a value matching this shape, `chatHandler` and
 * `completionHandler` will populate the
 * {@link https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#finish-chunk `finish`}
 * SSE event with `finishReason` and `usage`.
 *
 * ```ts
 * const chatFlow = ai.defineFlow(
 *   { name: 'chat', inputSchema: MessagesSchema,
 *     streamSchema: StreamChunkSchema, outputSchema: FlowOutputSchema },
 *   async (input, sc) => {
 *     const { stream, response } = ai.generateStream({ ... });
 *     for await (const chunk of stream) { ... }
 *     const res = await response;
 *     return { finishReason: res.finishReason, usage: res.usage };
 *   }
 * );
 * ```
 */
export const FlowOutputSchema = z.object({
  finishReason: z.string().optional(),
  usage: z.record(z.unknown()).optional(),
});

export type FlowOutput = z.infer<typeof FlowOutputSchema>;
