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
import { run } from '@genkit-ai/core';
import { firebaseAuth } from '@genkit-ai/firebase/auth';
import { noAuth, onFlow } from '@genkit-ai/firebase/functions';
import { gemini15Flash } from '@genkit-ai/googleai';
import { DecodedIdToken } from 'firebase-admin/auth';
import * as z from 'zod';
import { ai } from '../index.js';

export const flowBasicAuth = ai.defineFlow(
  {
    name: 'flowBasicAuth',
    inputSchema: z.object({ language: z.string(), uid: z.string() }),
    outputSchema: z.string(),
    authPolicy: (auth, input) => {
      if (!auth) {
        throw new Error('Authorization required.');
      }
      if (input.uid !== auth.uid) {
        throw new Error('You may only summarize your own profile data.');
      }
    },
  },
  async (input) => {
    const prompt = `Say hello in language ${input.language}`;

    return await run('call-llm', async () => {
      const llmResponse = await generate({
        model: gemini15Flash,
        prompt: prompt,
      });

      return llmResponse.text();
    });
  }
);

export const flowAuth = onFlow(
  ai,
  {
    name: 'flowAuth',
    inputSchema: z.string(),
    outputSchema: z.string(),
    httpsOptions: {
      cors: '*',
    },
    authPolicy: firebaseAuth((user: DecodedIdToken) => {
      if (!user.email_verified && !user.admin) {
        throw new Error('Auth failed - email not verified');
      }
    }),
  },
  async (language) => {
    const prompt = `Say hello in language ${language}`;

    return await run('call-llm', async () => {
      const llmResponse = await generate({
        model: gemini15Flash,
        prompt: prompt,
      });

      return llmResponse.text();
    });
  }
);

export const flowAuthNone = onFlow(
  ai,
  {
    name: 'flowAuthNone',
    inputSchema: z.string(),
    outputSchema: z.string(),
    httpsOptions: {
      cors: '*',
    },
    authPolicy: noAuth(),
  },
  async (language) => {
    const prompt = `Say hello in language ${language}`;

    return await run('call-llm', async () => {
      const llmResponse = await generate({
        model: gemini15Flash,
        prompt: prompt,
      });

      return llmResponse.text();
    });
  }
);
