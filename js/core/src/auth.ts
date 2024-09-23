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

import { AsyncLocalStorage } from 'node:async_hooks';
import { runInActionRuntimeContext } from './action.js';

const authAsyncLocalStorage = new AsyncLocalStorage<any>();

/**
 * Execute the provided function in the auth context. Call {@link getFlowAuth()} anywhere
 * within the async call stack to retrieve the auth.
 */
export function runWithAuthContext<R>(auth: any, fn: () => R) {
  return authAsyncLocalStorage.run(auth, () => runInActionRuntimeContext(fn));
}

/**
 * Gets the auth object from the current context.
 */
export function getFlowAuth(): any {
  return authAsyncLocalStorage.getStore();
}
