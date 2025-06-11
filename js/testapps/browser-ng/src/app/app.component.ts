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

import { Component } from '@angular/core';
import { genkit } from 'genkit/beta/browser';

const ai = genkit({});

// fake model
let reqCounter = 0;
const model = ai.defineModel({ name: 'banana' }, async (req) => {
  return {
    message: {
      role: 'model',
      content: [
        reqCounter++ === 0
          ? {
              toolRequest: {
                name: 'testTool',
                input: {},
                ref: 'ref123',
              },
            }
          : { text: 'r:' + JSON.stringify(req) },
      ],
    },
  };
});

const testTool = ai.defineTool(
  { name: 'testTool', description: 'description' },
  async () => 'tool called'
);

const p = ai.definePrompt({
  name: 'testp',
  prompt: 'yeah {{foo}}',
  model: 'banana',
});

@Component({
  selector: 'app-root',
  imports: [],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  title = 'browser-ng';

  async doIt() {
    console.log(
      await model.run({
        messages: [{ content: [{ text: 'hello' }], role: 'user' }],
      })
    );

    console.log(
      (
        await p({
          foo: 'yoo',
        })
      ).text
    );

    const { text } = await ai.generate({
      model: 'banana',
      prompt: 'hello',
      tools: [testTool],
    });
    console.log(text);
  }
}
