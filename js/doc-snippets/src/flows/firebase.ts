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
import { firebaseAuth } from '@genkit-ai/firebase/auth';
import { onFlow } from '@genkit-ai/firebase/functions';

export const menuSuggestion = onFlow(
  ai,
  {
    name: 'menuSuggestionFlow',
    authPolicy: firebaseAuth((user) => {
      if (!user.email_verified) {
        throw new Error('Verified email required to run flow');
      }
    }),
  },
  async (restaurantTheme) => {
    // ...
  }
);
// [END ex]
