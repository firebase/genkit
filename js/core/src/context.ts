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
import { HasRegistry, Registry } from './registry.js';

const contextAlsKey = 'core.auth.context';
const legacyContextAsyncLocalStorage = new AsyncLocalStorage<any>();

/**
 * Execute the provided function in the runtime context. Call {@link getFlowContext()} anywhere
 * within the async call stack to retrieve the context.
 */
export function runWithContext<R>(
  registry: Registry,
  context: any,
  fn: () => R
) {
  return legacyContextAsyncLocalStorage.run(context, () =>
    registry.asyncStore.run(contextAlsKey, context, () =>
      runInActionRuntimeContext(registry, fn)
    )
  );
}

/**
 * Gets the auth object from the current context.
 *
 * @deprecated use {@link getFlowContext}
 */
export function getFlowAuth(registry?: Registry | HasRegistry): any {
  if (!registry) {
    return legacyContextAsyncLocalStorage.getStore();
  }
  return getContext(registry);
}

/**
 * Gets the runtime context of the current flow.
 */
export function getContext(registry: Registry | HasRegistry): any {
  if ((registry as HasRegistry).registry) {
    registry = (registry as HasRegistry).registry;
  }
  registry = registry as Registry;
  return registry.asyncStore.getStore(contextAlsKey);
}
