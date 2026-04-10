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
import { NotificationsSchema } from '../schemas';
import { ai } from './index';

export { NotificationsSchema };

/**
 * Object flow for use with objectHandler + useObject.
 *
 * inputSchema:  z.object({ topic: z.string() })  — the POST body from useObject.
 * outputSchema: NotificationsSchema               — the final structured value.
 * streamSchema: z.string()                        — raw JSON text fragments.
 *
 * Each sendChunk call emits a fragment of the final JSON string.  useObject
 * reassembles fragments incrementally and updates the partial object in the UI.
 */
export const notificationsFlow = ai.defineFlow(
  {
    name: 'notifications',
    inputSchema: z.object({ topic: z.string() }),
    outputSchema: NotificationsSchema,
    streamSchema: z.string(),
  },
  async ({ topic }, { sendChunk }) => {
    const { stream, response } = ai.generateStream({
      output: { schema: NotificationsSchema },
      prompt: `Generate 3 mobile app notifications about: "${topic}".
Return ONLY valid JSON (no markdown, no explanation) matching this structure:
{"notifications":[{"title":"...","body":"...","icon":"<single emoji>"}]}
Use a single relevant emoji for the icon field.`,
    });

    for await (const chunk of stream) {
      if (chunk.text) {
        sendChunk(chunk.text);
      }
    }

    const text = (await response).text.replace(/```json\n?|\n?```/g, '').trim();
    return JSON.parse(text) as z.infer<typeof NotificationsSchema>; // eslint-disable-line @typescript-eslint/no-unsafe-return
  }
);
