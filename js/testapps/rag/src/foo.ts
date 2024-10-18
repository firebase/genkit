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

import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { genkit } from 'genkit';
import readline from 'node:readline';

const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

const refundAgent = ai.definePrompt(
  {
    name: 'refundAgent',
    config: { temperature: 1 },
    description: 'Refunds Agent',
  },
  '{{role "system"}} Help the user with a refund.'
);

const salesAgent = ai.definePrompt(
  {
    name: 'salesAgent',
    config: { temperature: 1 },
    description: 'Sales Agent',
    tools: [refundAgent],
  },
  '{{role "system"}} Be super enthusiastic about selling stuff. Feel free to adopt a pushy sales person persona.'
);

const triageAgent = ai.definePrompt(
  {
    name: 'triageAgent',
    config: { temperature: 1 },
    description: 'triage Agent',
    tools: [salesAgent, refundAgent],
  },
  '{{role "system"}} greet the person, ask them about what they need and if appropriate transfer an agents that can better handle the query'
);

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

(async () => {
  const session = ai.chat({
    prompt: triageAgent,
  });
  while (true) {
    await new Promise((resolve) => {
      rl.question(`Say: `, async (input) => {
        const { text } = await session.send(input);
        console.log(text);
        resolve(null);
      });
    });
  }
})();
