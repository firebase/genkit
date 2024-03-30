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
import { initializeGenkit } from '@genkit-ai/core/config';
import { durableFlow, interrupt, run } from '@genkit-ai/flow/experimental';
import { geminiPro } from '@genkit-ai/plugin-google-genai';
import * as z from 'zod';
import config from './genkit.config.js';

// To run this sample use the following sample commands:
//   genkit flow:run jokeFlow "\"apple\""
//   genkit flow:resume jokeFlow FLOW_ID_FROM_PREV_COMMAND "\{\"approved\":true}"

initializeGenkit(config);

export const jokeFlow = durableFlow(
  {
    name: 'jokeFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (inputSubject) => {
    const prompt = await run('make-prompt', async () => ({
      prompt: `Tell me a joke about ${inputSubject}`,
    }));

    const llmResponse = await run('run-llm', async () =>
      (await generate({ model: geminiPro, prompt: prompt.prompt })).text()
    );

    await run(
      'notify-hooman-approval-is-needed',
      async () => await notifyHooman(llmResponse)
    );

    const hoomanSaid = await interrupt(
      'approve-by-hooman',
      z.object({ approved: z.boolean() })
    );

    if (hoomanSaid.approved) {
      return llmResponse;
    } else {
      return 'Sorry, the llm generated something inappropriate, please try again.';
    }
  }
);

async function notifyHooman(llmResponse: string) {
  console.log('notifyHooman', llmResponse);
}
