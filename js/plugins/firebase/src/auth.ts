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

import { __RequestWithAuth } from '@genkit-ai/flow';
import { Response } from 'express';
import { DecodedIdToken, getAuth } from 'firebase-admin/auth';
import * as z from 'zod';
import { FunctionFlowAuth } from './functions.js';
import { initializeAppIfNecessary } from './helpers.js';

export function firebaseAuth<I extends z.ZodTypeAny>(
  policy: (user: DecodedIdToken, input: z.infer<I>) => void | Promise<void>
): FunctionFlowAuth<I>;
export function firebaseAuth<I extends z.ZodTypeAny>(
  policy: (user: DecodedIdToken, input: z.infer<I>) => void | Promise<void>,
  config: { required: true }
): FunctionFlowAuth<I>;
export function firebaseAuth<I extends z.ZodTypeAny>(
  policy: (
    user: DecodedIdToken | undefined,
    input: z.infer<I>
  ) => void | Promise<void>,
  config: { required: false }
): FunctionFlowAuth<I>;
export function firebaseAuth<I extends z.ZodTypeAny>(
  policy: (user: DecodedIdToken, input: z.infer<I>) => void | Promise<void>,
  config?: { required: boolean }
): FunctionFlowAuth<I> {
  initializeAppIfNecessary();
  const required = config?.required ?? true;
  return {
    async policy(auth: unknown | undefined, input: z.infer<I>) {
      // If required is true, then auth will always be set when called from
      // an HTTP context. However, we need to wrap the user-provided policy
      // to check for presence of auth when the flow is executed from runFlow
      // or an action context.
      if (required && !auth) {
        throw new Error('Auth is required');
      }

      return policy(auth as DecodedIdToken, input);
    },
    async provider(req, res, next) {
      const token = req.headers['authorization']?.split(/[Bb]earer /)[1];
      let decoded: DecodedIdToken;

      if (!token) {
        if (required) {
          unauthorized(res);
        } else {
          next();
        }
        return;
      }
      try {
        decoded = await getAuth().verifyIdToken(token);
      } catch (e) {
        unauthorized(res);
        return;
      }

      (req as __RequestWithAuth).auth = decoded;

      next();
    },
  };
}

function unauthorized(res: Response) {
  res.status(403);
  res.send('Unauthorized');
  res.end();
}
