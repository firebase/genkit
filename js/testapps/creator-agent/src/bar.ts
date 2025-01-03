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
import { genkit as initAgenkit, z } from 'genkit';
import { initAgents } from './agents.js';

const genkit = initAgenkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});
const ai = initAgents(genkit);

const updateUsername = genkit.defineTool({
  name: 'updateUsername',
  description: 'used to update the username',
  inputSchema: z.object({
    newUsername: z.string()
  })
}, async (input) => {
  await genkit.currentSession().updateState({
    username: input.newUsername,
  });
  return `updated username to ${input.newUsername}`;
});

const infoAgent = ai.defineAgent({
  name: 'infoAgent',
  description: `This agent helps with answering inquiries and requests.`,
  instructions: `User's name is {{@state.username}}. Greet them by name!`,
  tools: [updateUsername]
});

(async () => {
  const session = ai.startSession({
    agent: infoAgent,
    initialState: {
      username: 'Pavel',
    },
  });
  let resp = await session.send('update username to Bob');
  console.log(' - - - - -', JSON.stringify(resp.messages, undefined, 2));
  console.log('new state:', JSON.stringify(session.session.sessionData));
  resp = await session.send('hi');
  console.log(' - - - - -', JSON.stringify(resp.messages, undefined, 2));
})();
