/**
 * Copyright 2026 Google LLC
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

import { googleAI } from '@genkit-ai/google-genai';
import { genkit, z } from 'genkit';
import { toolApproval } from '../src/index.js';

const ai = genkit({
  plugins: [googleAI()],
});

const weatherTool = ai.defineTool(
  {
    name: 'weather',
    description: 'get the weather',
    inputSchema: z.object({ city: z.string() }),
    outputSchema: z.string(),
  },
  async ({ city }) => {
    return `The weather in ${city} is nice.`;
  }
);

async function main() {
  console.log('--- Running without approval ---');
  const response = await ai.generate({
    model: googleAI.model('gemini-3-flash-preview'),
    tools: [weatherTool],
    prompt: 'What is the weather in Paris?',
    use: [toolApproval()],
  });

  if (response.finishReason === 'interrupted') {
    console.log('Interrupted!');
    const interrupt = response.interrupts[0];
    console.log('Interrupt metadata:', interrupt?.metadata?.interrupt);
    if (!interrupt) {
      throw new Error('No interrupt found');
    }

    // approve the tool:
    interrupt.metadata = { ...interrupt.metadata, 'tool-approved': true };

    console.log('\n--- Running with approval ---');
    const response2 = await ai.generate({
      model: googleAI.model('gemini-3-flash-preview'),
      messages: response.messages,
      tools: [weatherTool],
      use: [toolApproval()],
      resume: {
        restart: [interrupt],
      },
    });
    console.log('Response:', response2.text);
  } else {
    console.log('Response:', response.text);
    return;
  }
}

main().catch(console.error);
