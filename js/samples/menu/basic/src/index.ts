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
import { configureGenkit } from '@genkit-ai/core';
import { defineFlow } from '@genkit-ai/flow';
import { geminiPro, googleAI } from '@genkit-ai/googleai';
import * as z from 'zod';

configureGenkit({
  plugins: [googleAI()],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});

export const menuQAFlow = defineFlow(
  {
    name: 'menuQAFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject) => {
    const prompt = `Our menu today includes burgers, spinach, and cod.
     Tell me if ${subject} can be found on the menu`;

    const llmResponse = await generate({
      model: geminiPro,
      prompt: prompt,
    });

    return llmResponse.text();
  }
);
