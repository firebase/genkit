/**
 * Copyright 2025 Google LLC
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

import { AuthPolicy, Request, UserFacingError } from 'genkit/authPolicy';

export interface ApiKeyContext {
  auth?: {
    apiKey: string;
  };
}

export function apiKey(
  policy: (context: ApiKeyContext) => void | Promise<void>
): AuthPolicy;
export function apiKey(value?: string): AuthPolicy;
export function apiKey(
  valueOrPolicy?: ((context: ApiKeyContext) => void | Promise<void>) | string
): AuthPolicy {
  return async function (request: Request): Promise<ApiKeyContext> {
    const context: ApiKeyContext = {};
    if ('authorization' in request.headers) {
      context.auth = { apiKey: request.headers['authorization'] };
    }
    if (typeof valueOrPolicy === 'string') {
      if (!context.auth) {
        throw new UserFacingError('unauthenticated', 'Unauthenticated');
      }
      if (context.auth?.apiKey != valueOrPolicy) {
        throw new UserFacingError('permission-denied', 'Permission denied');
      }
    } else if (typeof valueOrPolicy === 'function') {
      await valueOrPolicy(context);
    } else if (typeof valueOrPolicy !== 'undefined') {
      throw new Error(
        `Invalid type ${typeof valueOrPolicy} passed to apiKey()`
      );
    }
    return context;
  };
}
