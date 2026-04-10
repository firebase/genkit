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

import type { GenerateResponseChunk } from 'genkit';
import type { StreamChunk } from './schema.js';

/**
 * Converts a Genkit {@link https://genkit.dev/docs/models GenerateResponseChunk}
 * into an array of {@link StreamChunk} values ready to pass to `sendChunk()` in
 * a flow that uses `StreamChunkSchema` as its `streamSchema`.
 *
 * Handles text deltas, reasoning/thinking deltas, and tool-request parts.
 * Returns an empty array for chunks that carry none of these (e.g. pure
 * metadata chunks).
 *
 * ```ts
 * import { toStreamChunks } from '@genkit-ai/vercel-ai-sdk';
 *
 * const chatFlow = ai.defineFlow(
 *   { name: 'chat', inputSchema: MessagesSchema, streamSchema: StreamChunkSchema },
 *   async (input, { sendChunk }) => {
 *     const { stream, response } = ai.generateStream({ ... });
 *     for await (const chunk of stream) {
 *       for (const c of toStreamChunks(chunk)) sendChunk(c);
 *     }
 *     const res = await response;
 *     return { finishReason: res.finishReason, usage: res.usage };
 *   }
 * );
 * ```
 *
 * @see {@link https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#ui-message-stream-protocol UI Message Stream protocol}
 */
export function toStreamChunks(chunk: GenerateResponseChunk): StreamChunk[] {
  const chunks: StreamChunk[] = [];

  if (chunk.reasoning) {
    chunks.push({ type: 'reasoning', delta: chunk.reasoning });
  }

  if (chunk.text) {
    chunks.push({ type: 'text', delta: chunk.text });
  }

  for (const part of chunk.toolRequests) {
    const { ref, name, input } = part.toolRequest;
    chunks.push({
      type: 'tool-request',
      toolCallId: ref ?? name,
      toolName: name,
      input,
    });
  }

  return chunks;
}
