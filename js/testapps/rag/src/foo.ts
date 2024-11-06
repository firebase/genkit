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

const ai = genkit({
  plugins: [googleAI()],
  //promptDir: './prompts',
  model: gemini15Flash,
});

(async () => {
  console.log((await ai.prompt('myPrompt')()).text);
})();

/*
import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { genkit, z } from 'genkit';

const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

const developerAgent = ai.definePrompt(
  {
    name: 'developer_agent',
    config: { temperature: 1 },
    description: 'Refunds Agent can help with refund inquiries',
  },
  `{{role "system"}} You are a software engineer at a leading tech company.
	 Your expertise in programming in python. and do your best to produce perfect code.
        You will create a game using python, these are the instructions:

        Game: {{ @state.game }}

        Your Final answer must be the full python code,
        only the python code and nothing else.
`
);

const reviewerAgent = ai.definePrompt(
  {
    name: 'reviewer_agent',
    config: { temperature: 1 },
    description: 'Refunds Agent can help with refund inquiries',
  },
  `{{role "system"}} You are a software engineer that specializes in checking code for errors. You have an eye for detail and a knack for finding hidden bugs.

      You are reviewing a game developed using python, these are the instructions:

      Game:  {{ @state.game }}

      Using the code you got, check for errors. Check for logic errors, syntax errors, missing imports, variable declarations, mismatched brackets, and security vulnerabilities.
      Your Final answer is a bullet list of errors you found or suggestions to improve the code.
      You are not asked to run the code. You just need to provide feedback.

        When done reviweing transfer over to 'tl_agent'.
`
);

const tlAgent = ai.definePrompt(
  {
    name: 'tl_agent',
    input: {
      schema: z.object({ game: z.string() }),
    },
    config: { temperature: 1 },
    description: 'Refunds Agent can help with refund inquiries',
  },
  `{{role "system"}} You are a senior software engineer TL at a leading tech company.
      You are helping a junior software engineer improve their code.
      Their code creates a game using python, these are the instructions:

      Game: {{ @state.game }}

      Based on the code the developer_agent wrote, and the feedback from the reviewer_agent,
      you will improve the code.

      Your final answer must be the full python code, only the python code and nothing else.
`
);

(async () => {
  const sess = ai.createSession({
    initialState: {
      game: 'flappy bird',
    },
  });
  const { text: initialCode } = await sess
    .chat({
      preamble: developerAgent,
    })
    .send('build the game please');
  console.log(initialCode);

  const { text: feedback } = await sess
    .chat({
      preamble: reviewerAgent,
    })
    .send('review please');
  console.log(feedback);

  const { text: result } = await sess
    .chat({
      preamble: tlAgent,
    })
    .send('improve please');

  console.log(result);
})();
*/
