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

const contextAsyncLocalStorage = new AsyncLocalStorage<any>();

/**
 * Execute the provided function in the runtime context. Call {@link getFlowContext()} anywhere
 * within the async call stack to retrieve the context.
 */
export function runWithContext<R>(context: any, fn: () => R) {
  return contextAsyncLocalStorage.run(context, () =>
    runInActionRuntimeContext(fn)
  );
}

/**
 * Gets the auth object from the current context.
 *
 * @deprecated use {@link getFlowContext}
 */
export function getFlowAuth(): any {
  return contextAsyncLocalStorage.getStore();
}

/**
 * Gets the runtime context of the current flow.
 */
export function getFlowContext(): any {
  return contextAsyncLocalStorage.getStore();
}
