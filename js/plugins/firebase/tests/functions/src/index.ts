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

import { enableFirebaseTelemetry } from '@genkit-ai/firebase';
import { noAuth, onFlow } from '@genkit-ai/firebase/functions';
import { genkit, z } from 'genkit';

const ai = genkit({});
enableFirebaseTelemetry({});

export const simpleFlow = onFlow(
  ai,
  {
    name: 'simpleFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
    httpsOptions: {
      cors: '*',
    },
    authPolicy: noAuth(),
  },
  async (subject) => {
    return 'hello world!';
  }
);
