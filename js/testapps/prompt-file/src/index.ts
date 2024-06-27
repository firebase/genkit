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

import { configureGenkit } from '@genkit-ai/core';
import { dotprompt, prompt } from '@genkit-ai/dotprompt';
import { defineFlow } from '@genkit-ai/flow';
import { googleAI } from '@genkit-ai/googleai';
import * as z from 'zod';

configureGenkit({
  plugins: [googleAI(), dotprompt()],
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});

// This example demonstrates using prompt files in a flow
// Load the prompt file during initialization.
// If it fails, due to the prompt file being invalid, the process will crash,
// instead of us getting a more mysterious failure later when the flow runs.

prompt('recipe').then((recipePrompt) => {
  defineFlow(
    {
      name: 'chefFlow',
      inputSchema: z.object({
        food: z.string(),
      }),
      outputSchema: z.any(),
    },
    async (input) => (await recipePrompt.generate({ input: input })).output()
  );
});

prompt('recipe', { variant: 'robot' }).then((recipePrompt) => {
  defineFlow(
    {
      name: 'robotChefFlow',
      inputSchema: z.object({
        food: z.string(),
      }),
      outputSchema: z.any(),
    },
    async (input) => (await recipePrompt.generate({ input: input })).output()
  );
});

// A variation that supports streaming, optionally

prompt('story').then((storyPrompt) => {
  defineFlow(
    {
      name: 'tellStory',
      inputSchema: z.object({
        subject: z.string(),
        personality: z.string().optional(),
      }),
      outputSchema: z.string(),
      streamSchema: z.string(),
    },
    async ({ subject, personality }, streamingCallback) => {
      if (streamingCallback) {
        const { response, stream } = await storyPrompt.generateStream({
          input: { subject, personality },
        });
        for await (const chunk of stream()) {
          streamingCallback(chunk.content[0]?.text!);
        }
        return (await response()).text();
      } else {
        const response = await storyPrompt.generate({ input: { subject } });
        return response.text();
      }
    }
  );
});
