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
import { genkit } from 'genkit';
import { filesystem } from '../src/index.js';

const ai = genkit({
  plugins: [googleAI()],
});

async function main() {
  const { text } = await ai.generate({
    model: googleAI.model('gemini-3-flash-preview'),
    prompt:
      'Can you list the files in my temporary directory and read whatever is in `hello.txt`?',
    use: [
      filesystem({
        rootDirectory: process.env.TEMP_DIR || '/tmp',
      }),
    ],
  });
  console.log(text);
}

main().catch(console.error);
