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

import { createInterface } from 'node:readline';
import { ai } from './genkit.js';
import { infoAgent } from './infoAgent.js';

const rl = createInterface({
  input: process.stdin,
  output: process.stdout,
});

const EXAMPLE_USER_CONTEXT = {
  parentId: 4112,
  parentName: 'Francis Smith',
  students: [
    {
      id: 3734,
      name: 'Evelyn Smith',
      grade: 9,
      activities: ['Choir', 'Drama Club'],
    },
    { id: 9433, name: 'Evan Smith', grade: 11, activities: ['Chess Club'] },
  ],
};

async function main() {
  const chat = ai
    .createSession({ initialState: EXAMPLE_USER_CONTEXT })
    .chat(infoAgent);

  const { text: greeting } = await ai.generate(
    'Come up with a short friendly greeting for yourself talking to a parent as Bell, the helpful AI assistant for parents of Sparkyville High School. Feel free to use emoji.'
  );
  console.log();
  console.log('\x1b[33mbell>\x1b[0m', greeting);
  while (true) {
    await new Promise((resolve) => {
      rl.question('\n\x1b[36mprompt>\x1b[0m ', async (input) => {
        try {
          const start = chat.messages.length;
          const { stream, response } = await chat.sendStream(input);
          console.log();
          process.stdout.write('\x1b[33mbell>\x1b[0m ');
          for await (const chunk of stream) {
            process.stdout.write(chunk.text);
          }
          console.log(
            '\nTools Used:',
            (await response).messages
              .slice(start)
              .filter((m) => m.role === 'model')
              .map((m) =>
                m.content
                  .filter((p) => !!p.toolRequest)
                  .map(
                    (p) =>
                      `${p.toolRequest.name}(${JSON.stringify(p.toolRequest.input)})`
                  )
              )
              .flat()
              .filter((t) => !!t)
          );

          resolve(null);
        } catch (e) {
          console.log('e', e);
        }
      });
    });
  }
}

setTimeout(main, 0);
