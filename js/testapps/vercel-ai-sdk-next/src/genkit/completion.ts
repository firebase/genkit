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

import { z } from 'genkit';
import { ai } from './index';

/**
 * Completion flow for use with completionHandler + useCompletion.
 *
 * inputSchema:  z.string()  — the raw prompt string sent by useCompletion.
 * streamSchema: z.string()  — plain text deltas (simplest stream format).
 *
 * Works with both the default SSE mode and streamProtocol: 'text' mode
 * since it emits plain string chunks (not typed StreamChunk objects).
 */
export const completionFlow = ai.defineFlow(
  {
    name: 'completion',
    inputSchema: z.string(),
    outputSchema: z.string(),
    streamSchema: z.string(),
  },
  async (prompt, { sendChunk }) => {
    const { stream, response } = ai.generateStream(prompt);

    for await (const chunk of stream) {
      if (chunk.text) {
        sendChunk(chunk.text);
      }
    }

    return (await response).text;
  }
);
