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

import { Response } from 'express';
import { DecodedIdToken, getAuth } from 'firebase-admin/auth';
import { __RequestWithAuth, z, FlowAuthPolicy } from 'genkit';
import { FunctionFlowAuth } from './functions.js';
import { initializeAppIfNecessary } from './helpers.js';


export function firebaseAuth<I extends z.ZodTypeAny>(
  policy: (user: DecodedIdToken, input: z.infer<I>) => void | Promise<void>,
  config?: { required: boolean }
): FlowAuthPolicy<I> {
  initializeAppIfNecessary();
  const required = config?.required ?? true;
  return async (auth: DecodedIdToken | undefined, input: z.infer<I>) => {
    if (required && !auth) {
      throw new Error('Auth is required');
    }
    return policy(auth as DecodedIdToken, input);
  };
}

function unauthorized(res: Response) {
  res.status(403);
  res.send('Unauthorized');
  res.end();
}
