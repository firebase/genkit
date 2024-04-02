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

import { initializeGenkit } from '@genkit-ai/core';
import { prompt } from '@genkit-ai/dotprompt';
import { defineFlow } from '@genkit-ai/flow';
import * as z from 'zod';

initializeGenkit();

prompt('story');
// This example demonstrates using prompt files in a flow

// Load the prompt file during initialization.
// If it fails, due to the file being invalid, the process will crash
// instead of us getting a weird failure later when the flow runs.

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
