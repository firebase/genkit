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

import { testModels } from 'genkit/testing';
import { genkit } from 'genkit';
import { googleAI } from '@genkit-ai/googleai';
import { claude3Sonnet, llama31, vertexAI } from '@genkit-ai/vertexai';
import * as clc from 'colorette';
import { ollama } from 'genkitx-ollama';
import { openAI } from 'genkitx-openai';

export const ai = genkit({
  plugins: [
    googleAI(),
    vertexAI({
      location: 'us-central1',
      modelGarden: {
        models: [claude3Sonnet, llama31],
      },
    }),
    ollama({
      models: [
        {
          name: 'gemma2',
          type: 'chat',
        },
      ],
      serverAddress: 'http://127.0.0.1:11434', // default local address
    }),
    openAI(),
  ],
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});

testModels([
  'googleai/gemini-1.5-pro-latest',
  'googleai/gemini-1.5-flash-latest',
  'vertexai/gemini-1.5-pro',
  'vertexai/gemini-1.5-flash',
  'vertexai/claude-3-sonnet',
  'vertexai/llama-3.1',
  'ollama/gemma2',
  'openai/gpt-4o',
  'openai/gpt-4o-mini',
]).then((r) => {
  let failed = false;
  for (const test of r) {
    console.log(`${clc.bold('Test:')} ${test.description}`);
    for (const model of test.models) {
      if (model.passed) {
        console.log(
          `  - ${clc.bold(clc.green('PASSED'))}: ${clc.bold(model.name)}`
        );
      } else if (model.skipped) {
        console.log(
          `  - ${clc.bold(clc.yellow('SKIPPED'))}: ${clc.bold(model.name)}`
        );
      } else {
        failed = true;
        console.log(
          `  - ${clc.bold(clc.red('FAILED'))}: ${clc.bold(model.name)}`
        );
        if (model.error?.message) {
          console.log(prefixText(model.error?.message, '    '));
        }
        if (model.error?.stack) {
          console.log(prefixText(model.error?.stack, '    '));
        }
      }
    }
  }
  if (failed) {
    process.exitCode = 1;
  }
});

function prefixText(txt: string, prefix: string) {
  return txt
    .split('\n')
    .map((t) => prefix + t)
    .join('\n');
}
