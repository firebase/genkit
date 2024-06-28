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
import { firebaseAuth } from '@genkit-ai/firebase/auth';
import { noAuth, onFlow } from '@genkit-ai/firebase/functions';
import { run } from '@genkit-ai/flow';
import { gemini15Flash } from '@genkit-ai/googleai';
import { DecodedIdToken } from 'firebase-admin/auth';
import * as z from 'zod';

export const flowAuth = onFlow(
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
