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

import { genkit } from 'genkit';

const ai = genkit({});

// [START ex01]
export const menuSuggestionFlow = ai.defineFlow(
  {
    name: 'menuSuggestionFlow',
  },
  async (restaurantTheme) => {
    // ...
  }
);

ai.startFlowServer();
// [END ex01]

// [START ex02]
export const flowA = ai.defineFlow({ name: 'flowA' }, async (subject) => {
  // ...
});

export const flowB = ai.defineFlow({ name: 'flowB' }, async (subject) => {
  // ...
});

ai.startFlowServer({
  flows: [flowB],
  port: 4567,
  cors: {
    origin: '*',
  },
});
// [END ex02]
