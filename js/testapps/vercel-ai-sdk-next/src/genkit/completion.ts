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
  FlowOutputSchema,
  StreamChunkSchema,
  toFlowOutput,
  toStreamChunks,
} from '@genkit-ai/vercel-ai-sdk';
import { z } from 'genkit';
import { ai } from './index';

/**
 * Completion flow for use with completionHandler + useCompletion.
 *
 * inputSchema:  z.string()          — the raw prompt string sent by useCompletion.
 * streamSchema: StreamChunkSchema   — typed chunks for the full SSE protocol.
 * outputSchema: FlowOutputSchema    — finishReason + usage for the finish event.
 *
 * Extra fields sent by the client via useCompletion({ body: {...} }) are
 * available in the flow's context (set by completionHandler's contextProvider).
 * Access them via ai.currentContext() or pass them to ai.generateStream().
 */
export const completionFlow = ai.defineFlow(
  {
    name: 'completion',
    inputSchema: z.string(),
    outputSchema: FlowOutputSchema,
    streamSchema: StreamChunkSchema,
  },
  async (prompt, { sendChunk }) => {
    const { stream, response } = ai.generateStream(prompt);

    for await (const chunk of stream) {
      for (const sc of toStreamChunks(chunk)) {
        sendChunk(sc);
      }
    }

    return toFlowOutput(await response);
  }
);
