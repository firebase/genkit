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

// [START ex]
import { hasClaim, onCallGenkit } from 'firebase-functions/https';
import { defineSecret } from 'firebase-functions/params';

const apiKey = defineSecret('GOOGLE_AI_API_KEY');

const menuSuggestionFlow = ai.defineFlow(
  {
    name: 'menuSuggestionFlow',
  },
  async (restaurantTheme) => {
    // ...
  }
);

export const menuSuggestion = onCallGenkit(
  {
    secrets: [apiKey],
    authPolicy: hasClaim('email_verified'),
  },
  menuSuggestionFlow
);

// [END ex]
