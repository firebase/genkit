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

import { onCallGenkit } from 'firebase-functions/https';
import { defineSecret } from 'firebase-functions/params';
import { z } from 'genkit';
import { ai } from '../genkit.js';

const apiKey = defineSecret('GOOGLE_GENAI_API_KEY');

const greetFlow = ai.defineFlow(
  {
    name: 'greet',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (language: string) => {
    const { text } = await ai.generate({
      prompt: `Say hello in language ${language}`,
    });
    return text;
  }
);

export const greetNoAuth = onCallGenkit(
  {
    secrets: [apiKey],
  },
  greetFlow
);

export const greetAuthAndAppCheck = onCallGenkit(
  {
    secrets: [apiKey],
    authPolicy: (auth) => auth?.token?.email_verified && auth?.token?.admin,
    enforceAppCheck: true,
  },
  greetFlow
);
