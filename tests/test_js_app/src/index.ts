/**
 * Copyright 2024 Google LLC
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

import { generate } from '@genkit-ai/ai';
import { defineModel } from '@genkit-ai/ai/model';
import { configureGenkit } from '@genkit-ai/core';
import { firebase } from '@genkit-ai/firebase';
import { defineFlow } from '@genkit-ai/flow';
import * as z from 'zod';

defineModel(
  {
    name: 'customReflector',
  },
  async (input) => {
    // In Go, JSON object properties are output in sorted order.
    // JSON.stringify uses the order they appear in the program.
    // So swap the order here to match Go.
    const m = input.messages[0];
    input.messages[0] = { content: m.content, role: m.role };
    return {
      candidates: [
        {
          index: 0,
          finishReason: 'stop',
          message: {
            role: 'model',
            content: [
              {
                text: JSON.stringify(input),
              },
            ],
          },
        },
      ],
    };
  }
);

export default configureGenkit({
  plugins: [firebase()],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});

export const testFlow = defineFlow(
  { name: 'testFlow', inputSchema: z.string(), outputSchema: z.string() },
  async (subject) => {
    const response = await generate({
      model: 'customReflector',
      prompt: subject,
    });

    const want = `{"messages":[{"content":[{"text":"${subject}"}],"role":"user"}],"tools":[],"output":{"format":"text"}}`;
    if (response.text() !== want) {
      throw new Error(`Expected ${want} but got ${response.text()}`);
    }

    return 'Test flow passed';
  }
);
